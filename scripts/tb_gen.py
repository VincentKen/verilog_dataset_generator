import os
from scripts import meta_data
import subprocess
from shutil import which

DEBUG = False

MAX_SIM_TIME = 400 # maximum simulation time in ns

def init(max_sim_time):
    global MAX_SIM_TIME
    MAX_SIM_TIME = max_sim_time
    # check if gentbvlog command can be found and add a warning if not
    if which("gentbvlog") is None:
        print("Warning: gentbvlog command not found. Testbench generation will not work")
        print("Be sure to 'source setup_env.sh' inside the utils/vlogtbgen directory")


def generate_testbench(folder):
    '''
    Generate testbench for the verilog module in the folder
    '''
    global MAX_SIM_TIME
    meta = meta_data.MetaData()
    meta.load(folder)
    if meta.meta is None:
        return False
    name = meta.meta["module_name"]
    in_file = os.path.join(folder, "module.v")
    out_file = os.path.join(folder, "tb.v")
    subprocess_args = ["gentbvlog", "-in", in_file, "-top", name, "-out", out_file, "-max_sim_time", f"{MAX_SIM_TIME}"]
    for clk in meta.meta["clocks"]:
        subprocess_args.extend(["-clk", clk])
    for rst in meta.meta["resets"]:
        subprocess_args.extend(["-rst", rst])
    try:
        if DEBUG:
            with open(os.path.join(folder, "gentbvlog_stderr"), "w") as err:
                with open(os.path.join(folder, "gentbvlog_stdout"), "w") as out:
                    subprocess.run(subprocess_args, stdout=out, stderr=err)
        else:
            subprocess.run(subprocess_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        if DEBUG:
            error_file = open(f"{folder}/gentbvlog_err.txt", "w")
            error_file.write(str(e))
            error_file.close()
        return False
    # check if file was actually created
    if os.path.exists(f"{folder}/tb.v"):
        return True
    return False
    