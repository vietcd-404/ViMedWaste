"""FastAPI app. Chạy từ thư mục ViMedWaste: python -m uvicorn backend.main:app --port 8000

backend/
├─ main.py       tạo app, gắn router, xử lý lỗi
├─ schemas.py    kiểu dữ liệu đầu vào
├─ settings.py   đường dẫn, hằng số
├─ db.py         SQLite
├─ routers/      HTTP: system, stations, events, stats
└─ services/     nghiệp vụ: stations, events, stats, simulation, model_service, catalog, imaging
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import init_db
from .routers import events, stations, stats, system
from .services import NotFound
from .services.model_service import ModelUnavailable
from .settings import CORS_ORIGINS


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="ViMedWaste API", version="0.1.0", lifespan=lifespan, description="Hợp đồng: docs/API.md")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

for module in (system, stations, events, stats):
    app.include_router(module.router)


@app.exception_handler(NotFound)
async def _not_found(_, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ModelUnavailable)
async def _no_model(_, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})
