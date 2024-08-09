import threading

def get_user_name():
    name = input("Please enter your name: ")
    print(f"Hello, {name}!")

def timeout():
    print("\nTime's up! Exiting the program...")
    exit(1)

# Set a timer for 30 seconds
timer = threading.Timer(30.0, timeout)
timer.start()

try:
    get_user_name()
finally:
    timer.cancel()  # Cancel the timer if the user enters their name in time