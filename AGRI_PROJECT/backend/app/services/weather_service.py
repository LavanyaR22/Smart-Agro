import logging
from typing import Optional
import httpx
from backend.app.config import settings
from backend.app.models import WeatherResponse

logger = logging.getLogger(__name__)

class WeatherService:
    """Weather service with robust graceful fallback.
    
    If no OpenWeather API key is configured or the external network request fails,
    it returns realistic default weather metrics so the dashboard remains 100% operational.
    """

    def __init__(self, api_key: Optional[str] = None, city: Optional[str] = None):
        self.api_key = api_key or settings.OPENWEATHER_API_KEY
        self.city = city or settings.WEATHER_CITY

    async def get_current_weather(self, city: Optional[str] = None) -> WeatherResponse:
        target_city = city or self.city

        # If no API key provided, immediately return safe fallback data
        if not self.api_key or self.api_key.strip() == "":
            return WeatherResponse(
                city=target_city,
                temperature=28.5,
                humidity=55.0,
                condition="Partly Cloudy (Simulated)",
                is_fallback=True,
                source="simulation",
                source_detail="Built-in Weather Simulator (No API key required)",
            )

        # Attempt to query OpenWeatherMap API
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": target_city,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    payload = res.json()
                    return WeatherResponse(
                        city=payload.get("name", target_city),
                        temperature=float(payload["main"]["temp"]),
                        humidity=float(payload["main"]["humidity"]),
                        condition=payload["weather"][0]["description"].title() if payload.get("weather") else "Clear",
                        is_fallback=False,
                        source="weather_api",
                        source_detail="OpenWeatherMap Live API",
                    )
                else:
                    logger.warning("OpenWeatherMap returned status %d. Falling back to default.", res.status_code)
        except Exception as e:
            logger.warning("Weather fetch error: %s. Using graceful fallback.", str(e))

        # Graceful fallback on network or API failure
        return WeatherResponse(
            city=target_city,
            temperature=27.0,
            humidity=60.0,
            condition="Fair Weather (Fallback Mode)",
            is_fallback=True,
            source="simulation",
            source_detail="Offline Fallback Module",
        )

weather_service = WeatherService()
