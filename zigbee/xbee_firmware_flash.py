#!/usr/bin/env python3
"""
XBee Bootloader Invoke - Use %P command to enter bootloader
"""

import serial
import time
import sys
import os

def invoke_bootloader_with_percent_p(device_path="/tmp/ttyXBEE"):
    """Try to invoke bootloader using %P command"""
    
    print("Attempting to invoke bootloader with %P command...")
    
    # Try at different baud rates since we don't know current XBee baud
    baud_rates = [115200, 9600, 38400, 19200]
    
    for i, baud in enumerate(baud_rates):
        print(f"\nTrying %P at {baud} baud...")
        
        # Wait for socat to reconnect after previous attempt
        if i > 0:
            print("  Waiting for socat to reconnect...")
            time.sleep(8)  # Wait for socat reconnection
            
            # Wait for device to appear
            timeout = 15
            start_time = time.time()
            while not os.path.exists(device_path) and (time.time() - start_time) < timeout:
                time.sleep(1)
                print("  .", end="", flush=True)
            
            if not os.path.exists(device_path):
                print(f"\n  ✗ Device {device_path} not available")
                continue
            
            print("\n  ✓ Device ready")
        
        try:
            ser = serial.Serial(device_path, baud, timeout=5)
            time.sleep(3)  # Longer initial delay
            
            # Clear buffers
            ser.flushInput()
            ser.flushOutput()
            
            # Send %P command directly (no AT mode needed)
            print("  Sending %P command...")
            ser.write(b'%P\r')
            time.sleep(3)
            
            # Check for bootloader response
            response = ser.read(2000).decode('utf-8', errors='ignore')
            print(f"  Response: {repr(response[:200])}")
            
            if "Gecko Bootloader" in response or "BL >" in response:
                print(f"  ✓ BOOTLOADER ACTIVATED at {baud} baud!")
                
                # Set baud rate to 115200 for bootloader communication
                ser.close()
                
                print("  Connecting to bootloader at 115200 baud...")
                time.sleep(2)
                
                bootloader_ser = serial.Serial(device_path, 115200, timeout=5)
                time.sleep(2)
                
                # Send carriage return to get prompt
                bootloader_ser.write(b'\r')
                time.sleep(1)
                
                bl_response = bootloader_ser.read(1000).decode('utf-8', errors='ignore')
                print(f"  Bootloader prompt: {repr(bl_response)}")
                
                bootloader_ser.close()
                return True
            
            # Also try AT mode + %P
            print("  Trying AT mode + %P...")
            time.sleep(1.5)
            ser.write(b'+++')
            time.sleep(1.5)
            
            at_response = ser.read(100).decode('utf-8', errors='ignore')
            print(f"  AT response: {repr(at_response)}")
            
            if 'OK' in at_response:
                print("  AT mode entered, sending AT%P...")
                ser.write(b'AT%P\r')
                time.sleep(3)
                
                response = ser.read(2000).decode('utf-8', errors='ignore')
                print(f"  AT%P Response: {repr(response[:200])}")
                
                if "Gecko Bootloader" in response or "BL >" in response:
                    print(f"  ✓ BOOTLOADER ACTIVATED via AT%P at {baud} baud!")
                    ser.close()
                    return True
            else:
                print("  No AT response")
            
            ser.close()
            
        except Exception as e:
            print(f"  Error at {baud}: {e}")
    
    return False

def upload_firmware_xmodem(firmware_path, device_path="/tmp/ttyXBEE"):
    """Upload firmware using proper XMODEM protocol"""
    
    if not os.path.exists(firmware_path):
        print(f"✗ Firmware file not found: {firmware_path}")
        return False
    
    try:
        # Try to import xmodem library
        from xmodem import XMODEM
        print("✓ Using xmodem library")
    except ImportError:
        print("⚠ xmodem library not available, trying manual upload...")
        return manual_firmware_upload(firmware_path, device_path)
    
    try:
        print("Connecting to bootloader...")
        ser = serial.Serial(device_path, 115200, timeout=30)
        time.sleep(2)
        
        # Get bootloader prompt
        ser.write(b'\r')
        time.sleep(1)
        response = ser.read(1000).decode('utf-8', errors='ignore')
        print(f"Bootloader: {response}")
        
        if "BL >" not in response and "Gecko Bootloader" not in response:
            print("✗ Not in bootloader mode")
            return False
        
        # Send '1' to start upload
        print("Starting firmware upload...")
        ser.write(b'1')
        time.sleep(2)
        
        # Open firmware file
        with open(firmware_path, 'rb') as f:
            # Setup XMODEM
            def getc(size, timeout=10):
                return ser.read(size) or None
            
            def putc(data, timeout=10):
                return ser.write(data)
            
            modem = XMODEM(getc, putc)
            
            print("Starting XMODEM transfer...")
            success = modem.send(f)
            
            if success:
                print("✓ XMODEM transfer completed!")
                
                # Wait for completion message
                time.sleep(5)
                response = ser.read(1000).decode('utf-8', errors='ignore')
                print(f"Upload result: {response}")
                
                # Send '2' to run firmware
                print("Running new firmware...")
                ser.write(b'2')
                time.sleep(5)
                
                ser.close()
                return True
            else:
                print("✗ XMODEM transfer failed")
                ser.close()
                return False
                
    except Exception as e:
        print(f"✗ XMODEM upload failed: {e}")
        return False

def manual_firmware_upload(firmware_path, device_path="/tmp/ttyXBEE"):
    """Manual firmware upload without xmodem library"""
    
    print("Attempting manual firmware upload...")
    print("⚠ This is less reliable than proper XMODEM")
    
    # Use our previous gentle upload method
    try:
        ser = serial.Serial(device_path, 115200, timeout=10)
        time.sleep(2)
        
        # Send '1' to bootloader
        ser.write(b'1')
        time.sleep(3)
        
        # Read firmware and upload
        with open(firmware_path, 'rb') as f:
            firmware_data = f.read()
        
        print(f"Uploading {len(firmware_data)} bytes...")
        
        # Upload in chunks
        chunk_size = 128
        for i in range(0, len(firmware_data), chunk_size):
            chunk = firmware_data[i:i+chunk_size]
            ser.write(chunk)
            time.sleep(0.01)
            
            if i % (chunk_size * 50) == 0:
                progress = 100 * i // len(firmware_data)
                print(f"  Progress: {progress}%")
        
        print("Upload completed, waiting for processing...")
        time.sleep(10)
        
        # Send '2' to run
        ser.write(b'2')
        time.sleep(5)
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"Manual upload failed: {e}")
        return False

def main():
    device_path = "/tmp/ttyXBEE"
    
    if len(sys.argv) != 2:
        print("Usage: python xbee_bootloader_invoke.py <firmware.gbl>")
        sys.exit(1)
    
    firmware_path = sys.argv[1]
    
    print("XBee Bootloader Invoke & Flash")
    print("==============================")
    print(f"Firmware: {firmware_path}")
    print()
    
    # Step 1: Try to invoke bootloader
    if not invoke_bootloader_with_percent_p(device_path):
        print("✗ Could not invoke bootloader")
        print("\nTroubleshooting:")
        print("1. Check if XBee has any working firmware")
        print("2. Try hardware reset method with DTR/RTS lines")
        print("3. Consider direct USB-serial connection")
        return
    
    print("\n" + "="*50)
    print("BOOTLOADER READY - Starting firmware upload...")
    print("="*50)
    
    # Step 2: Upload firmware
    success = upload_firmware_xmodem(firmware_path, device_path)
    
    if success:
        print("\n✓ Firmware flash completed successfully!")
        print("Testing XBee in 10 seconds...")
        
        time.sleep(10)
        
        # Test XBee
        import subprocess
        subprocess.run(["python3", "xbee_at_test.py", "-b", "115200"])
        
    else:
        print("\n✗ Firmware flash failed")

if __name__ == "__main__":
    main()
