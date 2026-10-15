import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from backend.app.models import TelemetryData

CACHE_FILE = Path(__file__).resolve().parent.parent / "telemetry_cache.json"

class TelemetryStore:
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self._active_mode: str = "hardware"
        self._history: deque[TelemetryData] = deque(maxlen=max_history)
        self._latest_by_source: Dict[str, Optional[TelemetryData]] = {
            "hardware": None,
            "simulation": None,
        }
        self._last_received_by_source: Dict[str, Optional[datetime]] = {
            "hardware": None,
            "simulation": None,
        }
        # Backward-compatible references to overall latest
        self._latest: Optional[TelemetryData] = None
        self._last_received_at: Optional[datetime] = None
        self._load_cache()

    def get_active_mode(self) -> str:
        return self._active_mode

    def set_active_mode(self, mode: str) -> str:
        if not isinstance(mode, str):
            raise ValueError("Mode must be a string ('hardware' or 'simulation')")
        cleaned = mode.strip().lower()
        if cleaned not in ("hardware", "simulation"):
            raise ValueError(f"Invalid mode '{mode}'. Must be 'hardware' or 'simulation'.")
        self._active_mode = cleaned
        self._save_cache()
        return self._active_mode

    def _load_cache(self) -> None:
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                    # 1. Load active mode if persisted
                    saved_mode = raw.get("active_mode")
                    if saved_mode in ("hardware", "simulation"):
                        self._active_mode = saved_mode

                    # 2. Load independent per-source latest records if available
                    sources_data = raw.get("sources")
                    if isinstance(sources_data, dict):
                        for src in ("hardware", "simulation"):
                            src_info = sources_data.get(src)
                            if isinstance(src_info, dict):
                                if src_info.get("latest"):
                                    rec = TelemetryData(**src_info["latest"])
                                    self._latest_by_source[src] = rec
                                    self._history.append(rec)
                                if src_info.get("last_received_at"):
                                    self._last_received_by_source[src] = datetime.fromisoformat(
                                        src_info["last_received_at"]
                                    )

                    # 3. Backward-compatible fallback for legacy cache files
                    if "latest" in raw and raw["latest"]:
                        legacy_rec = TelemetryData(**raw["latest"])
                        self._latest = legacy_rec
                        src = legacy_rec.source or "simulation"
                        if src in self._latest_by_source and self._latest_by_source[src] is None:
                            self._latest_by_source[src] = legacy_rec
                            if raw.get("last_received_at") and self._last_received_by_source[src] is None:
                                self._last_received_by_source[src] = datetime.fromisoformat(raw["last_received_at"])
                            if legacy_rec not in self._history:
                                self._history.append(legacy_rec)

                    if raw.get("last_received_at"):
                        self._last_received_at = datetime.fromisoformat(raw["last_received_at"])

                    # Synchronize overall latest with active mode reading if available
                    active_rec = self._latest_by_source.get(self._active_mode)
                    if active_rec:
                        self._latest = active_rec
                        self._last_received_at = self._last_received_by_source.get(self._active_mode)
        except Exception:
            pass

    def _save_cache(self) -> None:
        try:
            sources_payload = {}
            for src in ("hardware", "simulation"):
                rec = self._latest_by_source.get(src)
                rx_at = self._last_received_by_source.get(src)
                sources_payload[src] = {
                    "latest": rec.model_dump(mode="json") if rec else None,
                    "last_received_at": rx_at.isoformat() if rx_at else None,
                }

            # Top-level 'latest' mirrors active mode for backward compatibility
            active_rec = self._latest_by_source.get(self._active_mode) or self._latest
            active_rx = self._last_received_by_source.get(self._active_mode) or self._last_received_at

            payload = {
                "active_mode": self._active_mode,
                "sources": sources_payload,
                "latest": active_rec.model_dump(mode="json") if active_rec else None,
                "last_received_at": active_rx.isoformat() if active_rx else None,
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception:
            pass

    def record_telemetry(self, data: TelemetryData) -> TelemetryData:
        now = datetime.now(timezone.utc)
        if data.timestamp is None:
            data.timestamp = now

        src = (data.source or "simulation").strip().lower()
        if src not in ("hardware", "simulation"):
            src = "simulation"

        # Record in dedicated per-source slot
        self._latest_by_source[src] = data
        self._last_received_by_source[src] = now

        # Maintain overall latest reference
        self._latest = data
        self._last_received_at = now

        self._history.append(data)
        self._save_cache()
        return data

    def get_latest(self, source: Optional[str] = None) -> Optional[TelemetryData]:
        target_src = (source or self._active_mode).strip().lower()
        if target_src in self._latest_by_source:
            return self._latest_by_source[target_src]
        return None

    def get_history(self, limit: int = 50, source: Optional[str] = None) -> List[TelemetryData]:
        items = list(self._history)
        if source:
            src_clean = source.strip().lower()
            items = [item for item in items if (item.source or "").lower() == src_clean]
        return items[-limit:]

    def get_sensor_status(self, source: Optional[str] = None) -> Dict[str, object]:
        target_src = (source or self._active_mode).strip().lower()
        last_rx = self._last_received_by_source.get(target_src)
        latest_rec = self._latest_by_source.get(target_src)

        if not last_rx or not latest_rec:
            return {
                "is_connected": False,
                "status": f"Awaiting initial reading ({target_src})",
                "seconds_since_last_beat": None,
                "device_id": None,
                "source": target_src,
                "active_mode": self._active_mode,
            }

        now = datetime.now(timezone.utc)
        elapsed = (now - last_rx).total_seconds()
        is_alive = elapsed < 30.0  # alive if pinged within 30 seconds

        return {
            "is_connected": is_alive,
            "status": "Online (Active)" if is_alive else "Offline (Stale)",
            "seconds_since_last_beat": round(elapsed, 1),
            "device_id": latest_rec.device_id,
            "source": latest_rec.source or target_src,
            "active_mode": self._active_mode,
        }

    def reset(self) -> None:
        """Reset in-memory state (used for clean isolated unit testing)."""
        self._active_mode = "hardware"
        self._history.clear()
        self._latest_by_source = {"hardware": None, "simulation": None}
        self._last_received_by_source = {"hardware": None, "simulation": None}
        self._latest = None
        self._last_received_at = None

telemetry_store = TelemetryStore()

