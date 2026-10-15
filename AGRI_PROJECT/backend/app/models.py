from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class TelemetryData(BaseModel):
    temperature: float = Field(..., description="Ambient temperature in °C", ge=-20.0, le=60.0)
    humidity: float = Field(..., description="Relative humidity in %", ge=0.0, le=100.0)
    soil_moisture: Optional[float] = Field(default=None, description="Soil moisture in %", ge=0.0, le=100.0)
    raw_soil_adc: Optional[int] = Field(default=None, description="Raw 12-bit analog ADC reading (0-4095)", ge=0, le=4095)
    device_id: str = Field(default="SIMULATED_ESP32", description="Sensor node identifier")
    timestamp: Optional[datetime] = Field(default=None, description="Record timestamp")

    # Soil chemistry & nutrients (optional; unavailable unless explicitly provided/simulated)
    nitrogen: Optional[float] = Field(default=None, description="Soil Nitrogen (N) in mg/kg", ge=0.0, le=500.0)
    phosphorus: Optional[float] = Field(default=None, description="Soil Phosphorus (P) in mg/kg", ge=0.0, le=500.0)
    potassium: Optional[float] = Field(default=None, description="Soil Potassium (K) in mg/kg", ge=0.0, le=500.0)
    ph: Optional[float] = Field(default=None, description="Soil pH level (0-14)", ge=0.0, le=14.0)

    # Source provenance metadata
    source: Optional[str] = Field(
        default=None,
        description="Overall telemetry source classification: 'hardware' | 'simulation'"
    )
    sources: Dict[str, str] = Field(
        default_factory=dict,
        description="Granular per-measurement source tags (e.g. {'soil_moisture': 'hardware', 'nitrogen': 'simulation'})"
    )

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Telemetry source must be a string ('hardware' or 'simulation')")
        cleaned = v.strip().lower()
        if cleaned not in ("hardware", "simulation"):
            raise ValueError(f"Invalid telemetry source '{cleaned}'. Must be 'hardware' or 'simulation'.")
        return cleaned

    @field_validator("sources", mode="before")
    @classmethod
    def validate_sources(cls, v: object) -> Dict[str, str]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("sources must be a key-value dictionary mapping measurement name to source label")
        cleaned = {}
        valid_labels = ("hardware", "simulation", "weather_api", "unavailable")
        for key, val in v.items():
            if val is not None:
                val_str = str(val).strip().lower()
                if val_str not in valid_labels:
                    raise ValueError(f"Invalid source label '{val_str}' for measurement '{key}'. Must be one of {valid_labels}.")
                cleaned[str(key).strip().lower()] = val_str
        return cleaned

    @model_validator(mode="after")
    def populate_default_sources(self) -> "TelemetryData":
        # 1. Determine overall default source if omitted
        if not self.source:
            dev = (self.device_id or "").upper()
            if "SIMULAT" in dev or "VIRTUAL" in dev:
                self.source = "simulation"
            elif "ESP32" in dev or "HARDWARE" in dev or "NODE" in dev:
                self.source = "hardware"
            else:
                self.source = "simulation"

        # 2. Populate per-measurement sources for primary physical readings
        for metric in ("temperature", "humidity"):
            if metric not in self.sources:
                self.sources[metric] = self.source

        if self.soil_moisture is not None:
            if "soil_moisture" not in self.sources:
                self.sources["soil_moisture"] = self.source
        else:
            if "soil_moisture" not in self.sources:
                self.sources["soil_moisture"] = "unavailable"

        if self.raw_soil_adc is not None:
            if "raw_soil_adc" not in self.sources:
                self.sources["raw_soil_adc"] = self.source

        # 3. For soil chemistry (NPK / pH):
        # If value is provided and not tagged, inherit self.source
        # If value is None, tag as 'unavailable'
        for metric in ("nitrogen", "phosphorus", "potassium", "ph"):
            val = getattr(self, metric)
            if val is not None:
                if metric not in self.sources:
                    self.sources[metric] = self.source
            else:
                if metric not in self.sources:
                    self.sources[metric] = "unavailable"

        return self

class PumpCommand(BaseModel):
    state: str = Field(..., description="Pump state: 'ON' or 'OFF'")
    duration_seconds: Optional[int] = Field(default=60, description="Auto-shutoff duration in seconds", ge=1, le=3600)
    mode: str = Field(default="manual", description="Operation mode: 'manual' or 'auto'")

    @field_validator("state", mode="before")
    @classmethod
    def validate_state(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("Pump state must be a string")
        cleaned = v.strip().upper()
        if cleaned not in ("ON", "OFF"):
            raise ValueError("Pump state must be 'ON' or 'OFF'")
        return cleaned

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: object) -> str:
        if v is None:
            return "manual"
        if not isinstance(v, str):
            raise ValueError("Pump mode must be a string")
        cleaned = v.strip().lower()
        if cleaned not in ("manual", "auto"):
            raise ValueError("Pump mode must be 'manual' or 'auto'")
        return cleaned

class PumpStatus(BaseModel):
    state: str
    is_active: bool
    mode: str
    last_updated: datetime
    is_hardware_connected: bool = False
    message: str

class CropProfile(BaseModel):
    id: str
    name: str
    min_moisture: float
    max_moisture: float
    optimal_temp_min: float
    optimal_temp_max: float
    description: str

class RecommendationResponse(BaseModel):
    crop_name: str
    status: str
    pump_recommended: bool
    reason: str
    current_moisture: Optional[float] = None
    target_range: str
    source: Optional[str] = Field(default=None, description="Data provenance: 'hardware', 'simulation', or 'override'")
    device_id: Optional[str] = Field(default=None, description="Device identifier evaluated")
    is_stale: bool = Field(default=False, description="Whether the evaluated telemetry reading was stale (>30s)")


class WeatherResponse(BaseModel):
    city: str
    temperature: float
    humidity: float
    condition: str
    is_fallback: bool
    source: str
    source_detail: Optional[str] = None

class TelemetryModeRequest(BaseModel):
    mode: str = Field(..., description="Target telemetry mode: 'hardware' or 'simulation'")

class TelemetryModeResponse(BaseModel):
    active_mode: str
    available_modes: List[str]
    message: Optional[str] = None
