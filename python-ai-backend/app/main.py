# author: jf
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import ALL_ROUTERS
from app.api.errors.handlers import register_error_handlers
from app.infrastructure.config.settings import get_settings

settings = get_settings()
app = FastAPI(title="python-ai-backend", version="0.1.0")
BOOT_TIME = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.app_cors_allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "UP"}


@app.get("/health/runtime")
def health_runtime(request: Request) -> dict[str, str | int]:
    return {
        "status": "UP",
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
        "pythonExecutable": sys.executable,
        "appFile": str(Path(__file__).resolve()),
        "configuredPort": settings.server_port,
        "requestPort": request.url.port or settings.server_port,
        "bootTime": BOOT_TIME,
    }


register_error_handlers(app)

for route in ALL_ROUTERS:
    app.include_router(route)
