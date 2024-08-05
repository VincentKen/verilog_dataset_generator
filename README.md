# DataGathering

This folder contains the necessary files and scripts for generating the dataset for Timing Diagram MLLM.

## Overview

The purpose of the DataGathering folder is to collect and preprocess the data required for training the multi-modal LLM.

## File Structure

The DataGathering folder is organized as follows:

```
DataGathering/
├── scripts/
│   ├── meta_data.py
│   ├── tb_gen.py
│   └── ...
├── data/
│   ├── text/
│   │   ├── text_data_1.txt
│   │   ├── text_data_2.txt
│   │   └── ...
│   └── visuals/
│       ├── image_1.jpg
│       ├── image_2.jpg
│       └── ...
|
|── main.py
└── README.md
```

## Setup
The file `requirements.txt` lists the python dependencies for these scripts, they can be installed with `pip install -r requirements.txt`. There is a chance the installation of `hdlparse` might produce an error.
In that case, first run `pip install setuptools==57.5.0`. This error occurs because `hdlparse` uses `use_2to3`, which is no longer available in newer versions of `setuptools`.  
  
This program requires the vlogTBGen from (EDAUtils)[https://www.edautils.com/VlogTBGen.html]. Make sure to either use `source setup_env.sh` or to run the `setup_env.bat` whenever you use the data gathering script

<!-- 1. Run the `data_collection.py` script to collect the required data from various sources.
2. Use the `data_preprocessing.py` script to preprocess the collected data, ensuring it is in the desired format for training the multi-modal LLM.
3. Customize the scripts as needed to suit your specific data gathering requirements. -->

<!-- ## Contributing

If you would like to contribute to the DataGathering folder, please follow these guidelines:

- Fork the repository and create a new branch for your contributions.
- Make your changes and submit a pull request, clearly describing the purpose and impact of your changes.

## License

This project is licensed under the [MIT License](LICENSE). -->
