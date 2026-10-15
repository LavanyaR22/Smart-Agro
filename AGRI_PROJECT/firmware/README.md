# ESP32 Firmware Guide & First Sensor Test

This directory contains the Arduino C++ firmware for the **AGRI Smart Irrigation** field sensor node.

---

## 1. Hardware Pin Connections

| Sensor / Module | Sensor Pin | ESP32 Pin | Power Voltage | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **DHT22** | DATA / OUT | **GPIO 4** | 3.3V (or 5V VIN) | Use 10kΩ pull-up between DATA and VCC if module lacks built-in resistor |
| **DHT22** | VCC / + | **3V3** | 3.3V | |
| **DHT22** | GND / - | **GND** | Ground | Common Ground |
| **Capacitive Soil v1.2** | AOUT | **GPIO 34** | 3.3V | **ADC1** pin (safe to use with Wi-Fi) |
| **Capacitive Soil v1.2** | VCC | **3V3** | 3.3V | Power with 3.3V to protect 3.3V ADC inputs |
| **Capacitive Soil v1.2** | GND | **GND** | Ground | Common Ground |
| **5V Relay (Pump)** | IN | **GPIO 23** | — | **DISABLED in code during this sensor test** |

> **Safety Notice**: GPIO 23 (Pump Relay) is not initialized or energized in this sensor test. Physical irrigation remains completely unpowered.

---

## 2. Required Arduino Libraries

In **Arduino IDE**, open **Tools -> Manage Libraries...** (or press `Ctrl + Shift + I`):

1. **DHT sensor library** by Adafruit (Version 1.4.x)
   - When prompted to install dependencies (e.g., *Adafruit Unified Sensor*), click **Install All**.
2. **ArduinoJson** by Benoit Blanchon
   - Version 6.x or 7.x (both versions are fully supported by this sketch).

---

## 3. Step-by-Step: Performing Your First Sensor Test

### Step A: Verify Standalone Mode
1. Open `firmware/esp32_irrigation/esp32_irrigation.ino` in Arduino IDE.
2. Ensure `ENABLE_WIFI_TELEMETRY = false;` (this is the safe default). No Wi-Fi or backend IP is needed for this test.
3. Select your board under **Tools -> Board -> esp32 -> ESP32 Dev Module**.
4. Select your COM port under **Tools -> Port** (e.g., `COM3`, `COM4`).
5. Click **Upload** (`Ctrl + U`).
6. Once uploaded, open **Tools -> Serial Monitor** (`Ctrl + Shift + M`).
7. Set baud rate to **115200 baud** in the bottom right corner of Serial Monitor.

### Step B: Inspect Sensor Output
You should see output every 3 seconds:
```text
--------------------------------------------------
Temperature    : 26.8 °C
Humidity       : 55.4 %
Soil Raw (ADC) : 3150 (provisional range: 1400 - 3200)
Soil Moisture  : 3 % [PROVISIONAL CALIBRATION]
```

### Step C: Sensor Calibration (Provisional vs. Real)
The default calibration values (`PROVISIONAL_AIR_VALUE = 3200`, `PROVISIONAL_WATER_VALUE = 1400`) are **provisional estimates**:
1. **Dry Air Test**:
   - Hold the capacitive probe in dry air. Note the `Soil Raw (ADC)` number printed in Serial Monitor (typically ~2800 to 3500).
   - Set this value as `PROVISIONAL_AIR_VALUE` in the sketch.
2. **Water Cup Test**:
   - Submerge the metal probe into a glass of clean water up to the white guideline (do not submerge the electronics at the top).
   - Note the `Soil Raw (ADC)` number (typically ~1200 to 1600).
   - Set this value as `PROVISIONAL_WATER_VALUE` in the sketch.
3. Re-upload to have accurate 0% to 100% moisture scaling for your specific hardware.

---

## 4. Optional: Enabling Wi-Fi Telemetry (After Sensors Work)

Once your sensors produce stable numbers in the Serial Monitor:
1. In `firmware/esp32_irrigation/esp32_irrigation.ino`, set:
   ```cpp
   const bool ENABLE_WIFI_TELEMETRY = true;
   ```
2. Replace `"YOUR_WIFI_SSID"` and `"YOUR_WIFI_PASSWORD"` with your actual 2.4 GHz Wi-Fi credentials.
3. Find your computer's local IP address on Windows:
   - Open PowerShell and run: `ipconfig`
   - Look for `IPv4 Address` under your active Wi-Fi or Ethernet adapter (e.g., `192.168.1.50`).
4. Replace `YOUR_PC_LAN_IP` in `BACKEND_URL`:
   ```cpp
   const char* BACKEND_URL = "http://192.168.1.50:8000/api/telemetry";
   ```
5. Re-upload. Telemetry will automatically stream from the ESP32 into your live FastAPI dashboard!

