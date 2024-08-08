import os
from scripts import meta_data
import subprocess
import json

def generate_wavedrom(folder):
    '''
    Generate wavedrom for the verilog module in the folder
    '''
    meta = meta_data.MetaData()
    meta.load(folder)
    if meta.meta is None:
        return False, False # return False if meta data could not be loaded, with the second value indicating that the folder should be deleted
    
    config = {"clocks": meta.meta["clocks"]}
    json.dump(config, open(f"{folder}/config.json", "w"))

    out_file = f"{folder}/main_wavedrom.json"
    subprocess_args = ["python", "-m", "vcd2wavedrom.vcd2wavedrom", "-in", "dump.vcd", "-out", out_file, "-c", f"{folder}/config.json"]
    
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
    if os.path.exists(f"{folder}/wavedrom.json"):
        return True, False
    return False, True