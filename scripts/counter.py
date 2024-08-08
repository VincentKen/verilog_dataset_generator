import os

def count(folder):
    total = 0
    modules = 0
    testbenches = 0
    compilations = 0
    simulations = 0
    for subfolder in os.listdir(folder):
        total += 1
        if os.path.exists(f"{folder}/{subfolder}/module.v"):
            modules += 1
        if os.path.exists(f"{folder}/{subfolder}/tb.v"):
            testbenches += 1
        if os.path.exists(f"{folder}/{subfolder}/iverilog_out"):
            compilations += 1
        if os.path.exists(f"{folder}/{subfolder}/dump.vcd"):
            simulations += 1
    
    print(f"Total dataset folders: {total}")
    print(f"Total modules: {modules}")
    print(f"Total testbenches: {testbenches}")
    print(f"Total compilations: {compilations}")
    print(f"Total simulations: {simulations}")


    
