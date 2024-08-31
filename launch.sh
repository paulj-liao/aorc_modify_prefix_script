#!/bin/bash

### 
#This script will create a virtual environment for python 3.12.1 and install the necessary packages to run the AORC script
###

/export/home/rblackwe/python3.12.1-cp312-cp312-manylinux2014_x86_64.AppImage -m venv ~/.venv/venv_py312

~/.venv/venv_py312/bin/python3 -m pip install Rich

mkdir aorc_script

cp /export/home/rblackwe/scripts/aorc_modify_prefix_script/* ~/aorc_script/

~/.venv/venv_py312/bin/python3 ~/aorc_script/main.py