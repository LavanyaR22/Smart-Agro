import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.models import TelemetryData, WeatherResponse
from backend.app.services.weather_service import WeatherService
from backend.app.services.telemetry_store import telemetry_store

class TestHybridTelemetryModel(unittest.TestCase):
    """Test unit validation and provenance rules for TelemetryData."""

    def test_simulator_reading_labelled_simulation(self):
        data = TelemetryData(
            temperature=26.5,
            humidity=58.0,
            soil_moisture=42.0,
            device_id="VIRTUAL_ESP32_NODE_01",
            source="simulation",
        )
        self.assertEqual(data.source, "simulation")
        self.assertEqual(data.sources["temperature"], "simulation")
        self.assertEqual(data.sources["humidity"], "simulation")
        self.assertEqual(data.sources["soil_moisture"], "simulation")

    def test_hardware_reading_labelled_hardware(self):
        data = TelemetryData(
            temperature=27.1,
            humidity=54.2,
            soil_moisture=48.0,
            device_id="ESP32_FIELD_NODE_01",
            source="hardware",
        )
        self.assertEqual(data.source, "hardware")
        self.assertEqual(data.sources["temperature"], "hardware")
        self.assertEqual(data.sources["humidity"], "hardware")
        self.assertEqual(data.sources["soil_moisture"], "hardware")

    def test_missing_npk_ph_remain_unavailable(self):
        data = TelemetryData(
            temperature=25.0,
            humidity=50.0,
            soil_moisture=40.0,
            source="hardware",
        )
        # NPK and pH must remain strictly None
        self.assertIsNone(data.nitrogen)
        self.assertIsNone(data.phosphorus)
        self.assertIsNone(data.potassium)
        self.assertIsNone(data.ph)
        # Provenance tags must explicitly indicate unavailable
        self.assertEqual(data.sources["nitrogen"], "unavailable")
        self.assertEqual(data.sources["phosphorus"], "unavailable")
        self.assertEqual(data.sources["potassium"], "unavailable")
        self.assertEqual(data.sources["ph"], "unavailable")

    def test_simulated_npk_ph_when_supplied(self):
        data = TelemetryData(
            temperature=25.0,
            humidity=50.0,
            soil_moisture=40.0,
            source="simulation",
            nitrogen=52.0,
            phosphorus=34.0,
            potassium=182.0,
            ph=6.85,
        )
        self.assertEqual(data.nitrogen, 52.0)
        self.assertEqual(data.phosphorus, 34.0)
        self.assertEqual(data.potassium, 182.0)
        self.assertEqual(data.ph, 6.85)
        self.assertEqual(data.sources["nitrogen"], "simulation")
        self.assertEqual(data.sources["phosphorus"], "simulation")
        self.assertEqual(data.sources["potassium"], "simulation")
        self.assertEqual(data.sources["ph"], "simulation")

    def test_invalid_source_rejected(self):
        with self.assertRaises(ValidationError):
            TelemetryData(
                temperature=25.0,
                humidity=50.0,
                soil_moisture=40.0,
                source="invalid_source",
            )

        with self.assertRaises(ValidationError):
            TelemetryData(
                temperature=25.0,
                humidity=50.0,
                soil_moisture=40.0,
                sources={"temperature": "unrecognized_source"},
            )

    def test_backward_compatible_inference(self):
        # Virtual device without explicit source defaults to simulation
        data_sim = TelemetryData(
            temperature=25.0,
            humidity=50.0,
            soil_moisture=40.0,
            device_id="VIRTUAL_ESP32_NODE_01",
        )
        self.assertEqual(data_sim.source, "simulation")
        self.assertEqual(data_sim.sources["soil_moisture"], "simulation")

        # Physical device without explicit source defaults to hardware
        data_hw = TelemetryData(
            temperature=25.0,
            humidity=50.0,
            soil_moisture=40.0,
            device_id="ESP32_FIELD_NODE_01",
        )
        self.assertEqual(data_hw.source, "hardware")
        self.assertEqual(data_hw.sources["soil_moisture"], "hardware")
        self.assertIsNone(data_hw.nitrogen)

    def test_hardware_reading_with_null_moisture_and_raw_adc(self):
        data = TelemetryData(
            temperature=27.2,
            humidity=53.4,
            soil_moisture=None,
            raw_soil_adc=4095,
            device_id="ESP32_FIELD_NODE_01",
            source="hardware",
        )
        self.assertIsNone(data.soil_moisture)
        self.assertEqual(data.raw_soil_adc, 4095)
        self.assertEqual(data.source, "hardware")
        self.assertEqual(data.sources["soil_moisture"], "unavailable")
        self.assertEqual(data.sources["raw_soil_adc"], "hardware")

    def test_raw_soil_adc_validation(self):
        # Valid boundary values: 0 and 4095
        data_min = TelemetryData(temperature=20.0, humidity=50.0, raw_soil_adc=0)
        self.assertEqual(data_min.raw_soil_adc, 0)

        data_max = TelemetryData(temperature=20.0, humidity=50.0, raw_soil_adc=4095)
        self.assertEqual(data_max.raw_soil_adc, 4095)

        # Values outside 0..4095 must fail validation
        with self.assertRaises(ValidationError):
            TelemetryData(temperature=20.0, humidity=50.0, raw_soil_adc=-1)

        with self.assertRaises(ValidationError):
            TelemetryData(temperature=20.0, humidity=50.0, raw_soil_adc=4096)


class TestHybridTelemetryAPI(unittest.TestCase):
    """Test HTTP API endpoints for ingestion and provenance."""

    def setUp(self):
        self.client = TestClient(app)

    def test_post_simulator_telemetry_endpoint(self):
        payload = {
            "temperature": 26.0,
            "humidity": 55.0,
            "soil_moisture": 38.0,
            "device_id": "VIRTUAL_ESP32_NODE_01",
            "source": "simulation",
            "nitrogen": 45.0,
            "phosphorus": 30.0,
            "potassium": 160.0,
            "ph": 6.7,
        }
        resp = self.client.post("/api/telemetry", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["source"], "simulation")
        self.assertEqual(body["sources"]["soil_moisture"], "simulation")
        self.assertEqual(body["sources"]["nitrogen"], "simulation")
        self.assertEqual(body["nitrogen"], 45.0)

    def test_post_hardware_telemetry_endpoint(self):
        payload = {
            "temperature": 27.5,
            "humidity": 60.0,
            "soil_moisture": 50.0,
            "device_id": "ESP32_FIELD_NODE_01",
            "source": "hardware",
        }
        resp = self.client.post("/api/telemetry", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["source"], "hardware")
        self.assertEqual(body["sources"]["soil_moisture"], "hardware")
        self.assertIsNone(body["nitrogen"])
        self.assertEqual(body["sources"]["nitrogen"], "unavailable")

    def test_post_hardware_telemetry_with_null_moisture_and_raw_adc(self):
        payload = {
            "temperature": 27.2,
            "humidity": 53.4,
            "soil_moisture": None,
            "raw_soil_adc": 4095,
            "device_id": "ESP32_FIELD_NODE_01",
            "source": "hardware",
        }
        resp = self.client.post("/api/telemetry", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["source"], "hardware")
        self.assertIsNone(body["soil_moisture"])
        self.assertEqual(body["raw_soil_adc"], 4095)
        self.assertEqual(body["sources"]["soil_moisture"], "unavailable")
        self.assertEqual(body["sources"]["raw_soil_adc"], "hardware")

    def test_post_invalid_source_returns_422(self):
        payload = {
            "temperature": 25.0,
            "humidity": 50.0,
            "soil_moisture": 40.0,
            "source": "fabricated_data",
        }
        resp = self.client.post("/api/telemetry", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_status_endpoint_reports_source(self):
        # Post known hardware reading
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 28.0,
                "humidity": 52.0,
                "soil_moisture": 44.0,
                "device_id": "ESP32_NODE_01",
                "source": "hardware",
            },
        )
        resp = self.client.get("/api/telemetry/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_connected"])
        self.assertEqual(data["source"], "hardware")

    def test_get_telemetry_mode_default(self):
        telemetry_store.set_active_mode("hardware")
        resp = self.client.get("/api/telemetry/mode")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["active_mode"], "hardware")
        self.assertIn("hardware", data["available_modes"])
        self.assertIn("simulation", data["available_modes"])

    def test_post_telemetry_mode_switching(self):
        # Switch to simulation
        resp = self.client.post("/api/telemetry/mode", json={"mode": "simulation"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["active_mode"], "simulation")

        # Verify via GET
        resp_get = self.client.get("/api/telemetry/mode")
        self.assertEqual(resp_get.json()["active_mode"], "simulation")

        # Switch back to hardware
        resp_back = self.client.post("/api/telemetry/mode", json={"mode": "hardware"})
        self.assertEqual(resp_back.status_code, 200)
        self.assertEqual(resp_back.json()["active_mode"], "hardware")

    def test_post_telemetry_mode_invalid_returns_400(self):
        resp = self.client.post("/api/telemetry/mode", json={"mode": "cloud_virtual"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid mode", resp.json()["detail"])

    def test_latest_and_status_respect_explicit_source(self):
        # Post hardware reading
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 27.2,
                "humidity": 53.4,
                "soil_moisture": None,
                "raw_soil_adc": 4095,
                "device_id": "ESP32_FIELD_NODE_01",
                "source": "hardware",
            },
        )
        # Post simulation reading
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 24.0,
                "humidity": 60.0,
                "soil_moisture": 45.0,
                "device_id": "VIRTUAL_ESP32_NODE_01",
                "source": "simulation",
            },
        )

        # Query explicit source=hardware
        resp_hw = self.client.get("/api/telemetry/latest?source=hardware")
        self.assertEqual(resp_hw.status_code, 200)
        self.assertEqual(resp_hw.json()["device_id"], "ESP32_FIELD_NODE_01")
        self.assertIsNone(resp_hw.json()["soil_moisture"])
        self.assertEqual(resp_hw.json()["raw_soil_adc"], 4095)

        # Query explicit source=simulation
        resp_sim = self.client.get("/api/telemetry/latest?source=simulation")
        self.assertEqual(resp_sim.status_code, 200)
        self.assertEqual(resp_sim.json()["device_id"], "VIRTUAL_ESP32_NODE_01")
        self.assertEqual(resp_sim.json()["soil_moisture"], 45.0)

        # Invalid source query parameter returns 400
        resp_inv = self.client.get("/api/telemetry/latest?source=invalid_src")
        self.assertEqual(resp_inv.status_code, 400)

        resp_inv_status = self.client.get("/api/telemetry/status?source=invalid_src")
        self.assertEqual(resp_inv_status.status_code, 400)

    def test_latest_and_status_omitted_source_uses_active_mode(self):
        # Set active mode to hardware
        self.client.post("/api/telemetry/mode", json={"mode": "hardware"})
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 27.2,
                "humidity": 53.4,
                "soil_moisture": None,
                "raw_soil_adc": 4095,
                "device_id": "ESP32_FIELD_NODE_01",
                "source": "hardware",
            },
        )
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 24.0,
                "humidity": 60.0,
                "soil_moisture": 45.0,
                "device_id": "VIRTUAL_ESP32_NODE_01",
                "source": "simulation",
            },
        )

        # In hardware mode, omitted source returns hardware data
        resp = self.client.get("/api/telemetry/latest")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["device_id"], "ESP32_FIELD_NODE_01")

        # Switch to simulation mode, omitted source returns simulation data
        self.client.post("/api/telemetry/mode", json={"mode": "simulation"})
        resp_sim = self.client.get("/api/telemetry/latest")
        self.assertEqual(resp_sim.status_code, 200)
        self.assertEqual(resp_sim.json()["device_id"], "VIRTUAL_ESP32_NODE_01")

        # Switch back to hardware for clean state
        self.client.post("/api/telemetry/mode", json={"mode": "hardware"})

    def test_missing_telemetry_never_falls_back_to_other_source(self):
        telemetry_store.reset()
        # Post ONLY simulation telemetry
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 24.0,
                "humidity": 60.0,
                "soil_moisture": 45.0,
                "device_id": "VIRTUAL_ESP32_NODE_01",
                "source": "simulation",
            },
        )
        # Ensure active mode is hardware
        self.client.post("/api/telemetry/mode", json={"mode": "hardware"})

        # Hardware has never reported: latest must return null, NOT simulation data
        resp = self.client.get("/api/telemetry/latest?source=hardware")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json())

        # Status for hardware must report awaiting/not connected, NOT simulation status
        status_resp = self.client.get("/api/telemetry/status?source=hardware")
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertFalse(status_data["is_connected"])
        self.assertEqual(status_data["source"], "hardware")
        self.assertIsNone(status_data["device_id"])


class TestWeatherServiceProvenance(unittest.IsolatedAsyncioTestCase):
    """Test data provenance in WeatherService."""

    async def test_fallback_weather_labelled_simulation(self):
        svc = WeatherService(api_key="", city="TestCity")
        res = await svc.get_current_weather()
        self.assertTrue(res.is_fallback)
        self.assertEqual(res.source, "simulation")

    async def test_live_weather_labelled_weather_api(self):
        svc = WeatherService(api_key="mock_key", city="TestCity")
        mock_payload = {
            "name": "TestCity",
            "main": {"temp": 24.5, "humidity": 65.0},
            "weather": [{"description": "clear sky"}],
        }

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: mock_payload

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            res = await svc.get_current_weather()
            self.assertFalse(res.is_fallback)
            self.assertEqual(res.source, "weather_api")
            self.assertEqual(res.city, "TestCity")
            self.assertEqual(res.temperature, 24.5)

class TestTelemetryStoreModeIsolation(unittest.TestCase):
    """Test independent per-source storage and mode selection in TelemetryStore."""

    def setUp(self):
        telemetry_store.reset()

    def tearDown(self):
        telemetry_store.reset()

    def test_default_active_mode_is_hardware(self):
        self.assertEqual(telemetry_store.get_active_mode(), "hardware")

    def test_mode_switching_and_validation(self):
        telemetry_store.set_active_mode("simulation")
        self.assertEqual(telemetry_store.get_active_mode(), "simulation")

        telemetry_store.set_active_mode("hardware")
        self.assertEqual(telemetry_store.get_active_mode(), "hardware")

        with self.assertRaises(ValueError):
            telemetry_store.set_active_mode("invalid_mode")

    def test_independent_per_source_storage(self):
        # 1. Record hardware telemetry
        hw_reading = TelemetryData(
            temperature=27.2,
            humidity=53.4,
            soil_moisture=None,
            raw_soil_adc=4095,
            device_id="ESP32_FIELD_NODE_01",
            source="hardware",
        )
        telemetry_store.record_telemetry(hw_reading)

        # 2. Record simulated telemetry
        sim_reading = TelemetryData(
            temperature=24.0,
            humidity=60.0,
            soil_moisture=45.0,
            device_id="VIRTUAL_ESP32_NODE_01",
            source="simulation",
        )
        telemetry_store.record_telemetry(sim_reading)

        # 3. Neither record overwrites the other
        latest_hw = telemetry_store.get_latest("hardware")
        self.assertIsNotNone(latest_hw)
        self.assertEqual(latest_hw.device_id, "ESP32_FIELD_NODE_01")
        self.assertIsNone(latest_hw.soil_moisture)
        self.assertEqual(latest_hw.raw_soil_adc, 4095)

        latest_sim = telemetry_store.get_latest("simulation")
        self.assertIsNotNone(latest_sim)
        self.assertEqual(latest_sim.device_id, "VIRTUAL_ESP32_NODE_01")
        self.assertEqual(latest_sim.soil_moisture, 45.0)

        # 4. In default hardware mode, get_latest() returns hardware reading
        telemetry_store.set_active_mode("hardware")
        self.assertEqual(telemetry_store.get_latest().device_id, "ESP32_FIELD_NODE_01")

        # In simulation mode, get_latest() returns simulation reading
        telemetry_store.set_active_mode("simulation")
        self.assertEqual(telemetry_store.get_latest().device_id, "VIRTUAL_ESP32_NODE_01")

    def test_isolated_sensor_status_freshness(self):
        # Record ONLY hardware reading
        hw_reading = TelemetryData(
            temperature=28.0,
            humidity=50.0,
            soil_moisture=None,
            device_id="ESP32_FIELD_NODE_01",
            source="hardware",
        )
        telemetry_store.record_telemetry(hw_reading)

        # Hardware status is online
        hw_status = telemetry_store.get_sensor_status("hardware")
        self.assertTrue(hw_status["is_connected"])
        self.assertEqual(hw_status["source"], "hardware")
        self.assertEqual(hw_status["device_id"], "ESP32_FIELD_NODE_01")

        # Simulation status remains awaiting reading / not connected
        sim_status = telemetry_store.get_sensor_status("simulation")
        self.assertFalse(sim_status["is_connected"])
        self.assertEqual(sim_status["source"], "simulation")
        self.assertIsNone(sim_status["device_id"])

    def test_cache_persistence_roundtrip(self):
        hw_reading = TelemetryData(
            temperature=29.0,
            humidity=52.0,
            soil_moisture=None,
            raw_soil_adc=4095,
            device_id="ESP32_FIELD_NODE_01",
            source="hardware",
        )
        sim_reading = TelemetryData(
            temperature=23.5,
            humidity=61.0,
            soil_moisture=44.0,
            device_id="VIRTUAL_ESP32_NODE_01",
            source="simulation",
        )
        telemetry_store.set_active_mode("hardware")
        telemetry_store.record_telemetry(hw_reading)
        telemetry_store.record_telemetry(sim_reading)

        # Create a fresh store instance pointing to same cache file
        from backend.app.services.telemetry_store import TelemetryStore
        new_store = TelemetryStore()
        self.assertEqual(new_store.get_active_mode(), "hardware")
        self.assertEqual(new_store.get_latest("hardware").device_id, "ESP32_FIELD_NODE_01")
        self.assertEqual(new_store.get_latest("simulation").device_id, "VIRTUAL_ESP32_NODE_01")
        self.assertIsNone(new_store.get_latest("hardware").soil_moisture)
        self.assertEqual(new_store.get_latest("simulation").soil_moisture, 44.0)


class TestCropRecommendationSafety(unittest.TestCase):
    """Test safety, mode isolation, and provenance for crop recommendations."""

    def setUp(self):
        self.client = TestClient(app)
        telemetry_store.reset()

    def tearDown(self):
        telemetry_store.reset()

    def test_hardware_mode_with_null_moisture_withholds_irrigation(self):
        # Post hardware reading with null soil moisture (ADC 4095)
        self.client.post("/api/telemetry/mode", json={"mode": "hardware"})
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 27.2,
                "humidity": 53.4,
                "soil_moisture": None,
                "raw_soil_adc": 4095,
                "device_id": "ESP32_FIELD_NODE_01",
                "source": "hardware",
            },
        )
        resp = self.client.get("/api/crops/wheat/recommendation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "NO_DATA")
        self.assertFalse(data["pump_recommended"])
        self.assertEqual(data["source"], "hardware")
        self.assertEqual(data["device_id"], "ESP32_FIELD_NODE_01")
        self.assertFalse(data["is_stale"])
        self.assertIsNone(data["current_moisture"])
        self.assertIn("uncalibrated", data["reason"].lower())

    def test_hardware_mode_never_falls_back_to_simulation(self):
        # Post ONLY simulation telemetry
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 24.0,
                "humidity": 60.0,
                "soil_moisture": 30.0,  # below wheat threshold (min 45%), would trigger WATER_NEEDED if used
                "device_id": "VIRTUAL_ESP32_NODE_01",
                "source": "simulation",
            },
        )
        # Ensure active mode is hardware
        self.client.post("/api/telemetry/mode", json={"mode": "hardware"})

        # Recommendation in hardware mode must NOT use the 30% simulation reading
        resp = self.client.get("/api/crops/wheat/recommendation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "NO_DATA")
        self.assertFalse(data["pump_recommended"])
        self.assertEqual(data["source"], "hardware")
        self.assertIsNone(data["current_moisture"])

    def test_simulation_mode_uses_simulation_telemetry(self):
        # Post simulation reading needing water (wheat min is 45%)
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 25.0,
                "humidity": 55.0,
                "soil_moisture": 35.0,
                "device_id": "VIRTUAL_ESP32_NODE_01",
                "source": "simulation",
            },
        )
        self.client.post("/api/telemetry/mode", json={"mode": "simulation"})

        resp = self.client.get("/api/crops/wheat/recommendation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "WATER_NEEDED")
        self.assertTrue(data["pump_recommended"])
        self.assertEqual(data["source"], "simulation")
        self.assertEqual(data["device_id"], "VIRTUAL_ESP32_NODE_01")
        self.assertEqual(data["current_moisture"], 35.0)

    def test_stale_telemetry_withholds_irrigation(self):
        # Post hardware reading
        self.client.post(
            "/api/telemetry",
            json={
                "temperature": 26.0,
                "humidity": 55.0,
                "soil_moisture": 30.0,
                "device_id": "TEST_NODE",
                "source": "hardware",
            },
        )
        # Manually backdate the last_received_at timestamp to make it stale (>30s old)
        from datetime import datetime, timezone, timedelta
        telemetry_store._last_received_by_source["hardware"] = datetime.now(timezone.utc) - timedelta(seconds=60)

        resp = self.client.get("/api/crops/wheat/recommendation?source=hardware")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "STALE_DATA")
        self.assertFalse(data["pump_recommended"])
        self.assertTrue(data["is_stale"])
        self.assertIn("stale", data["reason"].lower())

    def test_manual_moisture_override_works(self):
        # When moisture is passed via query param, it overrides telemetry and tags as 'override'
        resp = self.client.get("/api/crops/wheat/recommendation?moisture=38.0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "WATER_NEEDED")
        self.assertTrue(data["pump_recommended"])
        self.assertEqual(data["source"], "override")
        self.assertEqual(data["device_id"], "MANUAL_OVERRIDE")
        self.assertEqual(data["current_moisture"], 38.0)

    def test_invalid_source_returns_400(self):
        resp = self.client.get("/api/crops/wheat/recommendation?source=invalid_sensor_type")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid source", resp.json()["detail"])

    def test_unknown_crop_returns_safe_response(self):
        resp = self.client.get("/api/crops/dragonfruit/recommendation?moisture=50.0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "UNKNOWN_CROP")
        self.assertFalse(data["pump_recommended"])


if __name__ == "__main__":
    unittest.main()


