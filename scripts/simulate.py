import os
from scripts import meta_data
import subprocess
from shutil import which

def compile(folder):
    '''
    Compile testbench and module together using Icarus Verilog
    '''
    subprocess_args = ["iverilog", f"{folder}/module.v", f"{folder}/tb.v", "-o", "iverilog_out"]
    # the testbench generator does not add a timescale to the testbench which causes the wrong time in the simulation output
    # it also does not add code for creating the vcd file
    with open(os.path.join(folder, "tb.v"), "r+") as f:
        content = f.read()
        f.seek(0, 0)
        # content always ends with `endmodule` so we can just add the code before that
        content = content.replace("endmodule", "initial begin\n$dumpfile(\"dump.vcd\");\n$dumpvars(0, testbench);\nend\nendmodule")
        f.write("`timescale 1ns/1ns\n" + content)

    try:
        subprocess.run(subprocess_args, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        with open(os.path.join(folder, "iverilog_err.txt"), "w") as f:
            f.write(str(e))
        return False, False
        

def run_simulation(folder):
    '''
    Run the compiled simulation
    '''
    subprocess_args = ["vvp", "iverilog_out"]
    try:
        subprocess.run(subprocess_args, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        with open(os.path.join(folder, "vvp_err.txt"), "w") as f:
            f.write(str(e))
        return False, False