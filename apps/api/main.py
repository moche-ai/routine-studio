import sys
import os

# Add paths for both Docker and native execution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from routes.agents import router as agents_router
from routes.assets import router as assets_router
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.studio import router as studio_router
from routes.tts import router as tts_router
from database import init_db
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Routine Studio API v2",
    version="2.0.0",
    description="YouTube Content Automation API",
    lifespan=lifespan
)

# CORS: Load from settings (credentials=True requires explicit origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(studio_router)
app.include_router(agents_router)
app.include_router(assets_router)
app.include_router(tts_router)

# Static file serving (output folder)
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")
try:
    app.mount("/output", StaticFiles(directory=output_dir), name="output")
except:
    pass  # Folder may not exist

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/")
async def root():
    return {
        "name": "Routine Studio API v2",
        "version": "2.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "admin": "/api/admin",
            "agents": "/api/agents",
            "assets": "/api/assets",
            "tts": "/api/tts",
            "output": "/output",
            "health": "/health"
        }
    }
