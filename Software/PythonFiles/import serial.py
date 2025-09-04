import serial
import time
# --- IMPORTANT: CONFIGURE YOUR SERIAL PORT HERE ---
ARDUINO_PORT = 'COM6'  # <--- CHANGE THIS TO YOUR ARDUINO'S PORT
BAUD_RATE = 9600
# Establish a serial connection (program will crash here if port is wrong/busy)
ser = serial.Serial(ARDUINO_PORT, BAUD_RATE)
print(f"Connected to Arduino on {ARDUINO_PORT}.")

# IMPORTANT: Wait for Arduino to reset
time.sleep(2)

# 1. Ask for the user's name
user_name = input("Hello! What is your name? ")
print(f"Nice to meet you, {user_name}!")

# 2. This 'while True' loop will run forever until you exit the program
while True:
    # 3. Ask for the action
    print(f"\n{user_name}, which action would you like to do?")
    print("  1. Turn on the LED")
    print("  2. Turn off the LED")
    print("  (Type 'exit' to quit)")
    
    user_choice = input("Enter your choice (1 or 2): ")

    # 4. Process the choice and send to Arduino
    if user_choice == '1':
        print("Processing... turning LED on.")
        ser.write(b'1') # Send the byte for '1'
    elif user_choice == '2':
        print("Processing... turning LED off.")
        ser.write(b'2') # Send the byte for '2'
    elif user_choice.lower() == 'exit':
        print("Exiting program. Goodbye!")
        break # This command breaks out of the 'while True' loop
    else:
        print("Invalid input. Please enter 1 or 2.")
        
    # Give Arduino a moment to process the command
    time.sleep(1)

# 5. Close the connection when the loop is broken
ser.close()
print("Serial port closed.")


ser.write(b'2') # Send the byte for '2'
