from typing import Dict, List, Optional
from backend.app.models import CropProfile, RecommendationResponse

DEFAULT_CROPS: Dict[str, CropProfile] = {
    "wheat": CropProfile(
        id="wheat",
        name="Wheat",
        min_moisture=45.0,
        max_moisture=65.0,
        optimal_temp_min=15.0,
        optimal_temp_max=25.0,
        description="Requires moderate moisture; sensitive to waterlogging during flowering.",
    ),
    "tomato": CropProfile(
        id="tomato",
        name="Tomato",
        min_moisture=60.0,
        max_moisture=80.0,
        optimal_temp_min=18.0,
        optimal_temp_max=27.0,
        description="Needs consistent moisture; dry spells cause blossom end rot.",
    ),
    "rice": CropProfile(
        id="rice",
        name="Rice (Paddy)",
        min_moisture=70.0,
        max_moisture=95.0,
        optimal_temp_min=20.0,
        optimal_temp_max=35.0,
        description="High water demand crop; requires continuous damp to flooded soil.",
    ),
    "maize": CropProfile(
        id="maize",
        name="Maize (Corn)",
        min_moisture=50.0,
        max_moisture=70.0,
        optimal_temp_min=18.0,
        optimal_temp_max=32.0,
        description="Moderate water needs; critical water demand during silking stage.",
    ),
    "cotton": CropProfile(
        id="cotton",
        name="Cotton",
        min_moisture=40.0,
        max_moisture=60.0,
        optimal_temp_min=21.0,
        optimal_temp_max=37.0,
        description="Drought-tolerant, deep-rooted crop; avoids excess water during boll opening.",
    ),
}

class RecommendationEngine:
    def __init__(self, crops: Optional[Dict[str, CropProfile]] = None):
        self.crops = crops or DEFAULT_CROPS

    def list_crops(self) -> List[CropProfile]:
        return list(self.crops.values())

    def get_crop(self, crop_id: str) -> Optional[CropProfile]:
        return self.crops.get(crop_id.lower())

    def evaluate(
        self,
        crop_id: str,
        current_moisture: Optional[float],
        source: Optional[str] = None,
        device_id: Optional[str] = None,
        is_stale: bool = False,
    ) -> RecommendationResponse:
        crop = self.get_crop(crop_id)
        if not crop:
            return RecommendationResponse(
                crop_name=crop_id,
                status="UNKNOWN_CROP",
                pump_recommended=False,
                reason=f"Crop '{crop_id}' is not in database. Please select a recognized crop.",
                current_moisture=current_moisture,
                target_range="N/A",
                source=source,
                device_id=device_id,
                is_stale=is_stale,
            )

        target_range = f"{crop.min_moisture}% - {crop.max_moisture}%"

        # Safety Check 1: Stale or offline telemetry
        if is_stale:
            src_desc = f" from source '{source}'" if source else ""
            return RecommendationResponse(
                crop_name=crop.name,
                status="STALE_DATA",
                pump_recommended=False,
                reason=f"Telemetry reading{src_desc} is stale or offline (>30s old). Irrigation withheld for safety.",
                current_moisture=current_moisture,
                target_range=target_range,
                source=source,
                device_id=device_id,
                is_stale=True,
            )

        # Safety Check 2: Missing or uncalibrated soil moisture
        if current_moisture is None:
            if source == "hardware":
                reason = "Hardware soil moisture is uncalibrated/unavailable (raw ADC requires sensor calibration). Irrigation withheld for safety."
            else:
                reason = "No valid soil moisture reading available. Please wait for sensor telemetry."
            return RecommendationResponse(
                crop_name=crop.name,
                status="NO_DATA",
                pump_recommended=False,
                reason=reason,
                current_moisture=None,
                target_range=target_range,
                source=source,
                device_id=device_id,
                is_stale=False,
            )

        if current_moisture < crop.min_moisture:
            deficit = round(crop.min_moisture - current_moisture, 1)
            return RecommendationResponse(
                crop_name=crop.name,
                status="WATER_NEEDED",
                pump_recommended=True,
                reason=f"Soil moisture ({current_moisture}%) is {deficit}% below minimum threshold ({crop.min_moisture}%). Irrigation recommended.",
                current_moisture=current_moisture,
                target_range=target_range,
                source=source,
                device_id=device_id,
                is_stale=False,
            )
        elif current_moisture > crop.max_moisture:
            surplus = round(current_moisture - crop.max_moisture, 1)
            return RecommendationResponse(
                crop_name=crop.name,
                status="EXCESS_WATER",
                pump_recommended=False,
                reason=f"Soil moisture ({current_moisture}%) is {surplus}% above optimal maximum ({crop.max_moisture}%). Keep pump OFF to prevent root rot.",
                current_moisture=current_moisture,
                target_range=target_range,
                source=source,
                device_id=device_id,
                is_stale=False,
            )
        else:
            return RecommendationResponse(
                crop_name=crop.name,
                status="OPTIMAL",
                pump_recommended=False,
                reason=f"Soil moisture ({current_moisture}%) is within the optimal range ({target_range}). No irrigation needed.",
                current_moisture=current_moisture,
                target_range=target_range,
                source=source,
                device_id=device_id,
                is_stale=False,
            )

recommendation_engine = RecommendationEngine()
