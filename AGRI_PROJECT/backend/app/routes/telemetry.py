from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.models import TelemetryData, TelemetryModeRequest, TelemetryModeResponse
from backend.app.services.telemetry_store import telemetry_store

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])

def _validate_source_filter(source: Optional[str]) -> Optional[str]:
    if source is None:
        return None
    cleaned = source.strip().lower()
    if cleaned not in ("hardware", "simulation"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source filter '{source}'. Must be 'hardware' or 'simulation'."
        )
    return cleaned

@router.post("", response_model=TelemetryData, summary="Ingest telemetry from ESP32 or simulator")
async def ingest_telemetry(payload: TelemetryData):
    """Receives sensor metrics (temperature, humidity, soil moisture).
    
    Can be called by either the Python simulator or the real ESP32 microcontroller.
    """
    recorded = telemetry_store.record_telemetry(payload)
    return recorded

@router.get("/mode", response_model=TelemetryModeResponse, summary="Get active telemetry source mode")
async def get_telemetry_mode():
    """Returns the currently active telemetry mode and available choices."""
    return TelemetryModeResponse(
        active_mode=telemetry_store.get_active_mode(),
        available_modes=["hardware", "simulation"],
    )

@router.post("/mode", response_model=TelemetryModeResponse, summary="Set active telemetry source mode")
async def set_telemetry_mode(payload: TelemetryModeRequest):
    """Switches the active telemetry mode between 'hardware' and 'simulation'."""
    try:
        updated_mode = telemetry_store.set_active_mode(payload.mode)
        return TelemetryModeResponse(
            active_mode=updated_mode,
            available_modes=["hardware", "simulation"],
            message=f"Telemetry mode switched to '{updated_mode}' successfully.",
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

@router.get("/latest", response_model=Optional[TelemetryData], summary="Get the most recent sensor reading")
async def get_latest_telemetry(
    source: Optional[str] = Query(default=None, description="Optional source filter: 'hardware' or 'simulation'")
):
    """Returns the most recent sensor reading for the specified source or the active mode."""
    cleaned_source = _validate_source_filter(source)
    latest = telemetry_store.get_latest(source=cleaned_source)
    if not latest:
        # Returns null/empty if no reading has been reported yet for this source
        return None
    return latest

@router.get("/history", response_model=List[TelemetryData], summary="Get historical telemetry series")
async def get_telemetry_history(
    limit: int = Query(default=20, ge=1, le=100),
    source: Optional[str] = Query(default=None, description="Optional source filter: 'hardware' or 'simulation'")
):
    cleaned_source = _validate_source_filter(source)
    return telemetry_store.get_history(limit=limit, source=cleaned_source)

@router.get("/status", summary="Get sensor connection status")
async def get_connection_status(
    source: Optional[str] = Query(default=None, description="Optional source filter: 'hardware' or 'simulation'")
):
    """Returns sensor heartbeat and connection status for the specified source or active mode."""
    cleaned_source = _validate_source_filter(source)
    return telemetry_store.get_sensor_status(source=cleaned_source)
