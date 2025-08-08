#!/usr/bin/env python3
"""
XBee Direct USB Flash - Flash XBee via direct USB-TTL connection
"""

import serial
import time
import sys
import os

def check_xbee_connection(device_path="/dev/ttyUSB0"):
    """Check if XBee is connected and responding"""
    
    print(f"Checking XBee connection on {device_path}...")
    
    # Try different baud rates
    baud_rates = [9600, 115200, 38400, 19200]
    
    for baud in baud_rates:
        print(f"Testing at {baud} baud...")
        
        try:
            ser = serial.Serial(device_path, baud, timeout=3)
            time.sleep(2)
            
            # Try AT command mode
            ser.flushInput()
            ser.flushOutput()
            time.sleep(1.5)
            ser.write(b'+++')
            time.sleep(1.5)
            
            response = ser.read(100).decode('utf-8', errors='ignore')
            print(f"  Response: {repr(response)}")
            
            if 'OK' in response:
                print(f"✓ XBee responding at {baud} baud in AT mode")
                
                # Get version info
                ser.write(b'ATVR\r')
                time.sleep(1)
                version = ser.read(100).decode('utf-8', errors='ignore')
                print(f"  Firmware: {repr(version.strip())}")
                
                # Exit AT mode
                ser.write(b'ATCN\r')
                time.sleep(1)
                
                ser.close()
                return baud, "at_mode"
            
            # Check if already in bootloader
            ser.write(b'\r\n')
            time.sleep(1)
            response = ser.read(1000).decode('utf-8', errors='ignore')
            
            if "Gecko Bootloader" in response or "BL >" in response:
                print(f"✓ XBee in bootloader mode at {baud} baud")
                ser.close()
                return baud, "bootloader"
            
            ser.close()
            
        except Exception as e:
            print(f"  Error at {baud}: {e}")
    
    return None, None

def force_bootloader_hardware(device_path="/dev/ttyUSB0", baud_rate=9600):
    """Force bootloader using hardware DTR/RTS control"""
    
    print("Attempting hardware bootloader entry...")
    
    try:
        # Open with DTR/RTS control
        ser = serial.Serial(
            device_path, 
            baud_rate, 
            timeout=5,
            dsrdtr=True,   # Enable DTR/DSR
            rtscts=True    # Enable RTS/CTS
        )
        
        print("Setting DTR low, RTS high...")
        ser.setDTR(False)  # DTR low
        ser.setRTS(True)   # RTS high
        time.sleep(0.5)
        
        print("Sending break signal...")
        ser.send_break(duration=0.25)
        time.sleep(0.5)
        
        print("Setting DTR and DIN low, RTS high...")
        ser.setDTR(False)  # DTR low
        ser.setRTS(True)   # RTS high
        time.sleep(0.5)
        
        # Switch to 115200 for bootloader
        ser.close()
        ser = serial.Serial(device_path, 115200, timeout=5)
        time.sleep(1)
        
        print("Sending carriage return at 115200...")
        ser.write(b'\r')
        time.sleep(2)
        
        response = ser.read(1000).decode('utf-8', errors='ignore')
        print(f"Bootloader response: {repr(response)}")
        
        if "Gecko Bootloader" in response or "BL >" in response:
            print("✓ Hardware bootloader entry successful!")
            ser.close()
            return True
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"✗ Hardware bootloader entry failed: {e}")
        return False

def flash_firmware_direct(firmware_path, device_path="/dev/ttyUSB0"):
    """Flash firmware directly via USB-TTL"""
    
    if not os.path.exists(firmware_path):
        print(f"✗ Firmware file not found: {firmware_path}")
        return False
    
    try:
        print(f"Connecting to bootloader at {device_path}...")
        ser = serial.Serial(device_path, 115200, timeout=30)
        time.sleep(2)
        
        # Get bootloader menu
        ser.write(b'\r')
        time.sleep(1)
        response = ser.read(1000).decode('utf-8', errors='ignore')
        print(f"Bootloader menu: {response}")
        
        if "BL >" not in response and "Gecko Bootloader" not in response:
            print("✗ Not in bootloader mode")
            return False
        
        # Start firmware upload
        print("Starting firmware upload (option 1)...")
        ser.write(b'1')
        time.sleep(2)
        
        # Check if ready for XMODEM
        response = ser.read(100).decode('utf-8', errors='ignore')
        print(f"Upload ready response: {repr(response)}")
        
        # Try XMODEM upload
        try:
            from xmodem import XMODEM
            print("Using XMODEM protocol...")
            
            with open(firmware_path, 'rb') as f:
                def getc(size, timeout=30):
                    return ser.read(size) or None
                
                def putc(data, timeout=30):
                    return ser.write(data)
                
                modem = XMODEM(getc, putc)
                success = modem.send(f)
                
                if success:
                    print("✓ XMODEM transfer completed!")
                else:
                    print("✗ XMODEM transfer failed")
                    return False
                    
        except ImportError:
            print("XMODEM library not available, trying binary upload...")
            
            # Read and upload firmware
            with open(firmware_path, 'rb') as f:
                firmware_data = f.read()
            
            print(f"Uploading {len(firmware_data)} bytes...")
            
            # Upload in 1KB chunks
            chunk_size = 1024
            total_chunks = (len(firmware_data) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(firmware_data), chunk_size):
                chunk = firmware_data[i:i+chunk_size]
                ser.write(chunk)
                
                chunk_num = i // chunk_size + 1
                if chunk_num % 10 == 0:
                    progress = 100 * chunk_num // total_chunks
                    print(f"  Progress: {progress}% ({chunk_num}/{total_chunks})")
                
                time.sleep(0.01)
        
        # Wait for completion
        print("Waiting for firmware processing...")
        time.sleep(10)
        
        response = ser.read(1000).decode('utf-8', errors='ignore')
        print(f"Processing response: {repr(response)}")
        
        # Run firmware (option 2)
        print("Running new firmware (option 2)...")
        ser.write(b'2')
        time.sleep(5)
        
        response = ser.read(1000).decode('utf-8', errors='ignore')
        print(f"Run response: {repr(response)}")
        
        ser.close()
        
        # Test new firmware
        print("Testing new firmware...")
        time.sleep(5)
        
        test_baud, test_mode = check_xbee_connection(device_path)
        if test_baud:
            print(f"✓ XBee responding at {test_baud} baud in {test_mode} mode")
            return True
        else:
            print("⚠ XBee not responding after firmware flash")
            return False
            
    except Exception as e:
        print(f"✗ Firmware flash failed: {e}")
        return False

def main():
    device_path = "/dev/ttyUSB0"
    
    if len(sys.argv) != 2:
        print("Usage: python xbee_usb_flash.py <firmware.gbl>")
        print("Example: python xbee_usb_flash.py XB3-24Z/XB3-24Z_1014-th.gbl")
        sys.exit(1)
    
    firmware_path = sys.argv[1]
    
    print("XBee Direct USB Flash")
    print("====================")
    print(f"Device: {device_path}")
    print(f"Firmware: {firmware_path}")
    print()
    
    # Check if device exists
    if not os.path.exists(device_path):
        print(f"✗ Device {device_path} not found")
        print("Make sure XBee is connected via USB-TTL adapter")
        return
    
    # Step 1: Check current XBee status
    current_baud, current_mode = check_xbee_connection(device_path)
    
    if current_mode == "bootloader":
        print("✓ XBee already in bootloader mode")
    elif current_mode == "at_mode":
        print("XBee in AT mode, attempting to invoke bootloader...")
        
        # Try software bootloader invocation
        try:
            ser = serial.Serial(device_path, current_baud, timeout=5)
            time.sleep(2)
            
            # Enter AT mode and send %P
            ser.write(b'+++\r')
            time.sleep(2)
            ser.write(b'AT%P\r')
            time.sleep(3)
            
            response = ser.read(1000).decode('utf-8', errors='ignore')
            if "Gecko Bootloader" in response:
                print("✓ Software bootloader entry successful")
            else:
                print("Software method failed, trying hardware method...")
                ser.close()
                if not force_bootloader_hardware(device_path, current_baud):
                    print("✗ Could not enter bootloader mode")
                    return
            
            ser.close()
            
        except Exception as e:
            print(f"Error invoking bootloader: {e}")
            return
    else:
        print("XBee not responding, trying hardware bootloader entry...")
        if not force_bootloader_hardware(device_path):
            print("✗ Could not enter bootloader mode")
            return
    
    # Step 2: Flash firmware
    print("\n" + "="*50)
    print("Starting firmware flash...")
    print("="*50)
    
    success = flash_firmware_direct(firmware_path, device_path)
    
    if success:
        print("\n✓ Firmware flash completed successfully!")
    else:
        print("\n✗ Firmware flash failed")

if __name__ == "__main__":
    main()
