#!/bin/bash

# Define paths
PYTHON_APPIMAGE="/export/home/rblackwe/python3.12.1-cp312-cp312-manylinux2014_x86_64.AppImage"
VENV_PATH="$HOME/.venv/venv_py312"
SOURCE_SCRIPT_DIR="/export/home/rblackwe/scripts/aorc_modify_prefix_script/main.py"

# Function to create virtual environment and install packages
setup_venv() {
    echo "Setting up virtual environment..."
    $PYTHON_APPIMAGE -m venv $VENV_PATH
    $VENV_PATH/bin/python3 -m pip install Rich
}

# Function to run main.py script
run_main_script() {
    # echo "Running main.py script..."
    $VENV_PATH/bin/python3 $SOURCE_SCRIPT_DIR
}

# Check if virtual environment exists
if [ -d "$VENV_PATH" ]; then
    # Try to run main.py script
    if ! run_main_script; then
        run_main_script
        echo "Virtual environment already exists. But there is an error when running the script."
    fi
else
    echo "Please wait while the program is initialized..."
    setup_venv
    run_main_script
fi