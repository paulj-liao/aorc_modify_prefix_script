import os
import fcntl
import sys
import time
import signal
from datetime import datetime

lock_file_path = '/export/home/rblackwe/scripts/original_aorc/logs/__lock_file__'
user_file_path = '/export/home/rblackwe/scripts/original_aorc/logs/__user_file__'

def check_and_run_single_instance():
    try:
        # Open the lock file
        lock_file = os.open(lock_file_path, os.O_CREAT | os.O_RDWR)
        try:
            # Try to acquire the exclusive lock
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # If lock is acquired, proceed with the main logic of the program
            print("Lock acquired. Running the program...")

            # Get the current user's username
            username = os.getlogin()
            # Get the current timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Write the username and timestamp to the user file
            with open(user_file_path, 'w+') as user_file:
                user_file.write(f'{username}\n{timestamp}')
            
            # Simulate some work with a sleep
            time.sleep(30)
            
            print("Program finished successfully.")
        except IOError:
            # If the lock is not acquired, another instance is running
            print("Another instance of the program is already running.")
            with open(user_file_path, 'r') as user_file:
                # Read the contents of the user file
                user_file_contents = user_file.read().splitlines()
                
                # Get the last run timestamp from the user file
                last_run_timestamp = user_file_contents[1]
                
                # Convert the last run timestamp to a datetime object
                last_run_datetime = datetime.strptime(last_run_timestamp, '%Y-%m-%d %H:%M:%S')
                
                # Calculate the time elapsed since the last run
                time_elapsed = datetime.now() - last_run_datetime
                
                # Print the last run information
                print(f"Last run by {user_file_contents[0]} at {last_run_timestamp}")
                print(f"Time elapsed since last run: {time_elapsed}")
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        # Ensure the lock file is closed properly
        release_lock()


def release_lock():
    if lock_file_path is not None:
        try:
            fcntl.flock(lock_file_path, fcntl.LOCK_UN)
            os.close(lock_file_path)
            print("Lock released.")
        except Exception as e:
            print(f"Failed to release lock: {e}")


def handle_exit(signum, frame):
    print(f"Received signal {signum}. Releasing lock and exiting.")
    release_lock()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    check_and_run_single_instance()
