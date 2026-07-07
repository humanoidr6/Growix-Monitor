import serial
import time
import binascii
from gpiozero import DigitalOutputDevice

DE_RE_PIN = 18

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

def scan_registers():
    flow_control = DigitalOutputDevice(DE_RE_PIN, initial_value=False)
    
    try:
        ser = serial.Serial('/dev/serial0', 9600, timeout=0.5)
    except Exception as e:
        print(f"Failed: {e}")
        return

    print("--- Scanning Holding Registers (0x03) from 0 to 60 ---")
    found_any = False
    
    for reg in range(61):
        # Build Read Holding Register request for 1 register
        request = bytearray([0x01, 0x03, (reg >> 8) & 0xFF, reg & 0xFF, 0x00, 0x01])
        request += calculate_crc(request)
        
        flow_control.on()
        time.sleep(0.005)
        ser.write(request)
        ser.flush()
        flow_control.off()
        
        response = ser.read(7)
        
        if response:
            if len(response) >= 5 and response[1] == 0x03:
                val = int.from_bytes(response[3:5], byteorder='big')
                print(f"Holding Register {reg:04d} (0x{reg:04X}): Value = {val}")
                found_any = True
        
        time.sleep(0.05)
        
    if not found_any:
        print("No valid holding registers found.")
        
    print("\n--- Scanning Input Registers (0x04) from 0 to 60 ---")
    found_input = False
    for reg in range(61):
        # Build Read Input Register request for 1 register
        request = bytearray([0x01, 0x04, (reg >> 8) & 0xFF, reg & 0xFF, 0x00, 0x01])
        request += calculate_crc(request)
        
        flow_control.on()
        time.sleep(0.005)
        ser.write(request)
        ser.flush()
        flow_control.off()
        
        response = ser.read(7)
        
        if response:
            if len(response) >= 5 and response[1] == 0x04:
                val = int.from_bytes(response[3:5], byteorder='big')
                print(f"Input Register {reg:04d} (0x{reg:04X}): Value = {val}")
                found_input = True
                
        time.sleep(0.05)

    if not found_input:
        print("No valid input registers found.")
        
    ser.close()

if __name__ == '__main__':
    scan_registers()
