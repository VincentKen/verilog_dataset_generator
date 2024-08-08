import os
from scripts import meta_data
import subprocess
from shutil import which

def xvlog(folder):
    '''
    Run xvlog on the testbench in the folder to create a snapshot
    '''
    subprocess_args = ["xvlog", f"{folder}/tb.v", f"{folder}/module.v"]
    try:
        proc = subprocess.run(subprocess_args, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(subprocess_args)
        print(f"Error: {e}")
        with open(os.path.join(folder, "xvlog_err.txt"), "w") as f:
            f.write(str(e))
        return False, False
    return True, False


def xelab(folder):
    subprocess_args = ["xelab", "-debug", "typical", "-top", "testbench", "-snapshot", "snapshot"]
    try:
        proc = subprocess.run(subprocess_args, shell=True, check=True, cwd=folder, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(subprocess_args)
        print(f"Error: {e}")
        with open(os.path.join(folder, "xelab_err.txt"), "w") as f:
            f.write(str(e))
        return False, False
    return True, False


def xsim(folder):
    subprocess_args = ["xsim", "snapshot", "-tclbatch", "utils/xsim_cfg.tcl"]
    try:
        proc = subprocess.run(subprocess_args, shell=True, check=True, cwd=folder, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(subprocess_args)
        print(f"Error: {e}")
        with open(os.path.join(folder, "xsim_err.txt"), "w") as f:
            f.write(str(e))
        return False, False
    