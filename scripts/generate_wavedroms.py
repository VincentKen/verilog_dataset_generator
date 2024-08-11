import os
from scripts import meta_data
import subprocess
import json
from utils.vcd2json import WaveExtractor

DEBUG = False

MAX_WAVEDROMS = 25

def _permute(arr):
    '''
    Get all possible permutations of the array
    '''
    if len(arr) == 0:
        return []
    if len(arr) == 1:
        return [arr]
    
    perms = []
    for i in range(len(arr)):
        current = arr[i]
        remaining = arr[:i] + arr[i+1:]
        for p in _permute(remaining):
            perms.append([current] + p)
    
    return perms


def generate_wavedrom(folder):
    '''
    Generate wavedrom for the verilog module in the folder
    '''
    try:
        meta = meta_data.MetaData()
        meta.load(folder)
        if meta.meta is None:
            return False # return False if meta data could not be loaded, with the second value indicating that the folder should be deleted

        signal_paths = []
        for signal in meta.meta["ports"]:
            if signal['name'] in meta.meta["clocks"]: # the vcd2json script needs clocks to be first
                signal_paths.insert(0, f"testbench/inst/{signal['name']}")
                continue
            signal_paths.append(f"testbench/inst/{signal['name']}")

        single_clk_module = len(meta.meta["clocks"]) == 1

        # shuffle the signals around to get waveforms with the signals in different orders
        # if not single_clk_module:
            # vcd2json only supports one clock signal, so if we have none, or multiple
            # we will not use the clock feature and instead randomize all signals
        signal_permutations = _permute(meta.meta["ports"])
        # else:
            # make sure the clock signal remains the first signal
            # signal_permutations = _permute(meta.meta["ports"][1:])
        
        
        if not os.path.exists(os.path.join(folder, "img")):
            os.mkdir(os.path.join(folder, "img"))

        timer_json = os.path.join(folder, 'img/timer.json')

        try:
            extractor = WaveExtractor(os.path.join(folder, "dump.vcd"), timer_json, signal_paths)
            extractor.has_clk = single_clk_module
            extractor.execute()
        except Exception as e:
            if DEBUG:
                error_file = open(os.path.join(folder, "vcd2wavedrom_err.txt"), "w")
                error_file.write(str(e))
                error_file.close()
            return False
        
        # check if file was generated
        if not os.path.exists(os.path.join(folder, timer_json)):
            error_file = open(os.path.join(folder, "vcd2wavedrom_err.txt"), "w")
            error_file.write("Wavedrom json file was not generated\n")
            error_file.write(timer_json)
            error_file.write("\n")
            error_file.write(",".join(signal_paths))
            return False
        
        # read the generated json file and create alternatives with different signal orders
        with open(os.path.join(folder, timer_json), "r") as f:
            wavedrom_json = json.load(f)

        # vcd2json has the tendence to group some signals together for some reason
        # we will split them up
        if single_clk_module:
            new_signals = []
            for signal in wavedrom_json["signal"]:
                if type(signal) == dict and "wave" in signal.keys():
                    new_signals.append(signal)
                elif type(signal) == list:
                    for i, s in enumerate(signal):
                        if type(s) == dict and "name" in s.keys():
                            new_signals.append(s)

            wavedrom_json["signal"] = new_signals
            json.dump(wavedrom_json, open(os.path.join(folder, timer_json), "w"))

        meta.meta["wavedroms"] = []
        for i, perm in enumerate(signal_permutations):
            if perm == meta.meta["ports"]:
                meta.meta['wavedroms'].append({
                    'index': i,
                    'json': 'timer.json',
                    'applied_variation': 'original'
                })
                continue
            new_wavedrom = wavedrom_json.copy()
            new_wavedrom["signal"] = []
            for signal in perm:
                # find the signal in the main wavedrom and add it to the new wavedrom
                for s in wavedrom_json["signal"]:
                    try:
                        if s["name"] == signal['name']:
                            new_wavedrom["signal"].append(s)
                            break
                    except Exception as e:
                        if DEBUG:
                            error_file = open(os.path.join(folder, "wavedrom_perm_err.txt"), "w")
                            error_file.write(str(e))
                            error_file.close()
            with open(os.path.join(folder, f"img/wavedrom_{i}.json"), "w") as f:
                json.dump(new_wavedrom, f)
            meta.meta["wavedroms"].append({
                'index': i,
                'json': f"wavedrom_{i}.json",
                'applied_variation': 'shuffled',
                'shuffled': {'pre': meta.meta["ports"], 'post': perm}})
            
            if i > MAX_WAVEDROMS: # limit the number of permutations since it grows very large with the number of signals
                break

        success_count = 0
        # start creating the corresponding images
        if DEBUG:
            err_out = open(os.path.join(folder, "wavedrom_cli_stderr"), "w")
            out = open(os.path.join(folder, "wavedrom_cli_stdout"), "w")
        else:
            err_out = subprocess.DEVNULL
            out = subprocess.DEVNULL
        for i in range(len(meta.meta["wavedroms"])):
            try:
                wavedrom = meta.meta["wavedroms"][i]
                wavedrom_json = os.path.join(folder, f"img/{wavedrom['json']}")
                wavedrom_png = os.path.join(folder, f"img/wavedrom_{wavedrom['index']}.png")
                subprocess_args = ["wavedrom-cli", "-i", wavedrom_json, "-p", wavedrom_png]
                subprocess.run(subprocess_args, timeout=10, stdout=out, stderr=err_out)
                meta.meta["wavedroms"][i]['png'] = f"wavedrom_{wavedrom['index']}.png"
            except Exception as e:
                if DEBUG:
                    error_file = open(os.path.join(folder, "wavedrom_img_err.txt"), "w")
                    error_file.write(str(e))
                    error_file.close()
                continue
            success_count += 1

        return success_count > 0
    except:
        return False