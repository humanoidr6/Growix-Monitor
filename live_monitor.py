import serial
import time
import sys

DE_RE_PIN = 18

try:
    from gpiozero import DigitalOutputDevice
    flow_control = DigitalOutputDevice(DE_RE_PIN, initial_value=False)
except Exception:
    flow_control = None

def calculate_crc(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for i in range(8):
            if (crc & 1) != 0:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

def read_register(ser, reg_addr):
    request = bytearray([0x01, 0x03, (reg_addr >> 8) & 0xFF, reg_addr & 0xFF, 0x00, 0x01])
    request += calculate_crc(request)
    
    if flow_control:
        flow_control.on()
        time.sleep(0.005)
        
    ser.write(request)
    ser.flush()
    
    if flow_control:
        flow_control.off()
    
    response = ser.read(7)
    if response and len(response) >= 5 and response[1] == 0x03:
        return int.from_bytes(response[3:5], byteorder='big')
    return None

def main():
    try:
        ser = serial.Serial('/dev/serial0', 9600, timeout=0.5)
    except Exception as e:
        print(f"Serial Error: {e}")
        return

    print("\033[2J\033[H", end="") # Clear screen
    print("Starting Live Environmental Telemetry...\n")
    time.sleep(1)

    while True:
        try:
            # Poll registers
            temp_raw = read_register(ser, 0x0013)
            moist_raw = read_register(ser, 0x0012)
            ec = read_register(ser, 0x0014)
            ph_raw = read_register(ser, 0x0006)
            n = read_register(ser, 0x0022)
            p = read_register(ser, 0x0023)
            k = read_register(ser, 0x0024)

            # Clear screen and reset cursor
            print("\033[2J\033[H", end="")
            
            print("\033[1;36m=== 📡 AUTOMATED SOIL MONITORING NODE ===\033[0m\n")
            
            if temp_raw is not None:
                print(f" \033[1;33m🌡️  Temperature:\033[0m      {temp_raw/10.0:5.1f} °C")
            if moist_raw is not None:
                print(f" \033[1;34m💧 Soil Moisture:\033[0m    {moist_raw/10.0:5.1f} %")
            if ec is not None:
                print(f" \033[1;32m⚡ Conductivity:\033[0m     {ec:5d} us/cm")
            if ph_raw is not None:
                print(f" \033[1;35m🧪 pH Level:\033[0m         {ph_raw/100.0:5.2f}")
                
            print("\n\033[1;36m--- 🧪 NPK Nutrients ---\033[0m")
            if n is not None:
                print(f" \033[1;31mN\033[0m (Nitrogen):       {n:5d} mg/kg")
            if p is not None:
                print(f" \033[1;32mP\033[0m (Phosphorus):     {p:5d} mg/kg")
            if k is not None:
                print(f" \033[1;34mK\033[0m (Potassium):      {k:5d} mg/kg")
                
            print("\n\033[90m(Press Ctrl+C to exit. Try gripping the sensor prongs!)\033[0m")
            
            time.sleep(1.5)
            
        except KeyboardInterrupt:
            print("\nExiting telemetry...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
            
    ser.close()

if __name__ == '__main__':
    main()
