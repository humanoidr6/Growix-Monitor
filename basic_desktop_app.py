import tkinter as tk
import serial
import time
import threading

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

class SensorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Growix Basic Monitor")
        self.root.geometry("250x350")
        self.root.resizable(False, False)
        
        self.lbl_title = tk.Label(root, text="Live Sensor Data", font=("Helvetica", 14, "bold"))
        self.lbl_title.pack(pady=15)
        
        self.lbl_temp = tk.Label(root, text="Temperature: -- °C", font=("Helvetica", 12))
        self.lbl_temp.pack(pady=5)
        
        self.lbl_moist = tk.Label(root, text="Moisture: -- %", font=("Helvetica", 12))
        self.lbl_moist.pack(pady=5)
        
        self.lbl_ec = tk.Label(root, text="EC: -- us/cm", font=("Helvetica", 12))
        self.lbl_ec.pack(pady=5)
        
        self.lbl_ph = tk.Label(root, text="pH Level: --", font=("Helvetica", 12))
        self.lbl_ph.pack(pady=5)
        
        self.lbl_npk = tk.Label(root, text="NPK: -- / -- / --", font=("Helvetica", 12))
        self.lbl_npk.pack(pady=5)
        
        self.lbl_status = tk.Label(root, text="Connecting to Sensor...", font=("Helvetica", 9), fg="gray")
        self.lbl_status.pack(side="bottom", pady=10)
        
        # Start background polling thread
        self.running = True
        self.thread = threading.Thread(target=self.poll_sensor, daemon=True)
        self.thread.start()

    def update_ui(self, data, status, color):
        if data:
            self.lbl_temp.config(text=f"Temperature: {data.get('temp', 0):.1f} °C")
            self.lbl_moist.config(text=f"Moisture: {data.get('moist', 0):.1f} %")
            self.lbl_ec.config(text=f"EC: {data.get('ec', 0)} us/cm")
            self.lbl_ph.config(text=f"pH Level: {data.get('ph', 0):.2f}")
            self.lbl_npk.config(text=f"NPK: {data.get('n', 0)} / {data.get('p', 0)} / {data.get('k', 0)}")
        self.lbl_status.config(text=status, fg=color)

    def poll_sensor(self):
        while self.running:
            try:
                ser = serial.Serial('/dev/serial0', 9600, timeout=0.5)
                break
            except Exception:
                self.root.after(0, self.update_ui, None, "Waiting for Serial Port...", "orange")
                time.sleep(2)

        while self.running:
            try:
                t_raw = read_register(ser, 0x0013)
                m_raw = read_register(ser, 0x0012)
                ec = read_register(ser, 0x0014)
                ph_raw = read_register(ser, 0x0006)
                n = read_register(ser, 0x0022)
                p = read_register(ser, 0x0023)
                k = read_register(ser, 0x0024)

                data = {
                    'temp': (t_raw / 10.0) if t_raw is not None else 0,
                    'moist': (m_raw / 10.0) if m_raw is not None else 0,
                    'ec': ec if ec is not None else 0,
                    'ph': (ph_raw / 100.0) if ph_raw is not None else 0,
                    'n': n if n is not None else 0,
                    'p': p if p is not None else 0,
                    'k': k if k is not None else 0
                }
                
                status_text = "Live" if t_raw is not None else "Sensor Offline (No Reply)"
                color = "green" if t_raw is not None else "red"
                
                self.root.after(0, self.update_ui, data, status_text, color)
                
            except Exception:
                self.root.after(0, self.update_ui, None, "Connection Lost. Retrying...", "red")
                
            time.sleep(2.0)

if __name__ == "__main__":
    root = tk.Tk()
    app = SensorApp(root)
    root.mainloop()
