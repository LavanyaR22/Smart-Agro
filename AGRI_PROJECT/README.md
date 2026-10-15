# 🌱 AGRI Smart Irrigation System (Major Project)

An end-to-end Smart Agriculture IoT & Automated Irrigation Management platform built with FastAPI, a responsive vanilla web dashboard, a realistic sensor node simulator, and ESP32 microcontroller firmware.

---

## 🚀 Key Features

- **Responsive Web Dashboard**: Displays live soil moisture, ambient temperature, relative humidity, pump state, and sensor connectivity.
- **Crop Intelligence**: Real-time irrigation recommendations for Wheat, Tomato, Rice, Maize, and Cotton based on soil moisture thresholds.
- **Manual Pump Control**: Software-simulated pump trigger with safety relays isolated by default.
- **Sensor Simulator**: Built-in Python virtual sensor simulator allowing full software testing before physical hardware is wired.
- **Modular Weather Service**: Fallback-protected weather module that keeps running even without an API key or internet access.
- **Zero External DB Dependency**: Runs out-of-the-box on localhost without requiring MongoDB, Docker, or MQTT brokers.

---

## 📁 Project Structure

```
AGRI_PROJECT/
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git ignore file for Python & Windows
├── README.md                     # Main documentation & run commands
├── backend/
│   ├── requirements.txt          # FastAPI, Uvicorn, Pydantic, HTTPX
│   └── app/
│       ├── __init__.py           # Application package
│       ├── main.py               # FastAPI entry point & static mount
│       ├── config.py             # App configuration & safe defaults
│       ├── models.py             # Pydantic schemas (telemetry, pump, crop, weather)
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── telemetry.py      # Telemetry ingestion & query endpoints
│       │   ├── pump.py           # Pump status & simulated toggle endpoints
│       │   ├── crops.py          # Crop profile & recommendation endpoints
│       │   └── weather.py        # Non-blocking weather query endpoint
│       └── services/
│           ├── __init__.py
│           ├── telemetry_store.py        # In-memory ring buffer & heartbeat tracker
│           ├── recommendation_engine.py  # Crop thresholds & recommendation logic
│           ├── pump_manager.py           # Pump state manager with safety isolation
│           └── weather_service.py        # Weather client with graceful fallback
├── frontend/
│   ├── index.html                # Responsive Smart Agriculture Dashboard
│   ├── css/
│   │   └── styles.css            # Modern theme & card layout
│   └── js/
│       └── app.js                # Live polling & UI state update controller
├── simulator/
│   ├── __init__.py
│   ├── requirements.txt          # Requests library
│   └── sensor_simulator.py       # Virtual soil & DHT sensor node
├── firmware/
│   ├── README.md                 # Hardware pinout & wiring guide
│   └── esp32_irrigation/
│       └── esp32_irrigation.ino  # ESP32 C++ Arduino sketch for DHT22 & Soil sensor
└── docs/
    ├── architecture.md           # System flow diagram & module design
    └── setup_guide.md            # Windows 11 step-by-step beginner guide
```

---

## ⚡ Exact Windows PowerShell Run Commands

### 1. Create and Activate Virtual Environment
Open **Windows PowerShell** in this folder:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(If script execution is disabled on your system, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once and retry activation).*

### 2. Install Python Dependencies
```powershell
python -m pip install -r backend/requirements.txt
python -m pip install -r simulator/requirements.txt
```

### 3. Launch the Backend Server
```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### 4. Launch the Sensor Simulator (Second Terminal)
Open a new PowerShell window in `AGRI_PROJECT`:
```powershell
.\venv\Scripts\Activate.ps1
python simulator/sensor_simulator.py
```
Watch live data stream into your dashboard in real-time!
