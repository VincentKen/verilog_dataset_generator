import os
import threading
from scripts import meta_data
import subprocess
from shutil import which

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
        return False, False # return False if meta data could not be loaded, with the second value indicating that the folder should be deleted
    name = meta.meta["module_name"]
    in_file = f"{folder}/module.v"
    out_file = f"{folder}/tb.v"
    subprocess_args = ["gentbvlog", "-in", in_file, "-top", name, "-out", out_file, "-max_sim_time", f"{MAX_SIM_TIME}"]
    for clk in meta.meta["clocks"]:
        subprocess_args.extend(["-clk", clk])
    for rst in meta.meta["resets"]:
        subprocess_args.extend(["-rst", rst])
    try:
        # out_file = open(f"{folder}/gentbvlog_out.txt", "w")
        # err_file = open(f"{folder}/gentbvlog_err.txt", "w")
        # cmd_file = open(f"{folder}/gentbvlog_cmd.txt", "w")
        proc = subprocess.run(subprocess_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # cmd_file.write("cmd: {}".format(proc.args))
    except Exception as e:
        print(subprocess_args)
        print(f"Error: {e}")
        return False, False
    # check if file was actually created
    if os.path.exists(f"{folder}/tb.v"):
        return True, False
    return False, True
    