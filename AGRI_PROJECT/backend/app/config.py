import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if it exists
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "AGRI Smart Irrigation System"
    VERSION: str = "0.1.0"
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # Safety defaults: physical hardware pump control is disabled by default
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "True").lower() in ("true", "1", "yes")
    ENABLE_HARDWARE_PUMP: bool = os.getenv("ENABLE_HARDWARE_PUMP", "False").lower() in ("true", "1", "yes")

    # Weather service (graceful fallback if empty)
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    WEATHER_CITY: str = os.getenv("WEATHER_CITY", "New Delhi")

settings = Settings()
