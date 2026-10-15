# System Architecture & Flow

This document details the modular architecture of the **AGRI Smart Irrigation System**.

---

## 1. High-Level Architecture Diagram

```
+-------------------------------------------------------------+
|                     Data Producers                          |
|                                                             |
|   +-----------------------+     +-----------------------+   |
|   |   Python Simulator    |     |  Physical ESP32 Node  |   |
|   |  (Virtual Soil/DHT)   |     |  (DHT22 + Capacitive) |   |
|   +-----------+-----------+     +-----------+-----------+   |
+---------------|-----------------------------|---------------+
                |                             |
                |  HTTP POST /api/telemetry   |
                +--------------+--------------+
                               |
                               v
+-------------------------------------------------------------+
|                    FastAPI Backend Server                   |
|                                                             |
|   +-----------------------------------------------------+   |
|   | Endpoints:                                          |   |
|   |   - /api/telemetry (POST / GET)                     |   |
|   |   - /api/pump (GET / POST)                          |   |
|   |   - /api/crops (GET list / GET recommendation)      |   |
|   |   - /api/weather (GET with offline fallback)        |   |
|   +-----------------------------------------------------+   |
|                              |                              |
|   +-----------------------------------------------------+   |
|   | Internal Services:                                  |   |
|   |   - TelemetryStore (In-memory ring buffer)          |   |
|   |   - RecommendationEngine (Crop threshold matching)  |   |
|   |   - PumpManager (Safety-isolated state manager)     |   |
|   |   - WeatherService (Non-blocking fallback client)   |   |
|   +-----------------------------------------------------+   |
+------------------------------+------------------------------+
                               |
                HTTP GET / API Polling Loop (2.5s)
                               |
                               v
+-------------------------------------------------------------+
|              Frontend Dashboard (Single Page App)           |
|                                                             |
|   - Real-time Moisture, Temperature, Humidity Gauges        |
|   - Crop Selector & Intelligent Decision Insights           |
|   - Simulated Pump Control Switch                           |
|   - Sensor Connection Pulse (Online / Offline detection)    |
|   - Weather Insight Widget                                  |
+-------------------------------------------------------------+
```

---

## 2. Key Modules & Design Decisions

1. **Decoupled Telemetry Ingestion**:
   - The `/api/telemetry` endpoint accepts standardized JSON regardless of whether the source is a physical ESP32 or the Python simulator.
   - Allows seamless development and testing of all software logic without physical hardware.

2. **Graceful Weather Isolation**:
   - The weather service operates independently. If an external API key is missing or the network drops, fallback values are served immediately, preventing any dashboard freeze.

3. **Safety Defaults**:
   - Hardware pump relays are isolated by default (`ENABLE_HARDWARE_PUMP=False`).
   - Manual pump toggles on the dashboard are simulated to ensure no physical equipment is triggered accidentally.

4. **Zero Heavy Database Dependency**:
   - Runs out of the box using an in-memory buffer without requiring Docker, MongoDB, or external database setups.
