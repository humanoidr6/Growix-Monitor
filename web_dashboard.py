import serial
import time
import threading
from flask import Flask, jsonify, render_template_string

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

# Global telemetry store
telemetry = {
    'temp': 0.0,
    'moist': 0.0,
    'ec': 0,
    'ph': 7.0,
    'n': 0,
    'p': 0,
    'k': 0,
    'status': 'Initializing...'
}

def poll_sensor():
    while True:
        try:
            ser = serial.Serial('/dev/serial0', 9600, timeout=0.5)
            telemetry['status'] = 'Live Telemetry Active'
            break
        except Exception as e:
            telemetry['status'] = f'Serial Error: Waiting for port...'
            time.sleep(2)

    while True:
        try:
            t_raw = read_register(ser, 0x0013)
            m_raw = read_register(ser, 0x0012)
            ec = read_register(ser, 0x0014)
            ph_raw = read_register(ser, 0x0006)
            n = read_register(ser, 0x0022)
            p = read_register(ser, 0x0023)
            k = read_register(ser, 0x0024)

            if t_raw is not None: telemetry['temp'] = t_raw / 10.0
            if m_raw is not None: telemetry['moist'] = m_raw / 10.0
            if ec is not None: telemetry['ec'] = ec
            if ph_raw is not None: telemetry['ph'] = ph_raw / 100.0
            if n is not None: telemetry['n'] = n
            if p is not None: telemetry['p'] = p
            if k is not None: telemetry['k'] = k
            
            telemetry['status'] = 'Live Telemetry Active'
            
        except Exception as e:
            telemetry['status'] = 'Sensor Disconnected'
            
        time.sleep(2.0)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Growix Telemetry</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');
        
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --accent-blue: #38bdf8;
            --accent-green: #34d399;
            --accent-purple: #c084fc;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        body {
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(192, 132, 252, 0.15) 0px, transparent 50%);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 2rem;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            font-weight: 700;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status {
            font-weight: 300;
            color: var(--accent-green);
            margin-bottom: 3rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            background-color: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(52, 211, 153, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            width: 100%;
            max-width: 1200px;
        }
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            border-color: rgba(255,255,255,0.2);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.85rem;
        }
        .card-value {
            font-size: 3.5rem;
            font-weight: 700;
            display: flex;
            align-items: baseline;
            gap: 8px;
        }
        .card-unit {
            font-size: 1.2rem;
            font-weight: 300;
            color: var(--text-muted);
        }
        .card.temp .card-value { color: #facc15; }
        .card.moist .card-value { color: #38bdf8; }
        .card.ec .card-value { color: #34d399; }
        .card.ph .card-value { color: #c084fc; }
        .card.n .card-value { color: #fb7185; }
        .card.p .card-value { color: #818cf8; }
        .card.k .card-value { color: #a3e635; }
        @media (max-width: 768px) {
            h1 { font-size: 2rem; }
            .dashboard { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <h1>Growix Lab Dashboard</h1>
    <div class="status">
        <div class="status-dot"></div>
        <span id="sys-status">Initializing...</span>
    </div>

    <div class="dashboard">
        <div class="card temp">
            <div class="card-header"><span>Temperature</span> <span>🌡️</span></div>
            <div class="card-value"><span id="val-temp">--</span><span class="card-unit">°C</span></div>
        </div>
        <div class="card moist">
            <div class="card-header"><span>Soil Moisture</span> <span>💧</span></div>
            <div class="card-value"><span id="val-moist">--</span><span class="card-unit">%</span></div>
        </div>
        <div class="card ec">
            <div class="card-header"><span>Conductivity</span> <span>⚡</span></div>
            <div class="card-value"><span id="val-ec">--</span><span class="card-unit">us/cm</span></div>
        </div>
        <div class="card ph">
            <div class="card-header"><span>pH Level</span> <span>🧪</span></div>
            <div class="card-value"><span id="val-ph">--</span><span class="card-unit">pH</span></div>
        </div>
        <div class="card n">
            <div class="card-header"><span>Nitrogen (N)</span> <span>🌱</span></div>
            <div class="card-value"><span id="val-n">--</span><span class="card-unit">mg/kg</span></div>
        </div>
        <div class="card p">
            <div class="card-header"><span>Phosphorus (P)</span> <span>🌱</span></div>
            <div class="card-value"><span id="val-p">--</span><span class="card-unit">mg/kg</span></div>
        </div>
        <div class="card k">
            <div class="card-header"><span>Potassium (K)</span> <span>🌱</span></div>
            <div class="card-value"><span id="val-k">--</span><span class="card-unit">mg/kg</span></div>
        </div>
    </div>

    <script>
        async function updateData() {
            try {
                const response = await fetch('/data');
                const data = await response.json();
                
                document.getElementById('sys-status').innerText = data.status;
                document.getElementById('val-temp').innerText = data.temp.toFixed(1);
                document.getElementById('val-moist').innerText = data.moist.toFixed(1);
                document.getElementById('val-ec').innerText = data.ec;
                document.getElementById('val-ph').innerText = data.ph.toFixed(2);
                document.getElementById('val-n').innerText = data.n;
                document.getElementById('val-p').innerText = data.p;
                document.getElementById('val-k').innerText = data.k;
            } catch (error) {
                console.error("Error fetching telemetry:", error);
                document.getElementById('sys-status').innerText = "Connection Lost";
            }
        }
        setInterval(updateData, 2000);
        updateData();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def data():
    return jsonify(telemetry)

if __name__ == '__main__':
    # Start the hardware polling thread
    sensor_thread = threading.Thread(target=poll_sensor, daemon=True)
    sensor_thread.start()
    
    # Run the lightweight Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
