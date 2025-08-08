#!/usr/bin/env bash
# XBee Virtual Serial Device Setup for NixOS
# This creates a virtual serial device that bridges to your ESP32 TCP connection

# Configuration
ESP32_IP="${1:-192.168.1.100}"
ESP32_PORT="${2:-8888}"
VIRTUAL_DEVICE="/tmp/ttyXBEE"

echo "Setting up virtual serial device for XBee..."
echo "ESP32 IP: $ESP32_IP"
echo "ESP32 Port: $ESP32_PORT" 
echo "Virtual Device: $VIRTUAL_DEVICE"

# Check if socat is available
if ! command -v socat &> /dev/null; then
    echo "Error: socat not found"
    echo "Install with: nix-env -iA nixpkgs.socat"
    echo "Or add socat to your NixOS configuration"
    exit 1
fi

# Kill any existing socat processes using our device
echo "Cleaning up existing connections..."
pkill -f "socat.*$VIRTUAL_DEVICE" 2>/dev/null || true
sleep 1

# Remove existing device file
rm -f "$VIRTUAL_DEVICE"

# Create the virtual serial device with auto-restart
echo "Creating virtual serial device with auto-restart..."
echo "Press Ctrl+C to stop"

# Function to run socat with retry
run_socat() {
    while true; do
        echo "Starting socat bridge..."
        socat -d -d \
            PTY,link="$VIRTUAL_DEVICE",raw,echo=0,waitslave \
            TCP:"$ESP32_IP":"$ESP32_PORT",reuseaddr,keepalive,keepidle=30,keepintvl=10,keepcnt=3
        
        echo "Connection lost, retrying in 1 second..."
        sleep 1
    done
}

# Trap Ctrl+C to clean exit
trap 'echo "Stopping..."; pkill -P $; exit 0' INT

# Run with auto-restart
run_socat
