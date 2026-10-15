from fastapi import APIRouter, HTTPException, status
from backend.app.models import PumpCommand, PumpStatus
from backend.app.services.pump_manager import pump_manager

router = APIRouter(prefix="/api/pump", tags=["Pump Control"])

@router.get("/status", response_model=PumpStatus, summary="Get current irrigation pump status")
async def get_pump_status():
    return pump_manager.get_status()

@router.post("/control", response_model=PumpStatus, summary="Manually trigger pump state (Simulated)")
async def control_pump(command: PumpCommand):
    """Toggles pump state between ON and OFF.
    
    Safe default: Runs in simulated mode unless hardware relay is explicitly enabled.
    """
    try:
        updated_status = pump_manager.set_state(command)
        return updated_status
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

