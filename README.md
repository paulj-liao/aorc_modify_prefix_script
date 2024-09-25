# DDoS AORC Modify Prefix-List Script

## Overview

This script is designed to allow the DDoS Security Operations Center (SOC) to add and remove prefixes from existing AORC customer policies. It supports both Nokia and Juniper devices and includes features for dry-run and test modes.

## Confluence documentation

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
- SSH Client settings should support `UTF-8` character encoding. For best results the Terminal should be set to `Xterm`, and a nerd font be installed.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/blackwri/ddos-aorc-modify-prefix-script.git
    ```

2. Ensure you have Python 3.12 or later installed.
   The launch.sh file creates a virtual environment within Nocsup with python3.12 installed in addition to installing the Rich library.


## Usage

1. **User requirements**:
    - User must be a member of the `ddos_ops` group

2. **Run the script**:
    ```sh
    bash launch.sh
    ```
    
4. **Script Modes**:
    - **Dry-Run Mode**: Set `dryrun = True` to generate commands without pushing them.
    - **Test Mode**: Set `test_mode = True` to run the script on test devices.

## Configuration

- **Log File Path**: The log file is created in the `__logs__` directory with a timestamp.
- **Lock File Path**: The lock file is created in the `__lock__` directory.
- **Configuration Files**: Commands for Nokia and Juniper devices are written to `__cmds_file_alu__.log` and `__cmds_file_jnpr__.log` respectively.

## Logging
Logs are stored in the __logs__ directory with a timestamp. If dryrun or test_mode is enabled, logs are prefixed with test_log__.

## Cleanup
Temporary files are cleaned up upon program exit. This includes command files for Nokia and Juniper devices.
