# DDoS AORC Modify Prefix-List Script

## Overview

This script is designed to allow the DDoS Security Operations Center (SOC) to add and remove prefixes from existing AORC customer policies. It supports both Nokia and Juniper devices and includes features for dry-run and test modes.

## Additional documentation can be found here

https://nsmomavp045b.corp.intranet:8443/display/SOPP/AORC+Only+Modify+Prefix-list+Script

## Features

- **Dry-Run Mode**: Generates commands without pushing them to the devices.
- **Test Mode**: Runs the script on test devices instead of production devices.
- **Time Limit**: Ensures the script runs within a specified time limit.
- **User Permissions**: Only users in the `ddosops` group can run the script.
- **Logging**: Logs all user decisions and actions.
- **Locking Mechanism**: Ensures only one instance of the script runs at a time.
- **Cleanup**: Cleans up temporary files upon exit.
- **IP Version**: Supports both IPv4 and IPv6 prefixes.
- **Multitreading**: Leverages multithreading to speed up large scale network changes.
- **IPaddress cleanup**: Validation checks are performed on all IP prefixes to ensure they are valid network addresses based on CIDR

## Requirements

- Python 3.10 or later
- Required Python modules: `os`, `sys`, `datetime`, `atexit`, `time`, `fcntl`, `subprocess`, `typing`, `threading`, `multiprocessing`, `time`, `ipaddress`, `rich`

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/ddos-aorc-modify-prefix-script.git
    cd ddos-aorc-modify-prefix-script
    ```

2. Ensure you have Python 3.12 or later installed.
   The launch.sh file creates a virtual environment within Nocsup with python3.12 installed in addition to installing the Rich library.


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
