# Growix Automated Environmental Monitoring Node

This repository contains the complete software stack, hardware specifications, and debugging scripts for the **Growix Automated Environmental/Soil Monitoring Node**. 

The goal of this project is to robustly extract telemetry data (Temperature, Moisture, Conductivity, pH, and NPK levels) from a Modbus RTU 7-in-1 Soil Sensor using a Raspberry Pi.

---

## 🏗️ Hardware Architecture & Wiring (CRITICAL)

The system relies on a Raspberry Pi communicating with a 12V RS-485 Soil Sensor via a C25B (MAX485) TTL-to-RS485 module. 

### ⚠️ Logic Level Warning
The Raspberry Pi operates strictly at **3.3V logic**. Standard MAX485 modules (like the C25B) operate at **5V**. If you power the C25B with 5V, the Receiver Output (`RO`) pin will send 5V into the Pi's UART RX pin, **which will permanently damage the Pi**.

**The Workaround Used in this Project:**
To avoid voltage dividers or logic level shifters, **power the C25B module directly from the Raspberry Pi's 3.3V pin.** While slightly out of spec for the MAX485 chip, it works flawlessly for short cable runs and prevents any hardware damage.

### 🔌 Pinout & Connections

| C25B (MAX485) Pin | Connected To | Notes |
| :--- | :--- | :--- |
| **VCC** | Pi **3.3V** (Pin 1 or 17) | **Crucial:** Use 3.3V, not 5V! |
| **GND** | Pi **GND** (Pin 6) | Must share ground with Pi & 12V supply |
| **DI** (Driver In) | Pi **GPIO 14 / TX** (Pin 8) | Transmits Modbus requests |
| **RO** (Receiver Out)| Pi **GPIO 15 / RX** (Pin 10)| Receives Modbus responses |
| **DE & RE** | Pi **GPIO 18** (Pin 12) | **Short these together**. Used for Flow Control. |
| **A / D+** | Sensor **Yellow/Green wire** | RS-485 Differential (+) |
| **B / D-** | Sensor **Blue/White wire** | RS-485 Differential (-) |

### 🔋 Powering the Sensor
*   **Sensor VCC:** Connect to external **12V DC Supply**.
*   **Sensor GND:** Connect to 12V DC Ground.
*   **Common Ground:** Run a wire connecting the 12V supply ground to the Raspberry Pi's GND. Without this, the RS-485 signal will float and fail.

---

## 🗺️ Modbus Register Map (Undocumented Sensor Fix)

During development, the specific datasheet for the sensor was missing. We wrote `scanner.py` to blindly poll memory addresses 0-60 and successfully reverse-engineered the sensor's register map based on ambient air responses.

**The Discovered Map (Holding Registers - 0x03):**
*   **0x0006:** pH Level (Divide by 100 -> e.g., 700 = 7.00 pH)
*   **0x0012:** Soil Moisture (Divide by 10 -> e.g., 0 = 0.0%)
*   **0x0013:** Temperature (Divide by 10 -> e.g., 276 = 27.6 °C)
*   **0x0014:** Electrical Conductivity (Raw us/cm)
*   **0x0022:** Nitrogen / N (Raw mg/kg)
*   **0x0023:** Phosphorus / P (Raw mg/kg)
*   **0x0024:** Potassium / K (Raw mg/kg)

---

## 💻 Software Stack

The software is written in Python 3, utilizing `pyserial` for low-level communication. 

### Why not `pymodbus` or `minimalmodbus`?
Because we are manually driving the DE/RE pins (Flow Control) via GPIO 18, high-level libraries often toggle the pin too early or too late, causing "No response received" errors. By writing raw Modbus RTU frames via `pyserial`, we achieve perfect microsecond timing over the Transmit/Receive states.

### Included Scripts:
1.  **`basic_desktop_app.py`:** A lightweight, self-contained Tkinter desktop app that runs natively on the Pi. It handles serial polling in a background thread and updates a clean graphical UI.
2.  **`web_dashboard.py`:** A premium, dark-mode Flask web dashboard utilizing glassmorphism CSS. Runs headlessly on the Pi and serves data to any device on the network via `http://<PI_IP>:5000`.
3.  **`live_monitor.py`:** A colorful Terminal UI (TUI) for SSH users to view live telemetry directly in the console.
4.  **`scanner.py`:** The reverse-engineering tool used to sweep Modbus registers and discover data payloads without a datasheet.
5.  **`Growix_Monitor.desktop`:** An LXDE autostart file to ensure the desktop app boots automatically after a power cut.

---

## 🚀 Setup & Installation (For New Developers)

If you are cloning this to a new Raspberry Pi, follow these exact steps:

### 1. Enable Hardware Serial
The Modbus scripts rely on `/dev/serial0`. You must free this up from the Linux console.
```bash
sudo raspi-config
# Navigate to: 3 Interface Options -> I6 Serial Port
# "Would you like a login shell to be accessible over serial?" -> NO
# "Would you like the serial port hardware to be enabled?" -> YES
# Reboot the Pi.
```

### 2. Environment Setup
We use a Python virtual environment to avoid PEP-668 restrictions in Debian Bookworm.
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-tk git

# Create virtual environment
python3 -m venv ~/sensor_env

# Install libraries
~/sensor_env/bin/pip install pyserial gpiozero flask
```

### 3. Autostart Configuration (Resilience)
To ensure the system boots straight into the telemetry UI after a power failure:
```bash
mkdir -p ~/.config/autostart
cp Growix_Monitor.desktop ~/.config/autostart/
chmod +x ~/.config/autostart/Growix_Monitor.desktop
```

---

## 🛠️ Troubleshooting

*   **Error: "Connection Lost" / "Sensor Offline (No Reply)"**
    *   *Check 1:* Is the 12V power supply plugged into the wall?
    *   *Check 2:* Are the A and B wires flipped? (Try reversing Yellow and Blue).
    *   *Check 3:* Is the DE/RE wire securely connected to GPIO 18?
*   **Error: "Permission Denied: /dev/serial0"**
    *   The `sciencebus` user must be in the `dialout` group: `sudo usermod -a -G dialout $USER`.
*   **Values are all 0 or don't make sense**
    *   Your specific sensor might use a different register map. Run `~/sensor_env/bin/python scanner.py` while holding the sensor to find which registers jump.
