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
from utils import print_banner, rich_important_print, rich_bad_print, rich_selection_print, rich_bold_print, rich_print 
from utils import rich_success_print, is_member_of_group
from utils import add_to_log, read_pid_lock, write_pid_lock, get_time_lapsed, get_customer_prefix_list
from utils import send_to_devices, select_action, get_prefixes, generate_commands, push_changes


# Author: Richard Blackwell
# Date: 1 August 2024 
# Version: 0.3.0

# 08/1/2024 - 0.1.0 - Initial version of the script
# 08/31/2024 - 0.2.0 - Incorporated the Rich module for all output
# 09/15/2024 - 0.3.0 - Added launch.sh


test_mode = True # test_mode will ensure that the script only runs on the test devices
dryrun = True # dry_run will ensure that the script only generates the commands but does not push them to the devices
total_time_limit = 600 # Total time limit for the script to run in seconds
group_name = "ddosops" # Group name for the users who are allowed to run this script
tstamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
script_path = "/export/home/rblackwe/scripts/aorc_modify_prefix_script"

# Log file path
log_file_path = (f"{script_path}/__logs__/__log__{tstamp}.txt")
if dryrun or test_mode: log_file_path = (f"{script_path}/__logs__/test_log__{tstamp}.txt")

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
    rich_bad_print(f"Time's up! This program has a time limit of {int(total_time_limit/60)} minute(s). Exiting program.")
    os._exit(1)


# Check if the resource is locked. If it is, wait for it to be released
def lock_resource():
    attempt_limit = 4 # Number of attempts to acquire lock
    wait_time = 2 # Time to wait before retrying
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
                            f"\nThis program is already in use. Only one instance of this script can be run at one time.\n"
                            f"User '{info['Username']}' is already running this program. Time lapsed: {str(time_lapsed)[:8]}\n")
                    rich_bad_print(already_runner_banner)

                    # If the user wants to retry, wait for the specified time before retrying
                    if attempt < attempt_limit - 1:
                        retry = input("Do you want to try again? (Y/YES to retry): ").strip().upper()
                        if retry not in ['Y', 'YES']:
                            rich_bad_print("Exiting program...")
                            sys.exit(1)
                        print(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        rich_bad_print(f"Failed to acquire lock after {attempt_limit} attempts.\n"
                                       "You have reached the maximum number of attempts. Exiting program.")
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
        user_decisions: Dict[str, str] = {}  
        user_decisions = add_to_log(log_file_path, user_decisions, "Username", username)
        user_decisions = add_to_log(log_file_path, user_decisions, "Timestamp", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Print the banner
        print_banner(lumen_banner)
        print()
        if test_mode: rich_important_print("TEST MODE: Reminder that you are in test mode.")
        if dryrun: rich_important_print("DRYRUN MODE: Reminder that you are in dryrun mode.")   
        print_banner(script_banner)

        # Get the customer's prefix-list
        selected_policy: str
        cust_id: str
        selected_policy, cust_id = get_customer_prefix_list(prod_devices, alu_cmds_file_path, jnpr_cmds_file_path, dryrun)
        user_decisions = add_to_log(log_file_path, user_decisions, "Provided Cust ID", cust_id)
        user_decisions = add_to_log(log_file_path, user_decisions, "Selected policy", selected_policy)
        rich_selection_print(f"You have selected: {selected_policy}")

        # Add or remove prefixes
        menu: Dict[str, str] = {  
            "1": "Add prefixes",
            "2": "Remove prefixes"}
        action: str = select_action(menu)
        if action == "1":
            rich_selection_print("You have selected: Add prefixes")
            user_decisions = add_to_log(log_file_path, user_decisions, "Selected action", "Add prefixes")
            add_prefixes: bool = True
            remove_prefixes: bool = False
        elif action == "2":
            rich_selection_print("You have selected: Remove prefixes")
            user_decisions = add_to_log(log_file_path, user_decisions, "Selected action", "Remove prefixes")
            add_prefixes: bool = False
            remove_prefixes: bool = True
        else:
            rich_bad_print(f"Invalid action selection. '{action}' was selected. Please report this error. Exiting program...")
            sys.exit(1)

        # Get the prefixes from the user
        valid_prefixes: List[str]
        prefix_confirm: str
        valid_prefixes, prefix_confirm = get_prefixes()
        rich_selection_print("User has confirmed the prefixes. Proceeding with generating commands...")
        user_decisions = add_to_log(log_file_path, user_decisions, "Provided Prefixes", valid_prefixes)
        user_decisions = add_to_log(log_file_path, user_decisions, "Prefix confirmation", prefix_confirm)
        
        # Generate configuration files
        cmds_alu: List[str]
        cmds_jnpr: List[str]
        config_confirm: str
        cmds_alu, cmds_jnpr, config_confirm = generate_commands(valid_prefixes, selected_policy, add_prefixes, remove_prefixes, test_mode, dryrun)

        user_decisions = add_to_log(log_file_path, user_decisions, "Nokia Configuration", cmds_alu)
        user_decisions = add_to_log(log_file_path, user_decisions, "Juniper Configuration", cmds_jnpr)
        user_decisions = add_to_log(log_file_path, user_decisions, "Configuration confirmation", config_confirm)
        if not config_confirm: 
            rich_selection_print("User has chosen not confimed the configuration changes and the changes will not be pushed to producation devices. Exiting program...")
            sys.exit(0)
        rich_selection_print("User has confirmed the configuration. Proceeding with pushing the changes to the devices...")

        # Write the commands to the configuration files
        with open(alu_cmds_file_path, 'w+') as file:
            for line in cmds_alu:
                file.write(line + "\n")
            file.close()
        with open(jnpr_cmds_file_path, 'w+') as file:
            for line in cmds_jnpr:
                file.write(line + "\n")
            file.close()
        if config_confirm: 
                output = send_to_devices(push_changes, devices, alu_cmds_file_path, jnpr_cmds_file_path, dryrun)
        print("")
        rich_success_print(f"\nConfiguration changes have been pushed to the devices successfully!\n")

        # Print the log of user's decisions
        rich_selection_print(f"Decision log:")
        for key, value in user_decisions.items():
            if key == "Nokia Configuration" or key == "Juniper Configuration":
                print(f"{key}:")
                for line in value:
                    if len(line) > 1:
                        print(line)
            else: 
                print(f"{key}: {value}")

        rich_selection_print("Program Finished. Exiting...")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting program...")
        sys.exit(0)
# END OF SCRIPT


if __name__ == "__main__":
    lock_resource()







