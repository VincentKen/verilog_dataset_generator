import os
import json
import hdlparse.verilog_parser as vlog
import copy

'''
This script is used to generate a meta.json file that contains the metadata of the verilog modules, the testbenches, and the waveforms, etc.
'''

# Shows the outline of the meta data contents
EMPTY_META = {
    "module_name": "",
    "parameters": [],
    "clocks": [],
    "resets": [],
    "ports": [],
    "code": ""
}

_CLK_NAMES = ["clk", "clock", "clk_i", "clock_i"]
_RST_NAMES = ["rst", "reset", "rst_i", "reset_i", 
              "nreset", "nreset_i", "nrst", 
              "nrst_i", "n_reset", "n_reset_i",
              "n_rst", "n_rst_i", "rst_n", 
              "rst_n_i", "reset_n", "reset_n_i"]
_NOT_CLK_NAMES = ["clk_en", "clock_en", "clk_enable", 
                  "clock_enable", "clk_e", "clock_e", 
                  "clk_enable_i", "clock_enable_i"
                  "clk_enable_n", "clock_enable_n",]

class MetaData:
    '''
    Class for gathering and storing meta data of verilog modules
    MetaData will be stored in meta.json files in the directory provided
    MetaData can also be loaded by providing the directory, then it expects to find meta.json in that directory
    It can analyze provided verilog code. For now it can only extract code in 1995 or 2001 syntax.
    It expects only one module in each provided piece of verilog code.
    '''

    def __init__(self):
        self.dir = None
        self.meta = copy.deepcopy(EMPTY_META)

    def load(self, dir):
        '''
        Load the meta data from the directory
        Expects the presents of a meta.json file in the directory
        Will return None if the file does not exist
        '''
        self.dir = dir
        # if meta.json exists, load it
        if os.path.exists(os.path.join(dir, "meta.json")):
            with open(os.path.join(dir, "meta.json"), "r") as f:
                try:
                    data = json.load(f)
                    self.meta = copy.deepcopy(data)
                except Exception as e:
                    print(f"Error: {e}")
                    print(f"Error loading meta.json in {dir}")
                    print(f"File contents: {f.read()}")
                    return None
            return self.meta
        else:
            return None

    def set_dir(self, dir):
        '''
        Set the directory for the meta_data to be stored in
        '''
        self.dir = dir

    def store(self, dir=None):
        '''
        Store the meta data to the directory
        If a directory is provided, the meta data will be stored in that directory
        If no directory is provided, the meta data will be stored in the directory provided by set_dir()
        '''
        if dir is None:
            dir = self.dir
        if dir is None:
            raise ValueError("No directory provided")
        with open(os.path.join(dir, "meta.json"), "w") as f:
            json.dump(self.meta, f)

    def analyze_code(self, code):
        '''
        Analyze the provided verilog code
        Will not save the meta data to a meta.json, this requires calling store(dir)
        '''
        self.meta = copy.deepcopy(EMPTY_META)
        vlog_ex = vlog.VerilogExtractor()
        try:
             modules = vlog_ex.extract_objects_from_source(code)
        except Exception as e:
            print(f"Error: {e}")
            print(code)
            raise e
        if modules is None or len(modules) == 0:
            return None
        m = modules[0]
        self.meta["code"] = code
        self.meta["module_name"] = m.name
        if hasattr(m, 'generics'):
            for param in m.generics:
                self.meta["parameters"].append(param.name)
        if hasattr(m, 'ports'):
            for signal in m.ports:
                if signal.name.lower() in _CLK_NAMES:
                    self.meta["clocks"].append(signal.name)
                elif signal.name.lower() in _RST_NAMES:
                    self.meta["resets"].append(signal.name)
                self.meta["ports"].append(signal.name)
        else:
            print(f"Error: No ports found in {m.name}")
        return self.meta
            

    def analyze_file(self, file):
        '''
        Analyze the provided verilog file
        Will not save the meta data to a meta.json, this requires calling store()
        Calling store() after analyze_file() will write the meta data to a meta.json file in the verilog file's directory
        '''
        with open(file, "r") as f:
            code = f.read()
        self.analyze_code(code)
        self.dir = os.path.dirname(file)
    
    def analyze_dir(self, dir):
        '''
        Attempts to find a verilog file in the provided directory
        Will analyze the first verilog file found
        Will not save the meta data to a meta.json, this requires calling store()
        '''
        for file in os.listdir(dir):
            if file.endswith(".v"):
                self.analyze_file(os.path.join(dir, file))
                return
