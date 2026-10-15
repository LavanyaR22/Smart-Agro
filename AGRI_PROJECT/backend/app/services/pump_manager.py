from datetime import datetime, timezone
from typing import Optional
from backend.app.config import settings
from backend.app.models import PumpCommand, PumpStatus

class PumpManager:
    """Manages irrigation pump state with safety defaults.
    
    By default, operations are strictly software-simulated.
    Physical activation requires ENABLE_HARDWARE_PUMP=True in settings.
    """

    def __init__(self):
        self._state: str = "OFF"
        self._mode: str = "manual"
        self._last_updated: datetime = datetime.now(timezone.utc)
        self._shutoff_at: Optional[datetime] = None

    def get_status(self) -> PumpStatus:
        is_active = (self._state == "ON")
        msg = "Pump is currently running (SIMULATED)" if is_active else "Pump is idle (OFF)"
        if not settings.ENABLE_HARDWARE_PUMP:
            msg += " [Hardware Relay Isolated for Safety]"

        return PumpStatus(
            state=self._state,
            is_active=is_active,
            mode=self._mode,
            last_updated=self._last_updated,
            is_hardware_connected=settings.ENABLE_HARDWARE_PUMP,
            message=msg,
        )

    def set_state(self, cmd: PumpCommand) -> PumpStatus:
        raw_state = cmd.state if isinstance(cmd.state, str) else str(cmd.state)
        target_state = raw_state.strip().upper()
        if target_state not in ("ON", "OFF"):
            raise ValueError("Pump state must be 'ON' or 'OFF'")

        raw_mode = cmd.mode if isinstance(cmd.mode, str) else str(cmd.mode or "manual")
        target_mode = raw_mode.strip().lower()
        if target_mode not in ("manual", "auto"):
            raise ValueError("Pump mode must be 'manual' or 'auto'")

        self._state = target_state
        self._mode = target_mode
        self._last_updated = datetime.now(timezone.utc)

        return self.get_status()

pump_manager = PumpManager()
