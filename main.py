import os
from datasets import load_dataset
import concurrent.futures
import multiprocessing
import scripts.meta_data as meta_data
import shutil
import re
import threading
import argparse
import scripts.tb_gen
from scripts.simulate import compile, run_simulation
import scripts.counter

# FOLDER = os.path.dirname(os.path.realpath(__file__)) + "/data"
FOLDER = "/media/vincent/Z/dataset"
MAX_PROCESSES = os.cpu_count() - 2 if os.cpu_count() > 2 else 1
MAX_PORTS = 6

DATASETS = ["wangxinze/Verilog_data", "shailja/Verilog_Github"]

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
        if len(meta.meta["ports"]) - len(meta.meta["clocks"]) - len(meta.meta["resets"]) <= MAX_PORTS:
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
    success, delete = scripts.tb_gen.generate_testbench(folder)
    TB_GEN_SEMAPHORE.release()
    if not success:
        if delete:
            pass
            # shutil.rmtree(folder)
        return False
    return True


def perform_simulation(folder):
    '''
    Perform a simulation on the module
    Used by the concurrent.futures.ThreadPoolExecutor for multithreading
    '''
    SIM_SEMAPHORE.acquire()
    success, delete = compile(folder)
    SIM_SEMAPHORE.release()
    if not success:
        if delete:
            pass
            # shutil.rmtree(folder)
        return False
    SIM_SEMAPHORE.acquire()
    success, delete = run_simulation(folder)
    SIM_SEMAPHORE.release()
    if not success:
        if delete:
            pass
            # shutil.rmtree(folder)
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
        # only add directories which dont have a tb.v file
        if os.path.exists(f"{FOLDER}/{folder}/tb.v"):
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
    total = 0
    for folder in os.listdir(FOLDER):
        total += 1
    print(f"Performing simulations on {total} modules using {MAX_PROCESSES} processes")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2*MAX_PROCESSES, initargs=(tb_gen_semaphore,))
    futures = []
    i = 0
    for folder in os.listdir(FOLDER):
        futures.append(executor.submit(perform_simulation, f"{FOLDER}/{folder}"))
        i += 1
        if i % 1000 == 0:
            print(f"Submitted {i} simulations to the pool", end="\r")
    print("")
    success = 0
    i = 0
    for future in concurrent.futures.as_completed(futures):
        if future.result():
            success += 1
        i += 1
        if i % 1000 == 0:
            print(f"Completed {i}/{total} simulations, success rate: {success}/{i}", end="\r")
    print(f"Completed {i}/{total} simulations, success rate: {success}/{i}")
    print("Simulations completed")


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
    parser.add_argument("--start_at", help="""
                        Starting point for the data gathering
                        0 = Gather verilog data. Gathers verilog from sources and stores their meta data. (deletes the old one if present)
                        1 = Generate the testbenches. Generates testbenches for the verilog files in the dataset.
                        2 = Run the testbenches. Runs the testbenches to get the output waveforms.
                        3 = Generate waveforms.
                        """, default="1")
    parser.add_argument("--num_processes", help="Number of processes to use for data gathering", default=MAX_PROCESSES)
    parser.add_argument("--max_ports", help="Only use modules with less than or equal to this number of ports", default=MAX_PORTS)
    parser.add_argument("--max_sim_time", help="Maximum simulation time for testbenches in ns", default=100)
    parser.add_argument("count", help="Gives details on the total amount of data available in the dataset", nargs="?", default=False)

    args = parser.parse_args()
    
    FOLDER = args.folder
    start_at = int(args.start_at)
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
    

    if start_at == 0:
        print("Creating dataset")
        gather_verilog_data()
        start_at = 1
    if start_at == 1:
        print("Generating testbenches")
        scripts.tb_gen.init(max_sim_time)
        generate_testbenches()
        start_at = 2
    if start_at == 2:
        print("Performing simulations")
        perform_simulations()
        start_at = 3
    if start_at == 3:
        pass
    

if __name__ == "__main__":
    main()
