#!/usr/bin/env python3
import serial
import time
import sys

def exit_bootloader_and_run(port='/dev/ttyUSB0'):
    """Connect to bootloader and tell it to run the firmware"""
    
    print("Connecting to bootloader to run firmware...")
    
    ser = serial.Serial(
        port=port,
        baudrate=115200,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=2,
        rtscts=False,
        dsrdtr=False
    )
    
    try:
        # Send carriage return to get menu
        ser.write(b'\r')
        time.sleep(0.5)
        
        response = ser.read(1000)
        print("Bootloader response:")
        print(response.decode('utf-8', errors='ignore'))
        
        # Send '2' to run the firmware
        print("\nSending '2' to run firmware...")
        ser.write(b'2')
        time.sleep(0.5)
        
        response = ser.read(1000)
        if response:
            print("Response:", response.decode('utf-8', errors='ignore'))
        
        print("✓ Firmware should now be running!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ser.close()

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
    exit_bootloader_and_run(port)
