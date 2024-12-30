#!/bin/env python3

import os
import sys
import datetime
import atexit
import time
import fcntl
from subprocess import Popen, PIPE
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import threading
import logging
import argparse
from utils import print_banner, rich_important_print, rich_bad_print, rich_selection_print 
from utils import rich_success_print, is_member_of_group
from utils import read_pid_lock, write_pid_lock, get_time_lapsed, get_customer_prefix_list
from utils import send_to_devices, select_action, get_prefixes, generate_commands, push_changes

# Author: Richard Blackwell
# Date: 23 September 2024 
# Version: 0.2.3

# 08/1/2024 - 0.1.0 - Initial version of the script
# 08/31/2024 - 0.2.0 - Incorporated the Rich module for all output
# 09/15/2024 - 0.2.1 - Added launch.sh. Restricited prefixes larger than /8 from being added
# 09/23/2024 - 0.2.2 - Added ROCI duration timer to log. Hardcoded file permissions
# 10/3/2024 - 0.2.3 - Adopted logging module
# 12/30/2024 - 0.2.4 - Added arg parse for dryrun and debug mode. Fixed logging issue


dryrun = False # dry_run will ensure that the script only generates the commands but does not push them to the devices
test_mode = False # test_mode will ensure that the script only runs on the test devices
total_time_limit = 3600 # Total time limit for the script to run in seconds
group_name = "ddosops" # Group name for the users who are allowed to run this script
tstamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
script_path = "/export/home/pliao/scripts/aorc_modify_prefix_script"

# Ensure the log directory exists
log_dir = os.path.join(script_path, "__logs__")
os.makedirs(log_dir, exist_ok=True)

# Log file path
log_file_path = (f"{log_dir}/log_{tstamp}.txt")
if dryrun or test_mode: log_file_path = (f"{log_dir}/test_log_{tstamp}.txt")

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s || %(name)s || %(levelname)s || %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Lock file paths
lock_file_path = (f'{script_path}/__lock__/__lock_file__')
pid_file_path = (f'{script_path}/__lock__/__pid_file__')

# Configuration files for Nokia and Juniper devices
alu_cmds_file_path = ('./__cmds_file_alu__.log')
jnpr_cmds_file_path = ('./__cmds_file_jnpr__.log')


lumen_banner = f"""
██╗     ██╗   ██╗███╗   ███╗███████╗███╗   ██╗
██║     ██║   ██║████╗ ████║██╔════╝████╗  ██║
██║     ██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║
██║     ██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║
███████╗╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║
╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝

╭──────────────────────────────────────────────────╮
│               Lumen DDoS Security                │
│                                                  │
│        DDoS AORC Modify Prefix-List Script       │
│                                                  │
│    For issues with this script, please reach     │
│             out to Richard Blackwell             │
│                                                  │
│           Richard.Blackwell@lumen.com            │
╰──────────────────────────────────────────────────╯"""

script_banner = f"""
The purpose of this script is to allow the DDoS SOC
to add and remove prefixes from existing AORC customer policies

Additional info can be found here:
https://nsmomavp045b.corp.intranet:8443/display/SOPP/AORC+Only+Modify+Prefix-list+Script"""


# One Nokia and one Juniper spare device that ROCI works with. These devices do not particpate with the local scrubbers.
test_devices = [
  {'manufacturer': 'Nokia',     'dns': '7750-spare.par1'},
  {'manufacturer': 'Juniper',   'dns': 'MX960-spare.hel1'},
]


# Complplete list of production PE routers that participate with the local scrubbers. 
prod_devices = [
    {'manufacturer': 'Juniper', 'dns': 'edge9.sjo1'},
    {'manufacturer': 'Juniper', 'dns': 'edge3.chi10'},
    {'manufacturer': 'Juniper', 'dns': 'edge4.syd1'},
    {'manufacturer': 'Nokia',   'dns': 'ear3.ams1'},
    {'manufacturer': 'Nokia',   'dns': 'msr2.frf1'},
    {'manufacturer': 'Nokia',   'dns': 'msr3.frf1'},
    {'manufacturer': 'Nokia',   'dns': 'msr11.hkg3'},
    {'manufacturer': 'Nokia',   'dns': 'msr12.hkg3'},
    {'manufacturer': 'Nokia',   'dns': 'msr2.lax1'},
    {'manufacturer': 'Nokia',   'dns': 'msr3.lax1'},
    {'manufacturer': 'Nokia',   'dns': 'ear4.lon2'},
    {'manufacturer': 'Nokia',   'dns': 'msr1.nyc1'},
    {'manufacturer': 'Nokia',   'dns': 'ear2.par1'},
    {'manufacturer': 'Nokia',   'dns': 'msr11.sap1'},
    {'manufacturer': 'Nokia',   'dns': 'msr12.sap1'},
    {'manufacturer': 'Nokia',   'dns': 'msr11.sng3'},
    {'manufacturer': 'Nokia',   'dns': 'msr12.sng3'},
    {'manufacturer': 'Nokia',   'dns': 'msr11.tok4'},
    {'manufacturer': 'Nokia',   'dns': 'msr2.wdc12'},
    {'manufacturer': 'Nokia',   'dns': 'msr3.wdc12'},
    {'manufacturer': 'Nokia',   'dns': 'msr1.dal1'}
]

# Function to cleanup temporary files upon program exit
def cleanup_files() -> None:
    try:
        if os.path.exists(alu_cmds_file_path):
            os.remove(alu_cmds_file_path)
        if os.path.exists(jnpr_cmds_file_path):
            os.remove(jnpr_cmds_file_path)
    except OSError as e:
        rich_bad_print(f"Error deleting files: {e}")


# Function to Kill the program after the time limit has been reached
def timeout():
    print()
    if int(total_time_limit) > 60:
        time_limit = f"{int(total_time_limit/60)} minute(s)"
    else:
        time_limit = f"{int(total_time_limit)} seconds"
    rich_bad_print(f"\nTime's up! This program has a time limit of {time_limit}. Exiting program.\n")
    os._exit(1)


# Check if the resource is locked. If it is, wait for it to be released
def lock_resource():
    attempt_limit = 5 # Number of attempts to acquire lock
    wait_time = 5 # Time to wait before retrying
    timer = threading.Timer(total_time_limit, timeout)
    timer.start()   

    try:
        with open(lock_file_path, 'w') as lock_file:
            for attempt in range(attempt_limit):
                # Attempt to acquire the lock
                try:
                    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    write_pid_lock(pid_file_path)
                    # Lock acquired successfully running script
                    main()
                    return
                
                # If the lock is already acquired, display the user who is running the script and the time lapsed
                except IOError:
                    contents = read_pid_lock(pid_file_path)
                    info = {"Username": "unknown", "Timestamp": "unknown"}
                    for line in contents.split('\n'):
                        if line.startswith("Username:"):
                            info["Username"] = line.split("Username: ")[1]
                        elif line.startswith("Timestamp:"):
                            info["Timestamp"] = line.split("Timestamp: ")[1]
                    
                    time_lapsed = get_time_lapsed(info["Timestamp"])
                    # Print the message to the user including the user who is running the script and the time lapsed
                    already_runner_banner = (
                            f"\nFailed to acuqire lock!\nThis program is already in use. Only one instance of this script can be run at one time.\n"
                            f"User '{info['Username']}' is already running this program. Time lapsed: {str(time_lapsed)[:8]}\n")
                    rich_bad_print(already_runner_banner)

                    # If the user wants to retry, wait for the specified time before retrying
                    if (attempt + 1) < attempt_limit:
                        retry = input("Do you want to try again? (Y/YES to retry): ").strip().upper()
                        if retry not in ['Y', 'YES']:
                            rich_bad_print("Exiting program...")
                            sys.exit(1)
                        print(f"Attempt {attempt + 2} of {attempt_limit} to acquire lock.")
                        print(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        rich_bad_print(f"Attempt limit exceeded!\n"
                                       f"Failed to acquire lock after {attempt_limit} attempts. Exiting program.")
                        sys.exit(1)
                
                # Release the lock
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
                    timer.cancel()

    except (FileNotFoundError, KeyboardInterrupt) as e:
        if isinstance(e, FileNotFoundError):
            print(f"Error: {lock_file_path} does not exist.")
        elif isinstance(e, KeyboardInterrupt):
            print("\nProcess interrupted by user. Exiting program...")
        sys.exit(0)


# Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="DDoS AORC Modify Prefix-List Script")
    parser.add_argument('--dryrun', action='store_true', help="Run the script in dryrun mode")
    parser.add_argument('--debug', action='store_true', help="Run the script in debug mode")
    return parser.parse_args()


#  BEGINNING OF SCRIPT
def main() -> None:
    try: # Handle keyboard interrupt

        # Check if the user is a member of the group "ddos_ops"
        username = os.getlogin()
        if not is_member_of_group(group_name):
            rich_bad_print(f"You do not have sufficient permission to run this program.\n"
                           "User '{username}' must be a member of the '{group_name}' group.")
            sys.exit(1)

        # Set the devices to be used based on the test_mode flag
        if test_mode: devices: List[str] = test_devices
        elif dryrun: devices: List[str] = prod_devices
        else: devices: List[str] = prod_devices

        # Register the cleanup function to be called on program exit
        atexit.register(cleanup_files)

        # Initialize dictionary to log choices made by the user
        # Log initial information
        logger.info(f"Username: {username}")
        logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Print the banner
        print_banner(lumen_banner)
        print()
        if test_mode: rich_important_print("TEST MODE: Reminder that you are in test mode. Contact Richard Blackwell for assistance.")
        if dryrun: rich_important_print("DRYRUN MODE: Reminder that you are in dryrun mode. Contact Richard Blackwell for assistance.")   
        print_banner(script_banner)

        # Get the customer's prefix-list
        selected_policy: str
        cust_id: str
        selected_policy, cust_id, search_time = get_customer_prefix_list(prod_devices, alu_cmds_file_path, jnpr_cmds_file_path, dryrun)
        logger.info(f"Provided Cust ID: {cust_id}")
        logger.info(f"Search time (seconds): {int(float(search_time))}")
        logger.info(f"Selected policy: {selected_policy}")
        rich_selection_print(f"You have selected: {selected_policy}")

        # Add or remove prefixes
        menu: Dict[str, str] = {  
            "1": "Add prefixes",
            "2": "Remove prefixes"}
        action: str = select_action(menu)
        if action == "1":
            rich_selection_print("You have selected: Add prefixes")
            logger.info("Selected action: Add prefixes")
            add_prefixes: bool = True
            remove_prefixes: bool = False
        elif action == "2":
            rich_selection_print("You have selected: Remove prefixes")
            logger.info("Selected action: Remove prefixes")
            add_prefixes: bool = False
            remove_prefixes: bool = True
        else:
            rich_bad_print(f"Invalid action selection. '{action}' was selected. Please report this error. Exiting program...")
            logger.error(f"Invalid action selection. '{action}' was selected. Exiting program...")
            sys.exit(1)

        # Get the prefixes from the user
        valid_prefixes: List[str]
        prefix_confirm: str
        valid_prefixes, prefix_confirm = get_prefixes()
        rich_selection_print("User has confirmed the prefixes. Proceeding with generating commands...")
        logger.info(f"Provided Prefixes: {valid_prefixes}")
        logger.info(f"Prefix confirmation: {prefix_confirm}")
        
        # Generate configuration files
        cmds_alu: List[str]
        cmds_jnpr: List[str]
        config_confirm: str
        cmds_alu, cmds_jnpr, config_confirm = generate_commands(valid_prefixes, selected_policy, add_prefixes, remove_prefixes, test_mode, dryrun)

        logger.info(f"Nokia Configuration: {cmds_alu}")
        logger.info(f"Juniper Configuration: {cmds_jnpr}")
        logger.info(f"Configuration confirmation: {config_confirm}")
        if not config_confirm: 
            rich_selection_print("User has chosen not confimed the configuration changes and the changes will not be pushed to producation devices. Exiting program...")
            sys.exit(0)
        rich_selection_print("User has confirmed the configuration. Proceeding with pushing the changes to the devices...")

        # Write the commands to the configuration files
        with open(alu_cmds_file_path, 'w+') as file:
            os.chmod(alu_cmds_file_path, 0o644)
            for line in cmds_alu:
                file.write(line + "\n")
            file.close()
        with open(jnpr_cmds_file_path, 'w+') as file:
            os.chmod(jnpr_cmds_file_path, 0o644)
            for line in cmds_jnpr:
                file.write(line + "\n")
            file.close()
        if config_confirm: 
                output, push_time = send_to_devices(push_changes, devices, alu_cmds_file_path, jnpr_cmds_file_path, dryrun)
                logger.info(f"Config push time (seconds): {int(float(push_time))}")
        print("")
        rich_success_print(f"\nConfiguration changes have been pushed to the devices successfully!\n")

        # Print the log of user's decisions
        def print_log_file(log_file_path: str) -> None:
            try:
                with open(log_file_path, 'r') as log_file:
                    for line in log_file:
                        parts = line.strip().split(" || ")
                        if len(parts) == 4:
                            key_value = parts[3].split(":", 1)
                            if len(key_value) == 2:
                                key, value = key_value
                                if key == "Nokia Configuration" or key == "Juniper Configuration" or key == "Provided Prefixes":
                                    print(f"{key}:")
                                    for line in value.split(","):
                                        print(f"  {line}")
                                else:
                                    print(f"{key}: {value}")
            except FileNotFoundError:
                print(f"Log file not found: {log_file_path}")
            except Exception as e:
                print(f"Error reading log file: {e}")


        rich_selection_print(f"Decision log:")
        print_log_file(log_file_path)

        rich_selection_print("Program Finished. Exiting...")
        logger.info("Program Finished. Exiting...")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting program...")
        logger.info("Process interrupted by user. Exiting program...")
        sys.exit(0)
# END OF SCRIPT


if __name__ == "__main__":
    args = parse_args()
    dryrun = args.dryrun
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        test_mode = args.debug
    lock_resource()
