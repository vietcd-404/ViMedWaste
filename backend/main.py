"""FastAPI app. Chạy từ thư mục ViMedWaste: python -m uvicorn backend.main:app --port 8000

backend/
├─ main.py       tạo app, gắn router, xử lý lỗi, (tùy chọn) phục vụ giao diện Angular
├─ schemas.py    kiểu dữ liệu đầu vào
├─ settings.py   cấu hình từ biến môi trường
├─ security.py   khóa bằng mật khẩu khi deploy công khai
├─ db.py         SQLite
├─ routers/      HTTP: system, stations, events, stats
└─ services/     nghiệp vụ: stations, events, stats, simulation, model_service, catalog, imaging
"""
from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .db import connect, init_db
from .routers import events, stations, stats, system
from .security import PasswordMiddleware
from .services import NotFound, simulation
from .services.model_service import ModelUnavailable
from .settings import CORS_ORIGINS, PASSWORD, SEED_EVENTS, STATIC_DIR


def _seed_if_empty() -> None:
    """Hosting miễn phí xóa dữ liệu mỗi lần khởi động lại → sinh lại sự kiện mô phỏng."""
    with connect() as c:
        if c.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
            simulation.simulate(SEED_EVENTS, seed=0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if SEED_EVENTS:
        # Chạy nền: CPU gói miễn phí yếu, phải mở cổng ngay kẻo nền tảng tưởng app treo
        threading.Thread(target=_seed_if_empty, daemon=True).start()
    yield


app = FastAPI(title="ViMedWaste API", version="0.1.0", lifespan=lifespan, description="Hợp đồng: docs/API.md")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
if PASSWORD:
    app.add_middleware(PasswordMiddleware, password=PASSWORD)

for module in (system, stations, events, stats):
    app.include_router(module.router)


@app.exception_handler(NotFound)
async def _not_found(_, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ModelUnavailable)
async def _no_model(_, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# Một container phục vụ cả giao diện: file tĩnh của Angular, đường dẫn lạ → index.html (router phía client).
if STATIC_DIR and (STATIC_DIR / "index.html").exists():
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Không có endpoint này"})
        f = (STATIC_DIR / path).resolve()
        if path and f.is_file() and STATIC_DIR.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(STATIC_DIR / "index.html")
