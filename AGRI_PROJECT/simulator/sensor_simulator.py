"""AGRI Smart Irrigation - Virtual Sensor Node Simulator

Simulates an ESP32 hardware node equipped with:
1. Capacitive Soil Moisture Sensor v1.2
2. DHT22 Digital Temperature and Humidity Sensor

Posts telemetry to FastAPI backend at regular intervals.
"""

import time
import random
import os
import sys
import requests

BACKEND_URL = "http://127.0.0.1:8000"
TELEMETRY_ENDPOINT = f"{BACKEND_URL}/api/telemetry"
PUMP_ENDPOINT = f"{BACKEND_URL}/api/pump/status"
INTERVAL_SECONDS = 3

# Explicit simulation flag for unconfirmed physical sensors (NPK & pH)
SIMULATE_SOIL_CHEMISTRY = os.getenv("SIMULATE_SOIL_CHEMISTRY", "True").lower() in ("true", "1", "yes")

def run_simulation():
    print("=" * 60)
    print("  AGRI SMART IRRIGATION - SENSOR NODE SIMULATOR")
    print("=" * 60)
    print(f"Target Backend : {TELEMETRY_ENDPOINT}")
    print(f"Update Interval: {INTERVAL_SECONDS} seconds")
    print(f"Data Source    : SIMULATION (Explicitly Tagged)")
    print(f"NPK/pH Sim     : {'ENABLED (Simulated)' if SIMULATE_SOIL_CHEMISTRY else 'DISABLED (Unavailable)'}")
    print("Press Ctrl + C at any time to stop the simulator.")
    print("=" * 60)

    # Initial baseline field conditions
    soil_moisture = 42.0  # Percentage (%)
    temperature = 26.5    # Celsius (°C)
    humidity = 58.0       # Relative Humidity (%)
    nitrogen = 50.0       # Soil Nitrogen (mg/kg)
    phosphorus = 35.0     # Soil Phosphorus (mg/kg)
    potassium = 180.0     # Soil Potassium (mg/kg)
    ph = 6.8              # Soil pH

    step = 0
    while True:
        step += 1
        try:
            # 1. Query pump state to simulate realistic physical reaction
            is_pump_on = False
            try:
                pump_resp = requests.get(PUMP_ENDPOINT, timeout=2.0)
                if pump_resp.status_code == 200:
                    pump_data = pump_resp.json()
                    is_pump_on = pump_data.get("is_active", False)
            except requests.RequestException:
                pass  # Backend not ready or unreachable

            # 2. Physics simulation
            if is_pump_on:
                # Irrigation water active: soil moisture increases
                soil_moisture += random.uniform(2.5, 4.0)
                soil_moisture = min(soil_moisture, 92.0)
                action_note = "[PUMP ON: Soil hydrating]"
            else:
                # Natural evapotranspiration: soil moisture gradually decreases
                soil_moisture -= random.uniform(0.3, 0.7)
                soil_moisture = max(soil_moisture, 20.0)
                action_note = "[PUMP OFF: Soil drying]"

            # Subtle weather fluctuations
            temperature += random.uniform(-0.2, 0.2)
            temperature = max(18.0, min(38.0, round(temperature, 1)))

            humidity += random.uniform(-0.5, 0.5)
            humidity = max(30.0, min(90.0, round(humidity, 1)))

            # Subtle soil chemistry dynamics (when enabled)
            if SIMULATE_SOIL_CHEMISTRY:
                nitrogen += random.uniform(-0.3, 0.3)
                nitrogen = max(10.0, min(150.0, round(nitrogen, 1)))

                phosphorus += random.uniform(-0.2, 0.2)
                phosphorus = max(5.0, min(100.0, round(phosphorus, 1)))

                potassium += random.uniform(-0.5, 0.5)
                potassium = max(50.0, min(300.0, round(potassium, 1)))

                ph += random.uniform(-0.02, 0.02)
                ph = max(4.5, min(9.0, round(ph, 2)))

            # 3. Construct telemetry payload with explicit source identification
            payload = {
                "temperature": round(temperature, 1),
                "humidity": round(humidity, 1),
                "soil_moisture": round(soil_moisture, 1),
                "device_id": "VIRTUAL_ESP32_NODE_01",
                "source": "simulation",
                "sources": {
                    "temperature": "simulation",
                    "humidity": "simulation",
                    "soil_moisture": "simulation",
                }
            }

            if SIMULATE_SOIL_CHEMISTRY:
                payload["nitrogen"] = round(nitrogen, 1)
                payload["phosphorus"] = round(phosphorus, 1)
                payload["potassium"] = round(potassium, 1)
                payload["ph"] = round(ph, 2)
                payload["sources"]["nitrogen"] = "simulation"
                payload["sources"]["phosphorus"] = "simulation"
                payload["sources"]["potassium"] = "simulation"
                payload["sources"]["ph"] = "simulation"

            # 4. Transmit to backend
            response = requests.post(TELEMETRY_ENDPOINT, json=payload, timeout=3.0)
            if response.status_code == 200:
                chem_log = f" | NPK=({payload.get('nitrogen')}, {payload.get('phosphorus')}, {payload.get('potassium')}) pH={payload.get('ph')} [SIMULATED]" if SIMULATE_SOIL_CHEMISTRY else " | NPK/pH: [UNAVAILABLE]"
                print(
                    f"[Step {step:03d}] Sent: Temp={payload['temperature']}°C | "
                    f"Humidity={payload['humidity']}% | "
                    f"Soil Moisture={payload['soil_moisture']}% (SIMULATION){chem_log} | {action_note}"
                )
            else:
                print(f"[Step {step:03d}] Backend responded with status {response.status_code}")

        except requests.ConnectionError:
            print(f"[Step {step:03d}] Backend offline at {BACKEND_URL}. Retrying in {INTERVAL_SECONDS}s...")
        except KeyboardInterrupt:
            print("\nSimulator stopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"[Step {step:03d}] Unexpected error: {e}")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_simulation()
