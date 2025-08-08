#!/usr/bin/env python3
"""
XBee AT Command Tester - Test AT commands via virtual serial device
"""

import serial
import time
import sys

def test_xbee_at(device_path="/tmp/ttyXBEE", baud_rate=9600):
    """Test XBee AT commands"""
    
    print(f"Connecting to {device_path} at {baud_rate} baud...")
    
    try:
        # Open serial connection
        ser = serial.Serial(device_path, baud_rate, timeout=3)
        time.sleep(2)  # Let connection stabilize
        
        print("✓ Serial connection opened")
        
        # Clear any existing data
        ser.flushInput()
        ser.flushOutput()
        
        # Enter command mode
        print("\nEntering command mode...")
        print("Waiting 1.5 seconds (guard time)...")
        time.sleep(1.5)
        
        print("Sending +++")
        ser.write(b'+++')  # No CR/LF for command mode entry
        
        print("Waiting 1.5 seconds (guard time)...")
        time.sleep(1.5)
        
        # Check for OK response
        response = ser.read(100).decode('utf-8', errors='ignore')
        print(f"Response: {repr(response)}")
        
        if 'OK' not in response:
            print("⚠ No OK response...")
            return False
        else:
            print("✓ Command mode entered successfully")
        
        # Test AT commands
        commands = [
            ("ATVR", "Firmware version"),
            ("ATSL", "Serial number low"),
            ("ATSH", "Serial number high"), 
            ("ATBD", "Baud rate"),
            ("ATAP", "API mode"),
            ("ATCE", "Coordinator enable"),
            ("ATID", "PAN ID"),
        ]
        
        for cmd, desc in commands:
            print(f"\nTesting {cmd} ({desc}):")
            
            # Clear buffer
            ser.flushInput()
            
            # Send command with CR
            full_cmd = cmd + '\r'
            ser.write(full_cmd.encode())
            print(f"→ Sent: {cmd}")
            
            # Wait for response
            time.sleep(1)
            
            # Read response
            response = ser.read(100).decode('utf-8', errors='ignore').strip()
            if response:
                print(f"← Response: {repr(response)}")
            else:
                print("← No response")
        
        # Exit command mode
        print(f"\nExiting command mode...")
        ser.write(b'ATCN\r')
        time.sleep(1)
        response = ser.read(100).decode('utf-8', errors='ignore')
        print(f"Exit response: {repr(response)}")
        
        ser.close()
        print("\n✓ Test completed")
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
        return False
    except KeyboardInterrupt:
        print("\n^C received")
        if 'ser' in locals():
            ser.close()
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test XBee AT commands")
    parser.add_argument("-d", "--device", default="/tmp/ttyXBEE", help="Serial device path")
    parser.add_argument("-b", "--baud", type=int, default=9600, help="Baud rate")
    
    args = parser.parse_args()
    
    # Test different baud rates if first fails
    baud_rates = [args.baud, 9600, 115200, 38400, 19200]
    
    for baud in baud_rates:
        if baud != args.baud:
            print(f"\n{'='*50}")
            print(f"Trying baud rate: {baud}")
            print(f"{'='*50}")
        
        if test_xbee_at(args.device, baud):
            print(f"\n✓ Success with baud rate: {baud}")
            break
        else:
            print(f"✗ Failed with baud rate: {baud}")
    else:
        print("\n✗ All baud rates failed")
