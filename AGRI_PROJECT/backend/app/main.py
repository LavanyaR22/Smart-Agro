from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.routes import telemetry, pump, crops, weather

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Smart Agriculture IoT Telemetry and Irrigation Recommendation API",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(telemetry.router)
app.include_router(pump.router)
app.include_router(crops.router)
app.include_router(weather.router)

# Mount Frontend static files for single-command launch
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/", summary="Serve Dashboard or Root Status")
async def root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs_url": "/docs",
        "message": "AGRI backend is running. Frontend static directory ready.",
    }

@app.get("/api/health", summary="Health check endpoint")
async def health_check():
    return {
        "status": "healthy",
        "simulation_mode": settings.SIMULATION_MODE,
        "hardware_pump_enabled": settings.ENABLE_HARDWARE_PUMP,
    }
