# api/app.py
# API REST de LRA AI Platform via FastAPI.
# Expone la plataforma via HTTP para integraciones externas.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import platform, projects, cloud

app = FastAPI(
    title="LRA AI Platform API",
    description="AI-Assisted Engineering Platform for DevOps and Platform Engineering",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(platform.router, prefix="/api/v1/platform", tags=["Platform"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(cloud.router, prefix="/api/v1/cloud", tags=["Cloud"])


@app.get("/")
def root():
    return {
        "platform": "LRA AI Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)