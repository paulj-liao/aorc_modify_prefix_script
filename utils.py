#!/bin/env python3

import ipaddress
import subprocess
import os
import grp
import sys
import multiprocessing
import datetime
from subprocess import Popen, PIPE
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from termcolor import colored

horiz_line = "----------------------------------------------------------------------------------------"


def bad_print(text: str) -> None:
    print(colored(text, 'red', attrs=['bold']))

def important_print(text: str) -> None:
    print(colored(text, 'yellow', attrs=['bold']))

def selection_print(text: str) -> None:
    print(colored(text, 'white', 'on_cyan', ['bold']))


def bold_print(text: str) -> None:
    print(colored(text, attrs=['bold']))


def is_member_of_group(group_name: str) -> bool:
    try:
        group_id = grp.getgrnam(group_name).gr_gid
        return group_id in os.getgroups()
    except KeyError:
        return False
    
 
def select_action(menu: Dict[str, str]) -> str:
    while True:
        print(f"\n{horiz_line}\n"
              "What action would you like the program to perform? \n")

        for key, value in menu.items():
            print(f"{key}: {value}")

        choice: str = input("\nPlease enter the number corresponding to the choice you wish to make: ")
        choice = str(choice.strip())
        if choice in menu:
            break
        else:
            bad_print("Invalid choice. Please try again.")
            continue

    return choice


def select_prefix_list(message: str, menu: dict) -> str:
    while True:
        print(f"\n{horiz_line}\n{message}\n")

        for key, value in menu.items():
            print(f"{key}: {value}")

        choice: str = input("\nPlease enter the number corresponding to the choice you wish to make: ")
        choice = str(choice.strip())
        if choice in menu:
            break
        else:
            bad_print("Invalid choice. Please try again.")
            continue

    return choice


def get_customer_prefix_list(devices: List[Dict[str, str]], alu_cmds_file_path: str, jnpr_cmds_file_path: str, dryrun_mode: bool) -> Tuple[str, str]:
    while True:
        # Prompt user to enter a unique identifier for the customer they want to work on
        cust_id: str = input("Please enter the customer name, BusOrg, BAN, MVL: ")
        cust_id_str = str(cust_id.strip())
        selection_print(f"\nSearching for customer \'{cust_id_str}\'...\n")

        # Generate commands to search for the customer's prefix list in the Juniper and Nokia PE routers.
        alu_cmd: str = f"show router policy \"ddos2-dynamic-check\" | match prefix-list | match ignore-case {cust_id}"
        with open(alu_cmds_file_path, 'w+') as file:
            file.write(alu_cmd)
            file.close()
        jnpr_cmd: str = f"show configuration policy-options | display set | match ddos2-dynamic-check | match \"from policy\" | match {cust_id}"
        with open(jnpr_cmds_file_path, 'w+') as file:
            file.write(jnpr_cmd)
            file.close()

        # Search for the customer's prefix list in the devices using roci
        found_prefix_list: List[str] = send_to_devices(search_config, devices, alu_cmds_file_path, jnpr_cmds_file_path, dryrun_mode)
        print(f"Search complete for customer \'{cust_id}\'.\n")
        
        # If no prefix lists were found, prompt the user to enter a different customer identifier
        if not found_prefix_list:
            print("No matches found. Please provide a different customer identifier.")
            continue

        # Sort and Remove duplicates from the list of found prefix lists
        found_prefix_list = sorted(list(set(found_prefix_list)))

        # Create a dictionary with the found policies
        found_prefix_list_dict: Dict[str, str] = {str(i+1): match for i, match in enumerate(found_prefix_list)}

        # Display matching prefix lists and prompt user to select the correct one
        found_prefix_list_dict[str(len(found_prefix_list_dict) + 1)] = "New search"
        user_input: str = select_prefix_list("Which prefix-list would you like to modify?", found_prefix_list_dict)

        # If the user wants to start a new search, restart the loop
        if user_input == str(len(found_prefix_list_dict)):
            print("Starting a new search...")
            continue
        elif user_input in found_prefix_list_dict:
            selected_prefix: str = found_prefix_list_dict[user_input]
            return selected_prefix, cust_id
        else:
            bad_print("Invalid choice. Please try again.")
            print("Starting a new search...")
            continue

def get_prefixes() -> Tuple[List[str], str]:
    while True:
        # Prompt user to enter prefixes
        print(f"\n{horiz_line}")
        bold_print("Follow instructions below to enter prefixes")
        print("   • Only one prefix per line. Please see example below:")
        print("         example: 1.1.0.0/16")
        print("                  1.1.1.1/32")
        print("   • Prefixes can be entered with or without CIDR notation")
        print("         example: 1.1.1.1 will become 1.1.1.1/32")
        print("   • Single IPs entered with CIDR notation will be converted to network address")
        print("         example: 1.1.1.1/24 will become 1.1.1.0/24")
        print("   • IPv4 and IPv6 prefixes are accepted")
        print()
        bold_print("Press ENTER on an empty line when you are done entering prefixes")
        print(f"{horiz_line}")
        
        prefixes: List[str] = []
        while True:
            prefix: str = input()
            if prefix == "" or prefix == " ":  # If the user presses enter on an empty line, break the loop
                break
            prefixes.append(prefix)

        # Validate the prefixes
        valid_prefixes: List[str] = []
        invalid_prefixes: List[str] = []
        valid_prefixes, invalid_prefixes = parse_prefixes(prefixes)
        
        # If invalid prefixes were entered, call them out to the user
        if invalid_prefixes:
            print(f"\n{horiz_line}")
            bad_print("The following prefixes are invalid and will be omitted.\n")
            for prefix in invalid_prefixes:
                print(prefix)

        # Confirm the valid prefixes with the user
        if valid_prefixes:
            print(f"\n{horiz_line}")
            important_print("The following prefixes appear to be valid. Please confirm before proceeding:")
            print("")
            for prefix in valid_prefixes:
                print(prefix)
            confirmation: str = input("\nAre the prefixes correct? (Y/N): ")
            if confirmation.lower() in ['y', 'yes']:
                return valid_prefixes, confirmation
            else:
                print(f"\n{horiz_line}")
                bad_print("Invlalid entry. Please re-enter the prefixes.")
        else:
            print(f"\n{horiz_line}")
            bad_print("No valid prefixes were entered. Please re-enter all valid prefixes below:\n")



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


def generate_commands(valid_prefixes: List[str], selected_policy: str, add_prefixes: bool, remove_prefixes: bool, test_mode: bool, dryrun: bool) -> Tuple[List[str], List[str], str]:
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
    important_print("This is your last chance to abort before the commands are pushed to the devices.")
    important_print("Please review the commands above before proceeding.")
    if test_mode: 
        bad_print("TEST MODE: Reminder that You are in test mode.")
    if dryrun: 
        bad_print("DRYRUN: Reminder that You are in dryrun mode.")
    confirmation = input("\nAre the commands correct? (Y/N): ")
    if confirmation.lower() != 'y' and confirmation.lower() != 'yes':
        bad_print("User has not confirmed the commands. Exiting program...")
        sys.exit(1)
    
    return cmds_alu, cmds_jnpr, confirmation


def roci(roci_cmd: str) -> List[str]:
    results = subprocess.run(roci_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    results = results.stdout.split("\n")
    return results


def search_config(device: Dict[str, str], alu_cmds_file: str, jnpr_cmds_file: str, dryrun: bool) -> List[str]:
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


def push_changes(device: Dict[str, str], alu_cmds_file: str, jnpr_cmds_file: str, dryrun: bool) -> List[str]:
    output = []
    try:
        # Nokia devices
        if device['manufacturer'] == "Nokia":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={alu_cmds_file}"
        # Juniper devices
        elif device['manufacturer'] == "Juniper":
            roci_cmd = f"roci {device['dns']} -hidecmd -f={jnpr_cmds_file}"
        if not dryrun:
            roci_results = roci(roci_cmd)
            print(f"Commands have been pushed to {device['dns']}")
        else:
            roci_results = [f"DRYRUN: Command not executed on {device}"]
            print(f"DRYRUN: Commands have not been pushed to {device['dns']}")
        for result in roci_results:
            output.append(result)
        
    except Exception as e:
        print(f"Error processing device {device['dns']}: {e}")
    return output


def send_to_devices(purpose: callable, devices: List[Dict[str, str]], alu_cmds_file: str, jnpr_cmds_file: str, dryrun: bool) -> List[str]:
    try:
        job_list = [(device, alu_cmds_file, jnpr_cmds_file, dryrun) for device in devices]
        with multiprocessing.Pool(processes=len(job_list)) as pool:
            results = pool.starmap(purpose, job_list)
        
        # Flatten the list of lists
        output = [prefix for sublist in results for prefix in sublist]
    except Exception as e:
        print(f"Error during multiprocessing: {e}")
        output = []
    return output


def add_to_log(log_file_path: str, log_dict: Dict[str, str], key: str, value: str) -> Dict[str, str]:
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


def write_pid_lock(pid_file_path: str) -> None:
    with open(pid_file_path, 'w') as pid_lock_file:
        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username: str = os.getlogin()
        pid_lock_file.write(f"Timestamp: {timestamp}\n")
        pid_lock_file.write(f"Username: {username}\n")


def read_pid_lock(pid_file_path: str) -> str:
    with open(pid_file_path, 'r') as pid_lock_file:
        contents: str = pid_lock_file.read()
    return contents


def get_time_lapsed(timestamp_str: str):
    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.now()
    time_lapsed = current_time - timestamp
    return time_lapsed







