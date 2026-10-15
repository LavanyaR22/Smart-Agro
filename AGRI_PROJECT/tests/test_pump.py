import unittest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.models import PumpCommand, PumpStatus
from backend.app.services.pump_manager import PumpManager, pump_manager

class TestPumpCommandModel(unittest.TestCase):
    """Test Pydantic model validation and normalization."""

    def test_valid_states_and_normalization(self):
        cmd1 = PumpCommand(state="ON")
        self.assertEqual(cmd1.state, "ON")

        cmd2 = PumpCommand(state="off")
        self.assertEqual(cmd2.state, "OFF")

        cmd3 = PumpCommand(state="  ON  ")
        self.assertEqual(cmd3.state, "ON")

        cmd4 = PumpCommand(state="  OFF\n")
        self.assertEqual(cmd4.state, "OFF")

    def test_valid_modes_and_normalization(self):
        cmd1 = PumpCommand(state="ON", mode="manual")
        self.assertEqual(cmd1.mode, "manual")

        cmd2 = PumpCommand(state="ON", mode=" AUTO ")
        self.assertEqual(cmd2.mode, "auto")

        cmd3 = PumpCommand(state="ON")
        self.assertEqual(cmd3.mode, "manual")

    def test_invalid_state_rejected(self):
        with self.assertRaises(ValidationError):
            PumpCommand(state="INVALID")

        with self.assertRaises(ValidationError):
            PumpCommand(state="START")

        with self.assertRaises(ValidationError):
            PumpCommand(state="")

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValidationError):
            PumpCommand(state="ON", mode="turbo")


class TestPumpManagerUnit(unittest.TestCase):
    """Test PumpManager isolated logic and safety defaults."""

    def setUp(self):
        self.manager = PumpManager()

    def test_default_simulation_safety(self):
        status = self.manager.get_status()
        self.assertEqual(status.state, "OFF")
        self.assertFalse(status.is_active)
        self.assertFalse(status.is_hardware_connected)

    def test_turn_on_simulated(self):
        cmd = PumpCommand(state="ON")
        status = self.manager.set_state(cmd)
        self.assertEqual(status.state, "ON")
        self.assertTrue(status.is_active)
        self.assertFalse(status.is_hardware_connected)
        self.assertIn("SIMULATED", status.message)

    def test_turn_off_simulated(self):
        # First turn on
        self.manager.set_state(PumpCommand(state="ON"))
        # Then turn off
        status = self.manager.set_state(PumpCommand(state="OFF"))
        self.assertEqual(status.state, "OFF")
        self.assertFalse(status.is_active)
        self.assertFalse(status.is_hardware_connected)


class TestPumpAPIIntegration(unittest.TestCase):
    """Test HTTP API routes using FastAPI TestClient."""

    def setUp(self):
        self.client = TestClient(app)

    def test_get_pump_status(self):
        resp = self.client.get("/api/pump/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("state", data)
        self.assertIn("is_active", data)
        self.assertFalse(data["is_hardware_connected"])

    def test_post_pump_control_valid_on(self):
        resp = self.client.post("/api/pump/control", json={"state": "ON"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["state"], "ON")
        self.assertTrue(data["is_active"])
        self.assertFalse(data["is_hardware_connected"])

    def test_post_pump_control_valid_off(self):
        resp = self.client.post("/api/pump/control", json={"state": "OFF"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["state"], "OFF")
        self.assertFalse(data["is_active"])
        self.assertFalse(data["is_hardware_connected"])

    def test_post_pump_control_with_whitespace(self):
        resp = self.client.post("/api/pump/control", json={"state": "  ON  "})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["state"], "ON")
        self.assertTrue(data["is_active"])

        resp2 = self.client.post("/api/pump/control", json={"state": "  off  "})
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2["state"], "OFF")
        self.assertFalse(data2["is_active"])

    def test_post_pump_control_invalid_state_returns_422(self):
        resp = self.client.post("/api/pump/control", json={"state": "INVALID"})
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertIn("detail", data)

    def test_post_pump_control_invalid_mode_returns_422(self):
        resp = self.client.post("/api/pump/control", json={"state": "ON", "mode": "UNKNOWN"})
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertIn("detail", data)

if __name__ == "__main__":
    unittest.main()
