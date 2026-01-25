#!/usr/bin/env python3
"""
Serial Bridge - Læser fra ESP32 via USB og sender til backend
Kør dette script på din computer mens ESP32 er forbundet via USB
"""

import serial
import requests
import time
import sys

# Konfiguration
SERIAL_PORT = "/dev/ttyUSB0"  # ESP32 fundet!
BAUDRATE = 115200
BACKEND_URL = "http://localhost:8000"

print("=" * 60)
print("ESP32 SERIAL BRIDGE")
print("=" * 60)
print(f"Serial Port: {SERIAL_PORT}")
print(f"Backend URL: {BACKEND_URL}")
print("=" * 60)
print()

# Find tilgængelige serial ports
print("💡 Tip: Find din ESP32 port:")
print("   Linux/Mac: ls /dev/tty*")
print("   Windows: Check Device Manager")
print()

try:
    # Åbn serial forbindelse
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    print(f"✓ Serial port åbnet: {SERIAL_PORT}")
    time.sleep(2)  # Vent på ESP32 boot
    
    print("Lytter efter fingerprint scans...")
    print("(Læg finger på sensor på ESP32)")
    print()
    
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            # Check for safety warning
            if line.startswith("SAFETY:VOLTAGE:"):
                voltage = float(line.split(":")[2])
                print(f"\n⚠️ SAFETY WARNING! Voltage: {voltage:.2f}V (over 5V limit)")
                print("System disabled for safety!")
                print("-" * 60)
            
            # Check for voltage reading
            elif line.startswith("VOLTAGE:"):
                voltage = float(line.split(":")[1])
                print(f"⚡ Voltage: {voltage:.2f}V")
                
                # Send til backend
                try:
                    requests.post(
                        f"{BACKEND_URL}/api/report-voltage",
                        json={"voltage": voltage},
                        timeout=2
                    )
                except Exception as e:
                    pass  # Ignorer fejl
            
            # Check for enrollment event
            elif line.startswith("ENROLL:SLOT:"):
                slot = int(line.split(":")[2])
                print(f"\n📝 Enrollment færdig! Slot: {slot}")
                
                # Rapporter enrollment til backend
                try:
                    requests.post(
                        f"{BACKEND_URL}/api/report-enrollment",
                        json={"slot": slot, "type": "enrollment"},
                        timeout=2
                    )
                    print(f"✅ Enrollment rapporteret til backend")
                except Exception as e:
                    print(f"❌ Backend fejl: {e}")
                
                print("-" * 60)
            
            # Check for scan result
            elif line.startswith("SLOT:"):
                slot = int(line.split(":")[1])
                print(f"\n🔍 Fingerprint scannet! Slot: {slot}")
                
                # Rapporter scan til backend
                try:
                    # Report scan så webside kan se det
                    requests.post(
                        f"{BACKEND_URL}/api/report-scan",
                        params={"slot": slot},
                        timeout=2
                    )
                    
                    # Check patient match
                    response = requests.post(
                        f"{BACKEND_URL}/esp32/scan",
                        json={"slot": slot},
                        timeout=2
                    )
                    
                    data = response.json()
                    
                    if data.get("match"):
                        print(f"✅ Patient fundet: {data['patient_name']} (ID: {data['patient_id']})")
                    else:
                        print(f"⚠️  Slot {slot} ikke linket til nogen patient endnu")
                    
                except Exception as e:
                    print(f"❌ Backend fejl: {e}")
                
                print("-" * 60)
            
            elif line:
                # Print anden output fra ESP32
                print(f"ESP32: {line}")
        
        time.sleep(0.1)

except serial.SerialException as e:
    print(f"\n❌ Serial port fejl: {e}")
    print("\n💡 Løsninger:")
    print("   1. Check ESP32 er forbundet via USB")
    print("   2. Find korrekt port (ls /dev/tty* eller Device Manager)")
    print("   3. Opdater SERIAL_PORT variabel i koden")
    print("   4. Check permissions (Linux: sudo usermod -a -G dialout $USER)")
    sys.exit(1)

except KeyboardInterrupt:
    print("\n\nAfbryder...")
    ser.close()
    print("Serial port lukket")
    sys.exit(0)
