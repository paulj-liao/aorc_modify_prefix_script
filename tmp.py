import time
import datetime


def get_time_lapsed(timestamp_str):
    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.now()
    time_lapsed = current_time - timestamp
    return time_lapsed


tstamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
time.sleep.wait(10.5)
duration = get_time_lapsed(tstamp)


