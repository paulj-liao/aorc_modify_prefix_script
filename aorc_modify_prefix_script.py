#!/bin/env python3

import ipaddress
import subprocess
import os
import grp
import sys
import multiprocessing
import datetime
import atexit
import time
import fcntl
from subprocess import Popen, PIPE
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from colorama import Fore, Back, Style
import threading

# TODO - Improve the parsing of erroneous user input

#Author: Richard Blackwell
#Date: 1 August 2024 
#Version: 0.1.0


test_mode = True # test_mode will ensure that the script only runs on the test devices
dry_run = True # dry_run will ensure that the script only generates the commands but does not push them to the devices
total_time_limit = 600 # Total time limit for the script to run in seconds


group_name = "ddosops"
tstamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
script_path = "/export/home/rblackwe/scripts/aorc_modify_prefix_script"

# Log file path
log_file_path = (f"{script_path}/__logs__/__log__{tstamp}.txt")
if dry_run or test_mode: log_file_path = (f"{script_path}/__logs__/__test_log__{tstamp}.txt")

# Lock file paths
lock_file_path = (f'{script_path}/.__lock__/__lock_file__')
pid_file_path = (f'{script_path}/.__lock__/__pid_file__')

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
    # {'manufacturer': 'Juniper', 'dns': 'edge9.sjo1'},
    # {'manufacturer': 'Juniper', 'dns': 'edge3.chi10'},
    # {'manufacturer': 'Juniper', 'dns': 'edge3.syd1'},
    # {'manufacturer': 'Nokia',   'dns': 'ear3.ams1'},
    # {'manufacturer': 'Nokia',   'dns': 'msr2.frf1'},
    # {'manufacturer': 'Nokia',   'dns': 'msr3.frf1'},
    # {'manufacturer': 'Nokia',   'dns': 'msr11.hkg3'},
    # {'manufacturer': 'Nokia',   'dns': 'msr12.hkg3'},
    # {'manufacturer': 'Nokia',   'dns': 'msr2.lax1'},
    # {'manufacturer': 'Nokia',   'dns': 'msr3.lax1'},
    # {'manufacturer': 'Nokia',   'dns': 'ear4.lon2'},
    # {'manufacturer': 'Nokia',   'dns': 'msr1.nyc1'},
    # {'manufacturer': 'Nokia',   'dns': 'ear2.par1'},
    # {'manufacturer': 'Nokia',   'dns': 'msr11.sap1'},
    # {'manufacturer': 'Nokia',   'dns': 'msr12.sap1'},
    # {'manufacturer': 'Nokia',   'dns': 'msr11.sng3'},
    # {'manufacturer': 'Nokia',   'dns': 'msr12.sng3'},
    # {'manufacturer': 'Nokia',   'dns': 'msr11.tok4'},
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


def timeout():
    print(f"\n{horiz_line}")
    redprint(f"Time's up! This program has a time limit of {total_time_limit/60:.2f} minutes.")
    print("Exiting program...")
    os._exit(1)


def selection_print(text: str) -> None:
    print("\033[1m" + text + "\033[0m")


def redprint(text: str) -> None:
    print("\033[1m" + "\033[91m" + text + "\033[0m")


def is_member_of_group(group_name: str) -> bool:
    try:
        group_id = grp.getgrnam(group_name).gr_gid
        return group_id in os.getgroups()
    except KeyError:
        return False


def action_choice(menu: Dict[str, str]) -> str:
    while True:
        print(f"\n{horiz_line}\n"
              "What action would you like to perform? \n")

        for key, value in menu.items():
            print(f"{key}: {value}")

        choice: str = input("\nPlease enter the number corresponding to the choice you wish to make: ")
        choice = str(choice.strip())
        if choice in menu:
            break
        else:
            redprint("Invalid choice. Please try again.")
            continue

    return choice


def user_choice(menu: dict) -> str:
    print(f"\n{horiz_line}\n"
          "Please enter the number corresponding to the choice you wish to make: \n")

    # Prompt user with choice on what they want the program to do.
    for key, value in menu.items():
        print(f"{key}: {value}")

    choice: str = input("\nPlease enter the number corresponding to the choice you wish to make: ")
    choice = str(choice.strip())
    if choice in menu:
        return choice
    else:
        redprint("Invalid choice. Please try again.")
        return choice


def get_customer_prefix_list(devices: List[Dict[str, str]]) -> Tuple[str, str]:
    while True:
        # Prompt user to enter a unique identifier for the customer they want to work on
        cust_id: str = input("Please enter the customer name, BusOrg, BAN, MVL: ")
        selection_print(f"\nSearching for customer \'{cust_id}\'...")
        print("")

        # Using roci to search for the AORC prefix list for this specific customer using the rancid files. There is an 8 hour delay to when these files are updated
        alu_cmd: str = f"show router policy \"ddos2-dynamic-check\" | match prefix-list | match ignore-case {cust_id}"
        with open(alu_cmds_file_path, 'w+') as file:
            file.write(alu_cmd)
            file.close()
        jnpr_cmd: str = f"show configuration policy-options | display set | match ddos2-dynamic-check | match \"from policy\" | match {cust_id}"
        with open(jnpr_cmds_file_path, 'w+') as file:
            file.write(jnpr_cmd)
            file.close()

        # Search for the customer's prefix list in the devices
        found_prefix_list: List[str] = send_to_devices(search_config, devices, alu_cmds_file_path, jnpr_cmds_file_path)
        print(f"Search complete for customer \'{cust_id}\'.\n")
        if not found_prefix_list:
            print("No matches found. Please provide a different customer identifier.")
            continue

        # Sort and Remove duplicates from the list of found prefix lists
        found_prefix_list = sorted(list(set(found_prefix_list)))

        # Create a dictionary with the found policies
        found_prefix_list_dict: Dict[str, str] = {str(i+1): match for i, match in enumerate(found_prefix_list)}

        # Display matching prefix lists and prompt user to select the correct one
        found_prefix_list_dict[str(len(found_prefix_list_dict) + 1)] = "New search"
        user_input: str = user_choice(found_prefix_list_dict)
        
        if user_input == str(len(found_prefix_list_dict)):
            print("Starting a new search...")
            continue
        elif user_input in found_prefix_list_dict:
            selected_prefix: str = found_prefix_list_dict[user_input]
            return selected_prefix, cust_id
        else:
            print("Starting a new search...")
            continue


def get_prefixes() -> Tuple[List[str], str]:
    # Prompt user to enter prefixes
    print(f"\n{horiz_line}")
    print("\033[1mFollow instructions below to enter prefixes\033[0m")
    print("   • Only one prefix per line. Please see example below:")
    print("         example: 1.1.0.0/16")
    print("                  1.1.1.1/32")
    print("   • Prefixes can be entered with or without CIDR notation")
    print("         example: 1.1.1.1 will become 1.1.1.1/32")
    print("   • Single IPs entered with CIDR notation will be converted to network address")
    print("         example: 1.1.1.1/24 will become 1.1.1.0/24")
    print("   • IPv4 and IPv6 prefixes are accepted")
    print()
    print("\033[1mPress ENTER on an empty line when you are done entering prefixes\033[0m")
    print(f"{horiz_line}")
    prefixes: List[str] = []
    while True:
        prefix: str = input()
        if prefix == "": # If the user presses enter on an empty line, break the loop
            break
        prefixes.append(prefix)

    # Validate the prefixes
    valid_prefixes: List[str] = []
    invalid_prefixes: List[str] = []
    valid_prefixes, invalid_prefixes = parse_prefixes(prefixes)
    if invalid_prefixes:
        print(f"\n{horiz_line}")
        redprint("The following prefixes are invalid and will be omitted.\n")
        for prefix in invalid_prefixes:
            redprint(prefix)

    # Confirm the valid prefixes with the user
    if valid_prefixes:
        print(f"\n{horiz_line}")
        selection_print("The following prefixes appear to be valid. Please confirm before proceeding:")
        print("")
        for prefix in valid_prefixes:
            print(prefix)
        confirmation: str = input("\nAre the prefixes are correct? (Y/N): ")
        if confirmation.lower() != 'y' and confirmation.lower() != 'yes':
            return get_prefixes()
    
    # If no valid prefixes were entered, prompt the user to re-enter them
    else:
        print(f"\n{horiz_line}")
        redprint("No valid prefixes were entered. Please re-enter all valid prefixes below:\n")
        return get_prefixes()

    return valid_prefixes, confirmation


def parse_prefixes(raw_list: List[str]) -> Tuple[List[str], List[str]]:
    valid_ips = []
    invalid_ips = []

    for prefix in raw_list:
        prefix = str(prefix.strip())
        if len(prefix) > 0: 
            try:
                # Convert the raw prefix into an IP network object
                ip_object = ipaddress.ip_network(prefix, strict=False)
                # Append the network address to the prefix_list
                valid_ips.append(str(ip_object))
            except ValueError:
                # If the prefix is invalid, add it to the invalid_prefixes list
                invalid_ips.append(prefix)
    
    return valid_ips, invalid_ips


def separate_prefixes(valid_ips: List[str]) -> Tuple[List[str], List[str]]:
    ipv4_prefixes: List[str] = []
    ipv6_prefixes: List[str] = []

    for prefix in valid_ips:
        ip_object = ipaddress.ip_network(prefix)
        if ip_object.version == 4:
            ipv4_prefixes.append(str(ip_object))
        elif ip_object.version == 6:
            ipv6_prefixes.append(str(ip_object))

    return ipv4_prefixes, ipv6_prefixes


def generate_commands(valid_prefixes: List[str], selected_policy: str, add_prefixes: bool, remove_prefixes: bool) -> Tuple[List[str], List[str], str]:
    # IMPORTANT: This function only generates modifications to the AORC prefix-lists. It does not modify the AORC policies

    # Nokia commands
    # IMPORTANT: Nokia stores v4 and v6 prefixes in the same prefix-list. Therefore they are added and removed the same way.
    cmds_alu: List[str] = []
    cmds_alu.append("/configure router policy-options abort")
    cmds_alu.append("/configure router policy-options begin")
    # Add prefixes
    if add_prefixes and not remove_prefixes: 
        if valid_prefixes:
            for prefix in valid_prefixes:
                cmds_alu.append(f"/configure router policy-options prefix-list {selected_policy} prefix {prefix} longer")
    # Remove prefixes
    elif remove_prefixes and not add_prefixes: 
        if valid_prefixes:
            for prefix in valid_prefixes:
                cmds_alu.append(f"/configure router policy-options prefix-list {selected_policy} no prefix {prefix} longer")
    cmds_alu.append("/configure router policy-options commit")
    cmds_alu.append("admin save\n")
            
    # Juniper commands
    # IMPORTANT: Juniper stores v4 and v6 prefixes in different prefix-lists. Therefore they are added and removed differently.
    cmds_jnpr: List[str] = []
    v4_prefixes, v6_prefixes = separate_prefixes(valid_prefixes)
    v6_selected_policy = selected_policy[:1] + "ipv6-" + selected_policy[1:] # Add ipv6- to the policy name
    v6_selected_policy = "ipv6-" + selected_policy # Add ipv6- to the policy name
    cmds_jnpr.append("edit private")
    # Add prefixes
    if add_prefixes and not remove_prefixes:
        # IPv4
        if v4_prefixes:
            for prefix in v4_prefixes:
                cmds_jnpr.append(f"set policy-options policy-statement {selected_policy} term BGP from route-filter {prefix} orlonger")
        # IPv6
        if v6_prefixes:
            for prefix in v6_prefixes:
                cmds_jnpr.append(f"set policy-options policy-statement {v6_selected_policy} term BGP from route-filter {prefix} orlonger")
    # Remove prefixes
    elif remove_prefixes and not add_prefixes:
        # IPv4
        if v4_prefixes:
            for prefix in v4_prefixes:
                cmds_jnpr.append(f"delete policy-options policy-statement {selected_policy} term BGP from route-filter {prefix} orlonger")
        # IPv6
        if v6_prefixes:
            for prefix in v6_prefixes:
                cmds_jnpr.append(f"delete policy-options policy-statement {v6_selected_policy} term BGP from route-filter {prefix} orlonger")
    cmds_jnpr.append("commit and-quit\n")

    # Print generated commands for Nokia and Juniper devices
    print(f"\n{horiz_line}")
    print("Commands have been generated for Nokia and Juniper devices. Please review below:")
    
    # Print Nokia commands
    print("\nNokia commands:")
    for line in cmds_alu:
        print(line)

    # Print Juniper commands
    print("\nJuniper commands:")
    for line in cmds_jnpr:
        print(line)

    # Prompt user to review commands before proceeding
    print(f"\n{horiz_line}")
    print(f"\033[93mThis is your last chance to abort before the commands are pushed to the devices.\033[0m")
    print("Please review the commands above before proceeding.")
    if test_mode: 
        print("\033[1m\033[91m\nTEST MODE: Reminder that You are in test mode.\033[0m")
    if dry_run: 
        print("\033[1m\033[91m\nDRYRUN: Reminder that You are in dryrun mode.\033[0m")
    confirmation = input("\nAre the commands correct? (Y/N): ")
    if confirmation.lower() != 'y' and confirmation.lower() != 'yes':
        redprint("User has not confirmed the commands. Restarting program...")
        main()
    
    return cmds_alu, cmds_jnpr, confirmation


def roci(roci_cmd: str) -> List[str]:
    results = subprocess.run(roci_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    results = results.stdout.split("\n")
    return results


def search_config(device: Dict[str, str], alu_cmds_file: str, jnpr_cmds_file: str) -> List[str]:
    found_prefix_list = []
    try:
        print(f"Searching {device['dns']}...")
        # Nokia devices
        if device['manufacturer'] == "Nokia":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={alu_cmds_file}"
            roci_results = roci(roci_cmd)
            for result in roci_results:
                words = result.split("\"")
                if len(words) > 2: # Nokia prefix list names are stored in the 2nd column
                    found_prefix_list.append(words[1])
        # Juniper devices
        elif device['manufacturer'] == "Juniper":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={jnpr_cmds_file}"
            roci_results = roci(roci_cmd)
            for result in roci_results:
                words = result.split(" ")
                if len(words) > 4: # Juniper prefix list are stored in the 5th column
                    found_prefix_list.append(words[5])
    except Exception as e:
        print(f"Error processing device {device['dns']}: {e}")
    return found_prefix_list


def push_changes(device: Dict[str, str], alu_cmds_file: str, jnpr_cmds_file: str) -> List[str]:
    output = []
    try:
        # print(f"Pushing commands to {device['dns']}...")
        # Nokia devices
        if device['manufacturer'] == "Nokia":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={alu_cmds_file}"
        # Juniper devices
        elif device['manufacturer'] == "Juniper":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={jnpr_cmds_file}"
        if not dry_run:
            roci_results = roci(roci_cmd)
        else:
            roci_results = [f"DRYRUN: Command not executed on {device}"]
        for result in roci_results:
            output.append(result)
        print(f"Commands have been pushed to {device['dns']}")
    except Exception as e:
        print(f"Error processing device {device['dns']}: {e}")
    return output


def send_to_devices(purpose: callable, devices: List[Dict[str, str]], alu_cmds_file: str, jnpr_cmds_file: str) -> List[str]:
    try:
        job_list = [(device, alu_cmds_file, jnpr_cmds_file) for device in devices]
        with multiprocessing.Pool(processes=len(job_list)) as pool:
            results = pool.starmap(purpose, job_list)
        
        # Flatten the list of lists
        output = [prefix for sublist in results for prefix in sublist]
    except Exception as e:
        print(f"Error during multiprocessing: {e}")
        output = []
    return output


def add_to_log(log_dict: Dict[str, str], key: str, value: str) -> Dict[str, str]:
        log_dict[key] = value
        try:
            with open(log_file_path, 'a') as file:
                if key == "Nokia Configuration" or key == "Juniper Configuration":
                    file.write(f"{key}:\n")
                    for line in value:
                        file.write(f"{line}\n")
                else:
                    file.write(f"{key}: {value}\n")
                return log_dict
        except Exception as e:
            print(f"An error occurred while writing to log file: {e}")


def write_pid_lock():
    with open(pid_file_path, 'w') as pid_lock_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = os.getlogin()
        pid_lock_file.write(f"Timestamp: {timestamp}\n")
        pid_lock_file.write(f"Username: {username}\n")


def read_pid_lock():
    with open(pid_file_path, 'r') as pid_lock_file:
        contents = pid_lock_file.read()
    return contents


def get_time_lapsed(timestamp_str):
    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.now()
    time_lapsed = current_time - timestamp
    return time_lapsed


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
                    write_pid_lock()
                    # Lock acquired successfully running script
                    main()
                    return
                
                # If the lock is already acquired, display the user who is running the script and the time lapsed
                except IOError:
                    contents = read_pid_lock()
                    info = {"Username": "unknown", "Timestamp": "unknown"}
                    for line in contents.split('\n'):
                        if line.startswith("Username:"):
                            info["Username"] = line.split("Username: ")[1]
                        elif line.startswith("Timestamp:"):
                            info["Timestamp"] = line.split("Timestamp: ")[1]
                    
                    time_lapsed = get_time_lapsed(info["Timestamp"])
                    print(f"\n\033[1m\033[91m{horiz_line}")
                    print("This program is already in use. Only one instance of this script can be run at one time.")
                    print(f"User '{info['Username']}' is already running this program. Time lapsed: '{str(time_lapsed)[:8]}'\n{horiz_line}\033[0m")
                    print("\033[0m")

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

        if test_mode: 
            print("\033[1m\033[91m\nTEST MODE: Reminder that You are in test mode.\033[0m")
            devices: List[str] = test_devices
        elif dry_run:
            print("\033[1m\033[91m\nDRY RUN MODE: Reminder that You are in dry run mode.\033[0m")
            devices: List[str] = prod_devices
        else: 
            devices: List[str] = prod_devices
        
        # Print the banner
        print(lumen_banner)
        print(f"\033[1m{script_banner}\033[0m")

        # Register the cleanup function to be called on program exit
        atexit.register(cleanup_files)

        # Initialize dictionary to log choices made by the user
        user_decisions: Dict[str, str] = {}  
        user_decisions = add_to_log(user_decisions, "Username", username)
        user_decisions = add_to_log(user_decisions, "Timestamp", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Get the customer's prefix list
        selected_policy: str
        cust_id: str
        selected_policy, cust_id = get_customer_prefix_list(prod_devices)
        selection_print(f"\nYou have selected: {selected_policy}")
        user_decisions = add_to_log(user_decisions, "Provided Cust ID", cust_id)
        user_decisions = add_to_log(user_decisions, "Selected policy", selected_policy)

        # Add or remove prefixes
        menu: Dict[str, str] = {  
            "1": "Add prefixes",
            "2": "Remove prefixes"}
        action = action_choice(menu)
        if action == "1":
            selection_print(f"\nYou have selected: Add prefixes")
            user_decisions = add_to_log(user_decisions, "Selected action", "Add prefixes")
            add_prefixes: bool = True
            remove_prefixes: bool = False
        elif action == "2":
            selection_print(f"\nYou have selected: Remove prefixes")
            user_decisions = add_to_log(user_decisions, "Selected action", "Add prefixes")
            add_prefixes: bool = False
            remove_prefixes: bool = True
        

        # Get the prefixes from the user
        valid_prefixes: List[str]
        prefix_confirm: str
        valid_prefixes, prefix_confirm = get_prefixes()
        selection_print(f"\nUser has confirmed the prefixes. Proceeding with generating commands...\033[0m")
        print("\033[0m")
        user_decisions = add_to_log(user_decisions, "Provided Prefixes", valid_prefixes)
        user_decisions = add_to_log(user_decisions, "Prefix confirmation", prefix_confirm)
        
        # Generate configuration files
        cmds_alu: List[str]
        cmds_jnpr: List[str]
        config_confirm: str
        cmds_alu, cmds_jnpr, config_confirm = generate_commands(valid_prefixes, selected_policy, add_prefixes, remove_prefixes)
        print("\033[0m")
        selection_print("User has confirmed the commands. Proceeding with pushing the commands to the devices...")
        print("\033[0m")
        user_decisions = add_to_log(user_decisions, "Nokia Configuration", cmds_alu)
        user_decisions = add_to_log(user_decisions, "Juniper Configuration", cmds_jnpr)
        user_decisions = add_to_log(user_decisions, "Configuration confirmation", config_confirm)

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
                output = send_to_devices(push_changes, devices, alu_cmds_file_path, jnpr_cmds_file_path)
        print("\033[0m")
        print(f"{horiz_line}")
        selection_print("Configuration changes have been pushed to the devices successfully!")
        print(f"{horiz_line}\n")

        # Print the log of user's decisions
        selection_print("Log of user's decisions:")
        print("")
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

if __name__ == "__main__":
    lock_resource()

# END OF SCRIPT





