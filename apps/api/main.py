import sys
sys.path.append('/data/routine/routine-studio-v2')
sys.path.append('/data/routine/routine-studio-v2/apps/api')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from routes.agents import router as agents_router
from routes.assets import router as assets_router
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.studio import router as studio_router
from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title='Routine Studio API v2',
    version='2.0.0',
    description='YouTube Content Automation API',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Register routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(studio_router)
app.include_router(agents_router)
app.include_router(assets_router)

# Static file serving (output folder)
try:
    app.mount('/output', StaticFiles(directory='/data/routine/routine-studio-v2/output'), name='output')
except:
    pass  # Folder may not exist

@app.get('/health')
async def health():
    return {'status': 'ok', 'version': '2.0.0'}

@app.get('/')
async def root():
    return {
        'name': 'Routine Studio API v2',
        'version': '2.0.0',
        'endpoints': {
            'auth': '/api/auth',
            'admin': '/api/admin',
            'agents': '/api/agents',
            'assets': '/api/assets',
            'output': '/output',
            'health': '/health'
        }
    }
