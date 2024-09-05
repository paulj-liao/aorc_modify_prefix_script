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
from rich import print as rprint
from rich.panel import Panel
from rich.console import Console


console = Console()
panel_width = 100 # Width of the output panels


def rich_bad_print(text: str) -> None:
    rprint(Panel(text, style="bold red", width=panel_width))

def rich_important_print(text: str) -> None:
    rprint(Panel(text, style="bold yellow", width=panel_width))

def rich_selection_print(text: str) -> None:
    rprint(Panel(text, border_style="bold cyan", style = "bold", width=panel_width))

def rich_bold_print(text: str) -> None:
    rprint(Panel(text, style="bold", width=panel_width))

def rich_print(text: str) -> None:
    rprint(Panel(text, width=panel_width))

def rich_success_print(text: str) -> None:
    rprint(Panel(text, style="bold green", width=panel_width, border_style="green on black"))

def make_banner(text: str) -> str:
    banner = ""
    for line in text.split("\n"):
        while len(line) < (int(panel_width) - 4):
            line = f" {line} "
        banner += f"{line}\n"
    return banner

def print_banner(text: str) -> None:
    banner = make_banner(text)
    rprint(Panel(banner, style="bold", width=panel_width))


def is_member_of_group(group_name: str) -> bool:
    try:
        group_id = grp.getgrnam(group_name).gr_gid
        return group_id in os.getgroups()
    except KeyError:
        return False
    
 
def select_action(menu: Dict[str, str]) -> str:
    while True:
        print("Please select an action from the menu below:")
        menu_content = "\n".join([f"{key}: {value}" for key, value in menu.items()])
        panel = Panel(menu_content, width=panel_width)
        console.print(panel)

        choice: str = input("\nPlease enter the number corresponding to the choice you wish to make: ")
        choice = str(choice.strip())
        if choice in menu:
            break
        else:
            rich_bad_print("Invalid choice. Please try again.")

    return choice


def get_customer_prefix_list(devices: List[Dict[str, str]], alu_cmds_file_path: str, jnpr_cmds_file_path: str, dryrun_mode: bool) -> Tuple[str, str]:
    while True:
        # Prompt user to enter a unique identifier for the customer they want to work on
        cust_id: str = input("Please enter the customer name, BusOrg, BAN, MVL: ")
        cust_id_str = str(cust_id.strip())
        rich_selection_print(f"Searching for customer '{cust_id_str}'...")    
        # Generate commands to search for the customer's prefix list in the Juniper and Nokia PE routers.
        alu_cmd: str = f"show router policy \"ddos2-dynamic-check\" | match prefix-list | match ignore-case {cust_id}"
        with open(alu_cmds_file_path, 'w+') as file:
            file.write(alu_cmd)
        jnpr_cmd: str = f"show configuration policy-options | display set | match ddos2-dynamic-check | match \"from policy\" | match {cust_id}"
        with open(jnpr_cmds_file_path, 'w+') as file:
            file.write(jnpr_cmd)    
        # Search for the customer's prefix list in the devices using roci
        found_prefix_list: List[str] = send_to_devices(search_config, devices, alu_cmds_file_path, jnpr_cmds_file_path, dryrun_mode)
        print(f"Search complete for customer '{cust_id}'.\n")

        # If no prefix lists were found, prompt the user to enter a different customer identifier
        if not found_prefix_list:
            rich_bad_print("[bold red]No matches found. Please provide a different customer identifier.[/bold red]")
            continue    
        # Sort and Remove duplicates from the list of found prefix lists
        found_prefix_list = sorted(list(set(found_prefix_list)))    
        # Create a dictionary with the found policies
        found_prefix_list_dict: Dict[str, str] = {str(i+1): match for i, match in enumerate(found_prefix_list)} 
        # Display matching prefix lists and prompt user to select the correct one
        found_prefix_list_dict[str(len(found_prefix_list_dict) + 1)] = "New search"
        menu_content = "\n".join([f"{key}: {value}" for key, value in found_prefix_list_dict.items()])
        while True:
            panel = Panel(f"Which prefix-list would you like to modify?\n\n{menu_content}", width = panel_width)
            console.print(panel)

            user_input: str = input("\nPlease enter the number corresponding to the choice you wish to make: ").strip()

            # If the user wants to start a new search, restart the loop
            if user_input == str(len(found_prefix_list_dict)):
                rich_selection_print("Starting a new search...")
                break
            elif user_input in found_prefix_list_dict:
                selected_prefix: str = found_prefix_list_dict[user_input]
                return selected_prefix, cust_id
            else:
                rich_bad_print("Invalid choice. Please try again")


def get_prefixes() -> Tuple[List[str], str]:
    while True:
        # Prompt user to enter prefixes
        console.print(Panel("Follow instructions below to enter prefixes\n\n"
                            "   • Only one prefix per line. Please see example below:\n"
                            "         example: 1.1.0.0/16\n"
                            "                  1.1.1.1/32\n"
                            "   • Prefixes can be entered with or without CIDR notation\n"
                            "         example: 1.1.1.1 will become 1.1.1.1/32\n"
                            "   • Single IPs entered with CIDR notation will be converted to network address\n"
                            "         example: 1.1.1.1/24 will become 1.1.1.0/24\n"
                            "   • IPv4 and IPv6 prefixes are accepted\n\n"
                            "Press ENTER on an empty line when you are done entering prefixes", 
                            width=panel_width))
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
            console.print(Panel("The following prefixes are invalid and will be omitted.\n\n" + "\n".join(invalid_prefixes), style="bold red", border_style="bold", width=panel_width))

        # Confirm the valid prefixes with the user
        if valid_prefixes:
            console.print(Panel("The following prefixes are valid. Please confirm before proceeding:\n\n" + "\n".join(valid_prefixes), style="bold", border_style="bold", width=panel_width))
            confirmation: str = input("\nAre the prefixes correct? (Y/N): ")
            if confirmation.lower() in ['y', 'yes']:
                return valid_prefixes, confirmation
            else:
                console.print(Panel("Invalid entry. Please re-enter the prefixes.", style="bold red", border_style="bold", width=panel_width))
        else:
            console.print(Panel("No valid prefixes were entered. Please re-enter all valid prefixes below:", style="bold red", border_style="bold", width=panel_width))


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

    while True:
        # Print generated commands for Nokia and Juniper devices
        print("\nCommands have been generated for Nokia and Juniper devices. Please review below:\n")

        # Print Nokia commands
        print("Nokia commands:")
        for line in cmds_alu:
            print(line)

        # Print Juniper commands
        print("Juniper commands:")
        for line in cmds_jnpr:
            print(line)

        # Prompt user to review commands before proceeding
        rich_important_print("This is your last chance to abort before the commands are pushed to production devices.\nPlease review the commands above before proceeding.")
        if test_mode: 
            rich_important_print("TEST MODE: Reminder that You are in test mode.")
        if dryrun: 
            rich_important_print("DRYRUN: Reminder that You are in dryrun mode.")
        confirmation = input("\nAre the commands correct? (Y/N): ")
        if confirmation.lower() in ['y', 'yes']:
            break
        else:
            rich_bad_print("User has aborted. Exiting program.")
            sys.exit(0)

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







