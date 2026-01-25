# SERVO CONTROL API
# Simpel funktion til at åbne lås via ESP32 servo

import serial
import os
import time

def unlock_servo(duration=2):
    """Åbn lås via ESP32 servo"""
    # Find ESP32 servo port (tjek både ttyUSB og ttyACM)
    servo_port = None
    
    # Fingerprint er typisk på ttyUSB0, servo skal være på en anden port
    fingerprint_port = '/dev/ttyUSB0'
    
    # Prøv at finde servo port (ikke fingerprint port)
    possible_ports = []
    for i in range(10):
        possible_ports.extend([f'/dev/ttyUSB{i}', f'/dev/ttyACM{i}'])
    
    for port in possible_ports:
        if os.path.exists(port):
            # Tjek om det ikke er fingerprint porten
            if port != fingerprint_port:
                servo_port = port
                print(f"[SERVO] Fundet servo port: {servo_port}")
                break
    
    if not servo_port:
        # Vis alle tilgængelige ports
        available = [p for p in possible_ports if os.path.exists(p)]
        return {
            "success": False, 
            "error": f"Servo ESP32 ikke fundet. Tilgængelige ports: {available}"
        }
    
    try:
        # Åbn serial forbindelse
        ser = serial.Serial(servo_port, 115200, timeout=5)
        time.sleep(2)  # Vent på ESP32 boot
        
        # Tøm input buffer
        ser.reset_input_buffer()
        
        # Send UNLOCK kommando
        command = f"UNLOCK:{duration}\n"
        print(f"[SERVO] Sender til {servo_port}: {command.strip()}")
        ser.write(command.encode())
        ser.flush()  # Tving send
        
        # Vent på svar (læs flere linjer)
        time.sleep(0.5)
        response_lines = []
        start_time = time.time()
        
        while time.time() - start_time < 3:  # Vent op til 3 sekunder
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    response_lines.append(line)
                    print(f"[SERVO] Modtog: {line}")
                    if "OK" in line or "UNLOCKING" in line:
                        break
            time.sleep(0.1)
        
        ser.close()
        
        response = " ".join(response_lines)
        print(f"[SERVO] Samlet svar: {response}")
        
        if "OK" in response or "UNLOCKING" in response:
            return {"success": True, "message": f"Lås åbnet i {duration} sekunder"}
        else:
            return {"success": False, "error": f"Ingen bekræftelse fra ESP32. Svar: {response}"}
    
    except Exception as e:
        print(f"[SERVO] Fejl: {e}")
        return {"success": False, "error": str(e)}
