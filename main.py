import os
from datasets import load_dataset
import concurrent.futures
import scripts.generate_wavedroms
import scripts.meta_data as meta_data
import shutil
import re
import threading
import argparse
import glob
import scripts.meta_data
import scripts.simulate
import scripts.tb_gen
from scripts.simulate import compile, run_simulation
import scripts.generate_wavedroms
import scripts.counter

FOLDER = os.path.dirname(os.path.realpath(__file__)) + "/data"
MAX_PROCESSES = os.cpu_count() - 2 if os.cpu_count() > 2 else 1
MAX_PORTS = 6

DATASETS = ["wangxinze/Verilog_data", "shailja/Verilog_Github"]

DEBUG = False

# used to limit access to the tb_gen script which uses subprocess to run gentbvlog
# too many processes can cause the system to hang
TB_GEN_SEMAPHORE = threading.Semaphore((MAX_PROCESSES/2) - 1)
SIM_SEMAPHORE = threading.Semaphore(MAX_PROCESSES - 1)

def remove_comments(code):
    '''
    Remove comments from the code
    This makes parsing and splitting the code into individual modules easier
    '''
    # remove block comments
    regex=r'/\*.*?\*/'
    matches = re.findall(regex, code, re.DOTALL)
    for match in matches:
        code = code.replace(match, '')
    # remove line comments
    regex=r'//.*$'
    code = re.sub(regex, '', code, flags=re.MULTILINE)
    return code


def split_modules(code):
    '''
    Split the code into individual modules
    '''
    code = remove_comments(code)
    code = code.split("endmodule")
    modules = []
    for c in code:
        modules.append(c + "endmodule")
    # remove last module, this only contains the endmodule keyword
    modules = modules[:-1]
    return modules

def parse_verilog_module(id, data):
    '''
    Parse the data and store it in a file
    Used by the concurrent.futures.ProcessPoolExecutor for multiprocessing
    '''
    meta = meta_data.MetaData()
    if meta.analyze_code(data) is not None:
        if len(meta.meta["ports"]) <= MAX_PORTS:
            os.makedirs(f"{FOLDER}/ds_{id}")
            meta.store(f"{FOLDER}/ds_{id}")
            # write the code to a file
            with open(f"{FOLDER}/ds_{id}/module.v", "w") as f:
                f.write(meta.meta["code"])
            return True
    return False

def generate_testbench(folder):
    '''
    Generate a testbench for the module
    Used by the concurrent.futures.ThreadPoolExecutor for multithreading
    '''
    TB_GEN_SEMAPHORE.acquire()
    success = scripts.tb_gen.generate_testbench(folder)
    TB_GEN_SEMAPHORE.release()
    if not success:
        if not DEBUG:
            shutil.rmtree(folder)
        return False
    return True


def perform_simulation(folder):
    '''
    Perform a simulation on the module
    Used by the concurrent.futures.ThreadPoolExecutor for multithreading
    '''
    SIM_SEMAPHORE.acquire()
    try:
        success = compile(folder)
    except Exception as e:
        SIM_SEMAPHORE.release()
        return False
    SIM_SEMAPHORE.release()
    if not success:
        if not DEBUG:
            shutil.rmtree(folder)
        return False
    SIM_SEMAPHORE.acquire()
    try:
        success = run_simulation(folder)
    except Exception as e:
        SIM_SEMAPHORE.release()
        return False
    SIM_SEMAPHORE.release()
    if not success:
        if not DEBUG:
            shutil.rmtree(folder)
        return False
    return True


def generate_waveform(folder):
    '''
    Generate the waveform from the simulation
    '''
    success = scripts.generate_wavedroms.generate_wavedrom(folder)
    if not success:
        if not DEBUG:
            shutil.rmtree(folder)
        return False
    return True


def gather_verilog_data():
    if os.path.exists(FOLDER):
        shutil.rmtree(FOLDER, ignore_errors=True)
    print(f"Creating directory {FOLDER}")
    os.makedirs(FOLDER)
    id = 0
    futures = []
    for dataset in DATASETS:
        i = 0
        print(f"Loading dataset {dataset}")
        ds = load_dataset(dataset, num_proc=MAX_PROCESSES)
        print(f"Dataset {dataset} loaded")
        print(f"Parsing dataset {dataset} using {MAX_PROCESSES} processes")
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=MAX_PROCESSES-1)
        for data in ds['train']:
            i += 1
            # datasets put their code under various names
            code = data if type(data) == str else data['text'] if 'text' in data else data['module_content']
            # the MetaData class only supports one module at a time for now
            if code.count("endmodule") > 1:
                modules = split_modules(code)
            else:
                modules = [code]
            for m in modules:
                futures.append(executor.submit(parse_verilog_module, id, m))
                id += 1
                if id % 1000 == 0:
                    print(f"Submitted a total of {id} modules to the pool", end="\r")
    print("")
    success = 0
    i = 0
    for future in concurrent.futures.as_completed(futures):
        if future.result():
            success += 1
        i += 1
        if i % 1000 == 0:
            print(f"Completed {i}/{len(futures)} files, success rate: {success}/{i}", end="\r")
    print(f"Completed {i}/{len(futures)} files, success rate: {success}/{i}")
    print("Dataset created")

def generate_testbenches():
    total = 0
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2*MAX_PROCESSES)
    futures = []
    i = 0
    for folder in os.listdir(FOLDER):
        # only add directories which dont have a tb.v file and don't have an error file
        if os.path.exists(f"{FOLDER}/{folder}/tb.v") or os.path.exists(f"{FOLDER}/{folder}/gentbvlog_err.txt") or os.path.exists(f"{FOLDER}/{folder}/meta_load_err.txt"):
            continue

        futures.append(executor.submit(generate_testbench, f"{FOLDER}/{folder}"))
        i += 1
        total += 1
        if i % 1000 == 0:
            print(f"Submitted {i} testbench generations to the pool", end="\r")
    print("")
    success = 0
    i = 0
    print("Waiting for testbenches to be generated")
    print("This uses the gentbvlog command, which can be slow. Depending on the number of modules, this can take a while")
    for future in concurrent.futures.as_completed(futures):
        if future.result():
            success += 1
        i += 1
        if i % 10 == 0:
            print(f"Completed {i}/{total} testbench generations, success rate: {success}/{i}", end="\r")
    print(f"Completed {i}/{total} testbench generations, success rate: {success}/{i}")
    print("Testbenches generated")


def perform_simulations():
    '''
    Perform simulations on the testbenches
    '''
    total = len([folder for folder in os.listdir(FOLDER)])
    print(f"Performing simulations on {total} modules using {MAX_PROCESSES} threads")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PROCESSES) as executor:
        futures = []
        for i, folder in enumerate(os.listdir(FOLDER), 1):
            futures.append(executor.submit(perform_simulation, f"{FOLDER}/{folder}"))
            i += 1
            if i % 10 == 0:
                print(f"Submitted {i} simulations to the pool", end="\r")
        print("")
        success = 0
        print("Waiting for simulations to complete")
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                if future.result():
                    success += 1
            except Exception as e:
                pass
            if i % 10 == 0:
                print(f"Completed {i}/{total} simulations, success rate: {success}/{i}", end="\r")
    print(f"Completed {i}/{total} simulations, success rate: {success}/{i}")
    print("Simulations completed")


def generate_waveforms():
    '''
    Generate waveforms for the simulations
    '''
    total = 0
    for folder in os.listdir(FOLDER):
        total += 1
    print(f"Generating waveforms for {total} modules using {MAX_PROCESSES} threads")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2*MAX_PROCESSES)
    futures = []
    i = 0
    for folder in os.listdir(FOLDER):
        if os.path.exists(f"{FOLDER}/{folder}/img") and len(glob.glob(f"{FOLDER}/{folder}/img/*.png")) > 0: # skip if waveforms already exist
            continue
        futures.append(executor.submit(scripts.generate_wavedroms.generate_wavedrom, os.path.join(FOLDER, folder)))
        i += 1
        if i % 1000 == 0:
            print(f"Submitted {i} waveform generations to the pool", end="\r")
    print("")
    success = 0
    i = 0
    for future in concurrent.futures.as_completed(futures):
        if future.result():
            success += 1
        i += 1
        if i % 10 == 0:
            print(f"Completed {i}/{total} waveform generations, success rate: {success}/{i}", end="\r")
    print(f"Completed {i}/{total} waveform generations, success rate: {success}/{i}")
    print("Waveforms generated")


def main():
    '''
    Main function to run the data gathering
    '''
    global FOLDER
    global MAX_PROCESSES
    global MAX_PORTS
    print("Parsing arguments")
    parser = argparse.ArgumentParser(description="Gathers data to form the dataset")
    parser.add_argument("--folder", help="Folder to store the dataset in", default=FOLDER)
    parser.add_argument("--start-at", help="""
                        Starting point for the data gathering
                        create = Creates a new dataset from scratch, gathers verilog from sources and stores them alongside some basic information. (deletes the old one if present)
                        tbgen = Generate the testbenches. Generates testbenches for the verilog files in the dataset. If interrupted, will try to start where previously left off
                        sim = Run the testbenches. Runs the testbenches to get the output waveforms. If interrupted, will try to start where previously left off
                        wfgen = Generate waveforms. If interrupted, will try to start where previously left off
                        """, default="tbgen")
    parser.add_argument("--num_processes", help="Number of processes to use for data gathering", default=MAX_PROCESSES)
    parser.add_argument("--max_ports", help="Only use modules with less than or equal to this number of ports", default=MAX_PORTS)
    parser.add_argument("--max_sim_time", help="Maximum simulation time for testbenches in ns", default=100)
    parser.add_argument("count", help="Gives details on the total amount of data available in the dataset", nargs="?", default=False)
    parser.add_argument("-D", "--debug", help="Enable debug mode", action="store_true")

    args = parser.parse_args()
    
    FOLDER = args.folder
    start_at = args.start_at
    print(f"Folder: {FOLDER}")
    MAX_PROCESSES = int(args.num_processes)
    MAX_PORTS = int(args.max_ports)
    
    max_sim_time = int(args.max_sim_time)

    if args.count:
        print("Counting...")
        scripts.counter.count(FOLDER)
        return

    print(f"Start at: {start_at}")
    print(f"Number of processes: {MAX_PROCESSES}")
    print(f"Max ports: {MAX_PORTS}")

    if args.debug:
        global DEBUG
        DEBUG = True
        scripts.tb_gen.DEBUG = True
        scripts.simulate.DEBUG = True
        scripts.meta_data.DEBUG = True
        scripts.generate_wavedroms.DEBUG = True

    if start_at == "create":
        print("Creating dataset")
        gather_verilog_data()
        start_at = "tbgen"
    if start_at == "tbgen":
        print("Generating testbenches")
        scripts.tb_gen.init(max_sim_time)
        generate_testbenches()
        start_at = "sim"
    if start_at == "sim":
        print("Performing simulations")
        perform_simulations()
        start_at = "wfgen"
    if start_at == "wfgen":
        generate_waveforms()
    

if __name__ == "__main__":
    main()
