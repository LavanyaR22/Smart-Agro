from typing import Optional
from fastapi import APIRouter, Query
from backend.app.models import WeatherResponse
from backend.app.services.weather_service import weather_service

router = APIRouter(prefix="/api/weather", tags=["Weather Integration"])

@router.get("/current", response_model=WeatherResponse, summary="Get local weather metrics with safe offline fallback")
async def get_current_weather(city: Optional[str] = Query(default=None, description="City name (optional)")):
    """Returns weather information for the specified city.
    
    If OpenWeather API key is not configured or network is unreachable,
    returns safe fallback data without failing or blocking the dashboard.
    """
    return await weather_service.get_current_weather(city=city)
