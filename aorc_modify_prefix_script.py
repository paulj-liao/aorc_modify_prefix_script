#!/bin/env python3.10

import ipaddress
import subprocess
import os
import sys
import multiprocessing
import datetime
import atexit
import time
from subprocess import Popen, PIPE
from datetime import datetime
from typing import List, Dict, Tuple, Optional, TextIO


#Author: Richard Blackwell
#Date: 1 August 2024 
#Version: 0.1.0


debug = False # debug doesn't really do anything since I use vscode
dry_run = True # dry_run will remain True until the script is ready for production

script_path = "/export/home/rblackwe/scripts/aorc_modify_prefix_script/"
tstamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
log_file_path = (f"{script_path}/logs/__log__{tstamp}.txt")
if dry_run: log_file_path = (f"{script_path}/logs/debug/__dryrun_log__{tstamp}.txt")
if debug: log_file_path = (f"{script_path}/logs/debug/__debug_log__{tstamp}.txt")
lock_file_path = (f'{script_path}/lock/__lock_file__')
user_file_path = (f'{script_path}/lock/__user_file__')
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
        os.remove(alu_cmds_file_path)
        os.remove(jnpr_cmds_file_path)
    except OSError as e:
        print(f"Error deleting files: {e}")


def greenprint(text: str) -> None:
    print("\033[92m" + text + "\033[0m")


def redprint(text: str) -> None:
    print("\033[91m" + text + "\033[0m")


def user_choice(menu: dict) -> str:
    print(f"\n{horiz_line}\n"
          "Please enter the number corresponding to the choice you wish to make: \n")

    # Prompt user with choice on what they want the program to do.
    for key, value in menu.items():
        print(f"{key}: {value}")

    choice: str = input("\nPlease enter the number corresponding to the choice you wish to make: ")
    if choice in menu:
        return choice
    else:
        redprint("Invalid choice. Please try again.")
        return choice


def get_customer_prefix_list(devices: List[Dict[str, str]]) -> Tuple[str, str]:
    while True:
        # Prompt user to enter a unique identifier for the customer they want to work on
        cust_id: str = input("Please enter the customer name, BusOrg, BAN, MVL: ")
        greenprint(f"\nSearching for customer \'{cust_id}\'...\n")

        # Using roci to search for the AORC prefix list for this specific customer using the rancid files. There is an 8 hour delay to when these files are updated
        alu_cmd: str = f"show router policy \"ddos2-dynamic-check\" | match prefix-list | match ignore-case {cust_id}"
        with open(alu_cmds_file_path, 'w+') as file:
            file.write(alu_cmd)
        jnpr_cmd: str = f"show configuration policy-options | display set | match ddos2-dynamic-check | match \"from policy\" | match {cust_id}"
        with open(jnpr_cmds_file_path, 'w+') as file:
            file.write(jnpr_cmd)

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
    print("\033[93m   • Only one prefix per line. Please see example below:\033[0m")
    print("         example: 1.1.0.0/16")
    print("                  1.1.1.1/32")
    print("\033[93m   • Prefixes can be entered with or without CIDR notation\033[0m")
    print("         example: 1.1.1.1 will become 1.1.1.1/32m")
    print("\033[93m   • Single IPs entered with CIDR notation will be converted to network address\033[0m")
    print("         example: 1.1.1.1/24 will become 1.1.1.0/24")
    print("\033[93m   • IPv4 and IPv6 prefixes are accepted\033[0m")
    print()
    print("\033[1mPress ENTER on an empty line when you are done entering prefixes\033[0m")
    print(f"{horiz_line}")
    prefixes: List[str] = []
    while True:
        prefix: str = input()
        # If the user presses enter on an empty line, break the loop
        if prefix == "":
            break
        prefixes.append(prefix)
    # Validate the entered prefixes
    valid_prefixes: List[str] = []
    invalid_prefixes: List[str] = []
    valid_prefixes, invalid_prefixes = process_prefixes(prefixes)
    if invalid_prefixes:
        print(f"\n{horiz_line}")
        redprint("The following prefixes are invalid and will be omitted.\n")
        for prefix in invalid_prefixes:
            redprint(prefix)
    # Confirm the valid prefixes with the user
    if valid_prefixes:
        print(f"\n{horiz_line}")
        greenprint("The following prefixes appear to be valid. Please confirm before proceeding:\n")
        for prefix in valid_prefixes:
            greenprint(prefix)
        confirmation: str = input("\nAre the prefixes are correct? (Y/N): ")
        if confirmation.lower() != 'y' and confirmation.lower() != 'yes':
            return get_prefixes()
    else:
        print(f"\n{horiz_line}")
        redprint("No valid prefixes were entered. Please re-enter all valid prefixes below:\n")
        return get_prefixes()

    return valid_prefixes, confirmation


def process_prefixes(raw_list: List[str]) -> Tuple[List[str], List[str]]:
    valid_ips = []
    invalid_ips = []

    for prefix in raw_list:
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

    print(f"\n{horiz_line}")
    print("Commands have been generated for Nokia and Juniper devices. Please review below:")
    print("\nNokia commands:")
    for line in cmds_alu:
        print(line)

    print("\nJuniper commands:")
    for line in cmds_jnpr:
        print(line)

    print(f"\n{horiz_line}")
    print(f"\033[93mThis is your last chance to abort before the commands are pushed to the devices.\033[0m")
    print("Please review the commands above before proceeding.")
    if debug: print("\033[1m\033[91m\nDEBUG: Reminder that You are in debug mode.\033[0m")
    if dry_run: print("\033[1m\033[91m\nDRYRUN: Reminder that You are in dryrun mode.\033[0m")
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
                if len(words) > 2:
                    found_prefix_list.append(words[1])
        # Juniper devices
        elif device['manufacturer'] == "Juniper":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={jnpr_cmds_file}"
            roci_results = roci(roci_cmd)
            for result in roci_results:
                words = result.split(" ")
                if len(words) > 4:
                    found_prefix_list.append(words[5])
    except Exception as e:
        print(f"Error processing device {device['dns']}: {e}")
    return found_prefix_list


def push_changes(device: Dict[str, str], alu_cmds_file: str, jnpr_cmds_file: str) -> List[str]:
    output = []
    try:
        print(f"Pushing commands to {device['dns']}...")
        # Nokia devices
        if device['manufacturer'] == "Nokia":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={alu_cmds_file}"
        # Juniper devices
        elif device['manufacturer'] == "Juniper":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={jnpr_cmds_file}"
        if not dry_run:
            roci_results = roci(roci_cmd)
        else:
            roci_results = [f"Dry run: Command not executed on {device}"]
        for result in roci_results:
            output.append(result)
    except Exception as e:
        print(f"Error processing device {device['dns']}: {e}")
    return output


def send_to_devices(purpose: callable, devices: List[Dict[str, str]], alu_cmds_file: str, jnpr_cmds_file: str) -> List[str]:
    try:
        with multiprocessing.Pool(processes=10) as pool:
            # Use tqdm to display a progress bar
            results = pool.starmap(purpose, [(device, alu_cmds_file, jnpr_cmds_file) 
                for device in devices
            ])
        
        # Flatten the list of lists
        output = [prefix for sublist in results for prefix in sublist]
    except Exception as e:
        print(f"Error during multiprocessing: {e}")
        output = []
    return output


def parse_decisions(user_decisions: Dict[str, List[str]]) -> List[str]:
    log = []
    log.append(horiz_line)
    log.append("SCRIPT LOG")
    log.append(horiz_line)
    if debug: log.append("DEBUG MODE")
    if dry_run: log.append("DRY RUN MODE")
    for key, value in user_decisions.items():
        if isinstance(value, list) and len(value) > 1:
            log.append(f"{key}:")
            for item in value:
                log.append(f"    {item}")
        else:
            log.append(f"{key}: {value}")
    log.append(horiz_line)
    log.append("Configuration changes have been pushed to the devices successfully!")
    log.append(horiz_line)
    return log


#  BEGINNING OF SCRIPT
def main() -> None:
    # Register the cleanup function to be called on program exit
    atexit.register(cleanup_files)
    if debug: 
        devices: List[str] = test_devices
    else: 
        devices: List[str] = prod_devices
    
    # Initialize dictionary to log choices made by the user
    user_decisions: Dict[str, str] = {} 
    user_decisions["Username"] = os.getlogin()
    user_decisions["Timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(lumen_banner)
    print(f"\033[1m{script_banner}\033[0m")

    try:
        # Get the customer's prefix list
        selected_policy: str
        cust_id: str
        selected_policy, cust_id = get_customer_prefix_list(prod_devices)
        greenprint(f"\nYou have selected: {selected_policy}")
        user_decisions["Provided Cust ID"] = cust_id
        user_decisions["Selected policy"] = selected_policy

        # Add or remove prefixes
        menu_add_or_remove: Dict[str, str] = {  
            "1": "Add prefixes",
            "2": "Remove prefixes"}
        user_input: str = user_choice(menu_add_or_remove)
        greenprint(f"\nYou have selected: {menu_add_or_remove[user_input]}")
        if user_input == "1":
            add_prefixes: bool = True
            remove_prefixes: bool = False
        elif user_input == "2":
            add_prefixes = False
            remove_prefixes = True
        user_decisions["Action"] = menu_add_or_remove[user_input]

        # Get the prefixes from the user
        valid_prefixes: List[str]
        prefix_confirm: str
        valid_prefixes, prefix_confirm = get_prefixes()
        greenprint("User has confirmed the prefixes. Proceeding with generating commands...")
        user_decisions["Provided Prefixes"] = valid_prefixes
        user_decisions["Prefix confirmation"] = prefix_confirm
        
        # Generate configuration files
        cmds_alu: List[str]
        cmds_jnpr: List[str]
        config_confirm: str
        cmds_alu, cmds_jnpr, config_confirm = generate_commands(valid_prefixes, selected_policy, add_prefixes, remove_prefixes)
        greenprint("\nUser has confirmed the commands. Proceeding with pushing the commands to the devices...\n")
        user_decisions["Nokia Configuration"] = cmds_alu
        user_decisions["Juniper Configuration"] = cmds_jnpr
        user_decisions["Configuration confirmation"] = config_confirm

        # Write the commands to the configuration files
        with open(alu_cmds_file_path, 'w+') as file:
            for line in cmds_alu:
                file.write(line + "\n")
        with open(jnpr_cmds_file_path, 'w+') as file:
            for line in cmds_jnpr:
                file.write(line + "\n")
        if config_confirm: 
        
        # Push the commands to the devices
            output = send_to_devices(push_changes, devices, alu_cmds_file_path, jnpr_cmds_file_path)
        # if debug: print(output)

        print("\n\n")

        # Log the user's decisions
        log = parse_decisions(user_decisions)
        with open(log_file_path, 'a') as file:
            for line in log: file.write(line + "\n")
        for line in log: 
            print(line)

        print("Exiting program...")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting program...")
        sys.exit(0)

if __name__ == "__main__":
    main()

# END OF SCRIPT





