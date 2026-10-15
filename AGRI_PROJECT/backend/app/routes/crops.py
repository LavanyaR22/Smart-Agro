from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.models import CropProfile, RecommendationResponse
from backend.app.services.recommendation_engine import recommendation_engine
from backend.app.services.telemetry_store import telemetry_store

router = APIRouter(prefix="/api/crops", tags=["Crops & Recommendations"])

@router.get("", response_model=List[CropProfile], summary="List all supported crop profiles")
async def list_crops():
    return recommendation_engine.list_crops()

@router.get("/{crop_id}/recommendation", response_model=RecommendationResponse, summary="Get irrigation recommendation for crop")
async def get_crop_recommendation(
    crop_id: str,
    moisture: Optional[float] = Query(default=None, description="Override moisture value; if omitted, active mode telemetry is used", ge=0.0, le=100.0),
    source: Optional[str] = Query(default=None, description="Target telemetry source: 'hardware' or 'simulation'")
):
    """Calculates whether irrigation is needed based on crop thresholds, active mode, and current moisture."""
    # 1. Validate explicit source query parameter if supplied
    target_source: str
    if source is not None:
        cleaned_source = source.strip().lower()
        if cleaned_source not in ("hardware", "simulation"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source filter '{source}'. Must be 'hardware' or 'simulation'."
            )
        target_source = cleaned_source
    else:
        target_source = telemetry_store.get_active_mode()

    # 2. Case A: Explicit manual moisture override (for testing/calibration scenarios)
    if moisture is not None:
        return recommendation_engine.evaluate(
            crop_id=crop_id,
            current_moisture=moisture,
            source="override",
            device_id="MANUAL_OVERRIDE",
            is_stale=False,
        )

    # 3. Case B: Evaluate telemetry strictly from the selected source
    latest_telemetry = telemetry_store.get_latest(source=target_source)
    status_info = telemetry_store.get_sensor_status(source=target_source)
    is_connected = bool(status_info.get("is_connected", False))

    if not latest_telemetry:
        # Selected source has never reported telemetry: fail-safe NO_DATA
        return recommendation_engine.evaluate(
            crop_id=crop_id,
            current_moisture=None,
            source=target_source,
            device_id=None,
            is_stale=False,
        )

    # If the reading is stale (>30s old / is_connected is False)
    if not is_connected:
        return recommendation_engine.evaluate(
            crop_id=crop_id,
            current_moisture=latest_telemetry.soil_moisture,
            source=target_source,
            device_id=latest_telemetry.device_id,
            is_stale=True,
        )

    # Fresh reading from the selected source
    return recommendation_engine.evaluate(
        crop_id=crop_id,
        current_moisture=latest_telemetry.soil_moisture,
        source=target_source,
        device_id=latest_telemetry.device_id,
        is_stale=False,
    )
