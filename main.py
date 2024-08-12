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
from termcolor import colored
from utils import bad_print, bold_print, selection_print, is_member_of_group
from utils import add_to_log, read_pid_lock, write_pid_lock, get_time_lapsed, get_customer_prefix_list
from utils import send_to_devices, select_action, get_prefixes, generate_commands, push_changes



#Author: Richard Blackwell
#Date: 1 August 2024 
#Version: 0.1.0



test_mode = False # test_mode will ensure that the script only runs on the test devices
dryrun = True # dry_run will ensure that the script only generates the commands but does not push them to the devices
total_time_limit = 600 # Total time limit for the script to run in seconds
group_name = "ddosops" # Group name for the users who are allowed to run this script
tstamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
script_path = "/export/home/rblackwe/scripts/aorc_modify_prefix_script"

# Log file path
log_file_path = (f"{script_path}/__logs__/__log__{tstamp}.txt")
if dryrun or test_mode: log_file_path = (f"{script_path}/__logs__/__test_log__{tstamp}.txt")

# Lock file paths
lock_file_path = (f'{script_path}/__lock__/__lock_file__')
pid_file_path = (f'{script_path}/__lock__/__pid_file__')

# Configuration files for Nokia and Juniper devices
alu_cmds_file_path = ('./__cmds_file_alu__.log')
jnpr_cmds_file_path = ('./__cmds_file_jnpr__.log')


lumen_banner = """
****************************************************************************************
            
                     ██╗     ██╗   ██╗███╗   ███╗███████╗███╗   ██╗                  
                     ██║     ██║   ██║████╗ ████║██╔════╝████╗  ██║
                     ██║     ██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║
                     ██║     ██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║
                     ███████╗╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║
                     ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝        
                                                                                   
                  ****************************************************               
                  *                      Lumen                       *               
                  *                     Security                     *               
                  *                                                  *               
                  *        DDoS AORC Modify Prefix-List Script       *               
                  *                                                  *               
                  *    For issues with this script, please reach     *               
                  *             out to Richard Blackwell             *               
                  *                                                  *               
                  *           Richard.Blackwell@lumen.com            *               
                  ****************************************************                  
                                                                                    
****************************************************************************************
"""

horiz_line = "----------------------------------------------------------------------------------------"

script_banner = (
    f"{horiz_line}\n"
    "                   The purpose of this script is to allow the DDoS SOC                  \n"
    "           to add and remove prefixes from existing AORC customer's policies            \n\n"
    "                           additional info can be found here:                           \n"
    "https://nsmomavp045b.corp.intranet:8443/display/SOPP/AORC+Only+Modify+Prefix-list+Script\n"       
    f"{horiz_line}\n"
)


# One Nokia and one Juniper spare device that ROCI works with. These devices do not particpate with the local scrubbers.
test_devices = [
  {'manufacturer': 'Nokia',     'dns': '7750-spare.par1'},
  {'manufacturer': 'Juniper',   'dns': 'MX960-spare.hel1'},
]


# Complplete list of production PE routers that participate with the local scrubbers. 
prod_devices = [
    {'manufacturer': 'Juniper', 'dns': 'edge9.sjo1'},
    {'manufacturer': 'Juniper', 'dns': 'edge3.chi10'},
    {'manufacturer': 'Juniper', 'dns': 'edge3.syd1'},
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
        print(f"Error deleting files: {e}")


# Function to Kill the program after the time limit has been reached
def timeout():
    print(f"\n{horiz_line}")
    bad_print(f"Time's up! This program has a time limit of {total_time_limit/60:.2f} minutes.")
    print("Exiting program...")
    os._exit(1)


# Check if the resource is locked. If it is, wait for it to be released
def lock_resource():
    attempt_limit = 4 # Number of attempts to acquire lock
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
                    print(f"\n{horiz_line}")
                    bad_print("This program is already in use. Only one instance of this script can be run at one time.")
                    bad_print(f"User '{info['Username']}' is already running this program. Time lapsed: '{str(time_lapsed)[:8]}'\n{horiz_line}")
                    print("")

                    # If the user wants to retry, wait for the specified time before retrying
                    if attempt < attempt_limit - 1:
                        retry = input("Do you want to try again? (Y/YES to retry): ").strip().upper()
                        if retry not in ['Y', 'YES']:
                            print("Exiting program...")
                            sys.exit(1)
                        print(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"Failed to acquire lock after {attempt_limit} attempts.")
                        print("You have reached the maximum number of attempts. Exiting.")
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
            print(f"You do not have sufficient permission to run this program. User '{username}' must be a member of the '{group_name}' group.")
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
        print(lumen_banner)
        if test_mode: bad_print("TEST MODE: Reminder that you are in test mode.")
        if dryrun: bad_print("DRYRUN MODE: Reminder that you are in dryrun mode.")   
        bold_print(f"\n{script_banner}")

        # Get the customer's prefix-list
        selected_policy: str
        cust_id: str
        selected_policy, cust_id = get_customer_prefix_list(prod_devices, alu_cmds_file_path, jnpr_cmds_file_path, dryrun)
        selection_print(f"\nYou have selected: {selected_policy}")
        user_decisions = add_to_log(log_file_path, user_decisions, "Provided Cust ID", cust_id)
        user_decisions = add_to_log(log_file_path, user_decisions, "Selected policy", selected_policy)

        # Add or remove prefixes
        menu: Dict[str, str] = {  
            "1": "Add prefixes",
            "2": "Remove prefixes"}
        action: str = select_action(menu)
        if action == "1":
            selection_print("\nYou have selected: Add prefixes")
            user_decisions = add_to_log(log_file_path, user_decisions, "Selected action", "Add prefixes")
            add_prefixes: bool = True
            remove_prefixes: bool = False
        elif action == "2":
            selection_print("\nYou have selected: Remove prefixes")
            user_decisions = add_to_log(log_file_path, user_decisions, "Selected action", "Remove prefixes")
            add_prefixes: bool = False
            remove_prefixes: bool = True
        else:
            print("Invalid action selection. Please report this error. Exiting program...")
            sys.exit(1)

        # Get the prefixes from the user
        valid_prefixes: List[str]
        prefix_confirm: str
        valid_prefixes, prefix_confirm = get_prefixes()
        selection_print("\nUser has confirmed the prefixes. Proceeding with generating commands...")
        user_decisions = add_to_log(log_file_path, user_decisions, "Provided Prefixes", valid_prefixes)
        user_decisions = add_to_log(log_file_path, user_decisions, "Prefix confirmation", prefix_confirm)
        
        # Generate configuration files
        cmds_alu: List[str]
        cmds_jnpr: List[str]
        config_confirm: str
        cmds_alu, cmds_jnpr, config_confirm = generate_commands(valid_prefixes, selected_policy, add_prefixes, remove_prefixes, test_mode, dryrun)

        selection_print(f"\nUser has confirmed the commands. Proceeding with pushing the commands to the devices...")
        user_decisions = add_to_log(log_file_path, user_decisions, "Nokia Configuration", cmds_alu)
        user_decisions = add_to_log(log_file_path, user_decisions, "Juniper Configuration", cmds_jnpr)
        user_decisions = add_to_log(log_file_path, user_decisions, "Configuration confirmation", config_confirm)

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
        print(f"\n{horiz_line}")
        selection_print("Configuration changes have been pushed to the devices successfully!")
        print(f"{horiz_line}\n")

        # Print the log of user's decisions
        selection_print(f"Log of user's decisions:\n")
        for key, value in user_decisions.items():
            if key == "Nokia Configuration" or key == "Juniper Configuration":
                print(f"{key}:")
                for line in value:
                    if len(line) > 1:
                        print(line)
            else: 
                print(f"{key}: {value}")

        
        print(f"\n{horiz_line}")
        selection_print("Program Finished. Exiting...")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting program...")
        sys.exit(0)
# END OF SCRIPT


if __name__ == "__main__":
    lock_resource()







