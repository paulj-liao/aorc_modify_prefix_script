script_path = "/export/home/rblackwe/scripts/aorc_modify_prefix_script/"
resource_name = f'{script_path}/lock/__user_file__'
lockfile_dir_path = f'{script_path}/lock/__lock_file__'

from resource_lock import LockablePidFile  

lock = LockablePidFile(resource_name, lockfile_dir_path)

token = lock.acquire():
if token is not None:
    # the lock is successfully acquired
    send_file_to_remote_device(.....)

    lock.release(token)
else:
    # failed to acquire lock - print an error message

    print(f"Failed to acquire lock details are : {lock.error_msg}")

