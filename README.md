The purpose of this script is to allow the DDoS SOC
to add and remove prefixes from existing AORC customer policies

Additional documentation can be found here
https://nsmomavp045b.corp.intranet:8443/display/SOPP/AORC+Only+Modify+Prefix-list+Script

# DDoS AORC Modify Prefix-List Script

## Overview

This script is designed to allow the DDoS Security Operations Center (SOC) to add and remove prefixes from existing AORC customer policies. It supports both Nokia and Juniper devices and includes features for dry-run and test modes.

## Features

- **Dry-Run Mode**: Generates commands without pushing them to the devices.
- **Test Mode**: Runs the script on test devices instead of production devices.
- **Time Limit**: Ensures the script runs within a specified time limit.
- **User Permissions**: Only users in the `ddosops` group can run the script.
- **Logging**: Logs all user decisions and actions.
- **Locking Mechanism**: Ensures only one instance of the script runs at a time.
- **Cleanup**: Cleans up temporary files upon exit.

## Requirements

- Python 3.12 or later
- Required Python modules: `os`, `sys`, `datetime`, `atexit`, `time`, `fcntl`, `subprocess`, `threading`
- Custom utility functions from `utils.py`

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/ddos-aorc-modify-prefix-script.git
    cd ddos-aorc-modify-prefix-script
    ```

2. Ensure you have Python 3.12 or later installed.

3. Install any required Python modules:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. **Set up the script**:
    - Modify the `script_path` variable to point to the correct directory.
    - Ensure the `group_name` variable is set to the correct user group.

2. **Run the script**:
    ```sh
    python3 main.py
    ```

3. **Script Modes**:
    - **Dry-Run Mode**: Set `dryrun = True` to generate commands without pushing them.
    - **Test Mode**: Set `test_mode = True` to run the script on test devices.

## Configuration

- **Log File Path**: The log file is created in the `__logs__` directory with a timestamp.
- **Lock File Path**: The lock file is created in the `__lock__` directory.
- **Configuration Files**: Commands for Nokia and Juniper devices are written to `__cmds_file_alu__.log` and `__cmds_file_jnpr__.log` respectively.
