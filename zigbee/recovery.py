#!/usr/bin/env python3
"""
XBee Recovery Script - Try to recover unresponsive XBee with proper socat delays
"""

import serial
import time
import sys
import os

def wait_for_socat_reconnect(device_path="/tmp/ttyXBEE", timeout=30):
    """Wait for socat to recreate the virtual device"""
    print(f"  Waiting for socat to reconnect...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(device_path):
            time.sleep(2)  # Give it a moment to be fully ready
            return True
        time.sleep(1)
        print("  .", end="", flush=True)
    
    print(f"\n  ✗ Timeout waiting for {device_path}")
    return False

def try_recovery_at_baud(baud_rate, device_path="/tmp/ttyXBEE"):
    """Try recovery at specific baud rate"""
    
    print(f"\nTrying bootloader recovery at {baud_rate} baud...")
    
    # Wait for socat to be ready
    if not wait_for_socat_reconnect(device_path):
        return False, None
    
    try:
        ser = serial.Serial(device_path, baud_rate, timeout=5)
        time.sleep(3)  # Longer initial delay
        
        print("  Connected to serial port")
        
        # Try multiple bootloader entry methods
        methods = [
            (b'\r\n', "Basic newline", 2),
            (b'+++', "AT command mode", None),  # Special handling
            (b'AT%F\r', "Direct firmware mode", 3),
            (b'\x7E\x00\x02\x23\x00\xDC', "API break", 2),
            (b'\x00\x00\x00\x00\x00', "Null sequence", 2),
        ]
        
        for cmd, desc, delay in methods:
            print(f"  Trying: {desc}")
            ser.flushInput()
            ser.flushOutput()
            
            # Special handling for +++ command
            if cmd == b'+++':
                time.sleep(1.5)  # Guard time
                ser.write(cmd)
                time.sleep(1.5)  # Guard time
            else:
                ser.write(cmd)
                if delay:
                    time.sleep(delay)
            
            # Read response
            response = ser.read(2000).decode('utf-8', errors='ignore')
            
            if response.strip():
                print(f"  Response: {repr(response[:150])}")
                
                if "Gecko Bootloader" in response:
                    print(f"  ✓ BOOTLOADER FOUND at {baud_rate} baud!")
                    ser.close()
                    return True, "bootloader"
                    
                elif "OK" in response:
                    print(f"  ✓ AT MODE FOUND at {baud_rate} baud!")
                    
                    # Try to force bootloader from AT mode
                    print("  Attempting to force bootloader mode...")
                    ser.write(b'AT%F\r')
                    time.sleep(3)
                    
                    bootloader_response = ser.read(2000).decode('utf-8', errors='ignore')
                    print(f"  Bootloader force response: {repr(bootloader_response[:100])}")
                    
                    if "Gecko Bootloader" in bootloader_response:
                        print("  ✓ Successfully forced into bootloader!")
                        ser.close()
                        return True, "bootloader"
                    
                    ser.close()
                    return True, "at_mode"
                
                elif response and len(response.strip()) > 0:
                    print(f"  ⚠ Unknown response, but XBee is alive!")
                    ser.close()
                    return True, "unknown"
            else:
                print("  No response")
        
        ser.close()
        return False, None
        
    except Exception as e:
        print(f"  ✗ Error at {baud_rate}: {e}")
        return False, None

def main():
    device_path = "/tmp/ttyXBEE"
    
    print("XBee Recovery Script")
    print("===================")
    print("This will try to recover an unresponsive XBee")
    print("Make sure socat is running in another terminal!")
    print()
    
    # Check if socat device exists
    if not os.path.exists(device_path):
        print(f"✗ {device_path} not found!")
        print("Make sure socat is running:")
        print("./xbee_socat_setup.sh your-esp32-ip 8888")
        return
    
    baud_rates = [115200, 9600, 38400, 19200, 57600]
    
    for i, baud in enumerate(baud_rates):
        print(f"\n{'='*50}")
        print(f"Attempt {i+1}/{len(baud_rates)}")
        
        success, mode = try_recovery_at_baud(baud)
        
        if success:
            print(f"\n✓ SUCCESS!")
            print(f"XBee is responding at {baud} baud in {mode} mode")
            
            if mode == "bootloader":
                print("\nYou can now flash firmware:")
                print(f"python gentle_xbee_flash.py XB3-24Z/XB3-24Z_1014-th.gbl")
            elif mode == "at_mode":
                print(f"\nXBee is working! Test with:")
                print(f"python3 xbee_at_test.py -b {baud}")
            
            return
        
        # Add delay between attempts to let socat settle
        if i < len(baud_rates) - 1:
            print(f"  Waiting 10 seconds before next attempt...")
            time.sleep(10)
    
    print(f"\n✗ XBee recovery failed at all baud rates")
    print("\nTroubleshooting steps:")
    print("1. Check ESP32 is powered and running")
    print("2. Check XBee power connections")
    print("3. Try hardware reset of ESP32")
    print("4. Check socat is running and connected")
    print("5. Consider removing XBee and flashing directly via USB-serial")

if __name__ == "__main__":
    main()
