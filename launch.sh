#!/bin/bash

# Define paths
PYTHON_APPIMAGE="/export/home/rblackwe/python3.12.1-cp312-cp312-manylinux2014_x86_64.AppImage"
VENV_PATH="$HOME/.venv/venv_py312_aorc_modify_prefix"
SOURCE_SCRIPT_DIR="/export/home/rblackwe/scripts/aorc_modify_prefix_script/main.py"
# If you are using the dev_main.py script, uncomment the line below and comment the line above
# SOURCE_SCRIPT_DIR="/export/home/rblackwe/scripts/aorc_modify_prefix_script/dev_main.py"

# Function to create virtual environment and install packages
setup_venv() {
    echo "Setting up virtual environment."
    $PYTHON_APPIMAGE -m venv $VENV_PATH
    $VENV_PATH/bin/python3 -m pip install Rich
}

# Function to run main.py script
run_main_script() {
    $VENV_PATH/bin/python3 $SOURCE_SCRIPT_DIR
}

# Check if virtual environment exists
if ! [ -d "$VENV_PATH" ]; then
    echo "Please wait while the program is initialized..."
    setup_venv
fi

run_main_script

