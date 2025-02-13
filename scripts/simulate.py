import os
from scripts import meta_data
import subprocess
from shutil import which

DEBUG = False

def compile(folder):
    '''
    Compile testbench and module together using Icarus Verilog
    '''
    subprocess_args = ["iverilog", f"{folder}/module.v", f"{folder}/tb.v", "-o", f"{folder}/iverilog_out"]
    # the testbench generator does not add a timescale to the testbench which causes the wrong time in the simulation output
    # it also does not add code for creating the vcd file
    with open(os.path.join(folder, "tb.v"), "r+") as f:
        content = f.read()
        f.seek(0, 0)
        # content always ends with `endmodule` so we can just add the code before that
        content = content.replace("endmodule", "initial begin\n$dumpfile(\"dump.vcd\");\n$dumpvars(0, testbench);\nend\nendmodule")
        f.write("`timescale 1ns/1ns\n" + content)

    try:
        if DEBUG:
            with open(os.path.join(folder, "iverilog_stderr"), "w") as err:
                with open(os.path.join(folder, "iverilog_stdout"), "w") as out:
                    subprocess.run(subprocess_args, check=True, stdout=out, stderr=err, timeout=10)
        else:
            subprocess.run(subprocess_args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except Exception as e:
        if DEBUG:
            with open(os.path.join(folder, "iverilog_err.txt"), "w") as f:
                f.write(str(e))
        return False
    return True

def run_simulation(folder):
    '''
    Run the compiled simulation
    '''
    cwd = os.getcwd()
    os.chdir(folder)
    subprocess_args = ["vvp", "iverilog_out"]
    try:
        if DEBUG:
            with open(os.path.join(folder, "vvp_stderr"), "w") as err:
                with open(os.path.join(folder, "vvp_stdout"), "w") as out:
                    subprocess.run(subprocess_args, check=True, stdout=out, stderr=err, timeout=10)
        else:
            subprocess.run(subprocess_args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except Exception as e:
        if DEBUG:
            with open(os.path.join(folder, "vvp_err.txt"), "w") as f:
                f.write(str(e))
        os.chdir(cwd)
        return False
    os.chdir(cwd)
    return True