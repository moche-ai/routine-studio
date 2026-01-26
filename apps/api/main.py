import sys
sys.path.append('/data/routine/routine-studio-v2')
sys.path.append('/data/routine/routine-studio-v2/apps/api')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.agents import router as agents_router
from routes.assets import router as assets_router

app = FastAPI(
    title='Routine Studio API v2',
    version='2.0.0',
    description='YouTube Content Automation API'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 라우터 등록
app.include_router(agents_router)
app.include_router(assets_router)

# 정적 파일 서빙 (output 폴더)
try:
    app.mount('/output', StaticFiles(directory='/data/routine/routine-studio-v2/output'), name='output')
except:
    pass  # 폴더가 없을 수 있음

@app.get('/health')
async def health():
    return {'status': 'ok', 'version': '2.0.0'}

@app.get('/')
async def root():
    return {
        'name': 'Routine Studio API v2',
        'version': '2.0.0',
        'endpoints': {
            'agents': '/api/agents',
            'assets': '/api/assets',
            'output': '/output',
            'health': '/health'
        }
    }
