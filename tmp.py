import resource_lock
import time
import sys



script_path = "/export/home/rblackwe/scripts/aorc_modify_prefix_script"
# Lock file paths
lock_file_path = (f'{script_path}/lock/__lock_file__')
pid_file_path = (f'{script_path}/lock/__pid_file__')



lock = resource_lock.ResourceLock(lock_file_path, pid_file_path)
token = lock.acquire()
if token is not None:
    # the lock is successfully acquired
    # Push the commands to the devices
    # output = send_to_devices(push_changes, devices, alu_cmds_file_path, jnpr_cmds_file_path)
    time.sleep(30)
    lock.release(token)
else:
    # failed to acquire lock - print an error message
    print(f"Failed to acquire lock details are : {lock.error_msg}")
    sys.exit(1)