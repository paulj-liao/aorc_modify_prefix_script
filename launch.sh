#!/bin/bash

# Define paths
PYTHON_APPIMAGE="/export/home/pliao/python3.12.1-cp312-cp312-manylinux2014_x86_64.AppImage"
VENV_PATH="$HOME/.venv/venv_py312_aorc_modify_prefix"
SOURCE_SCRIPT_DIR="/export/home/pliao/scripts/aorc_modify_prefix_script/main.py"
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
    args=""
    if [ "$1" == "dryrun" ]; then
        args="--dryrun"
    elif [ "$1" == "debug" ]; then
        args="--debug"
    elif [ "$1" == "both" ]; then
        args="--dryrun --debug"
    fi
    $VENV_PATH/bin/python3 $SOURCE_SCRIPT_DIR $args
}

# Check if virtual environment exists
if ! [ -d "$VENV_PATH" ]; then
    echo "Please wait while the program is initialized..."
    setup_venv
fi

# Prompt user for mode
echo "Select mode to run the script:"
echo "1. Normal"
echo "2. Dryrun"
echo "3. Debug"
echo "4. Both Dryrun and Debug"
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        run_main_script
        ;;
    2)
        run_main_script "dryrun"
        ;;
    3)
        run_main_script "debug"
        ;;
    4)
        run_main_script "both"
        ;;
    *)
        echo "Invalid choice. Running in normal mode."
        run_main_script
        ;;
esac

