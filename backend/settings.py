"""Đường dẫn và cấu hình backend, đọc từ biến môi trường (mặc định cho máy dev).

| Biến                     | Mặc định                         | Ý nghĩa                                         |
|--------------------------|----------------------------------|-------------------------------------------------|
| VIMEDWASTE_DB            | backend/data/vimedwaste.db       | file SQLite (ảnh sự kiện nằm cạnh, thư mục events/) |
| VIMEDWASTE_CORS          | localhost:4200                   | danh sách origin, phân cách dấu phẩy            |
| VIMEDWASTE_SIM_DATA      | data/external/mw40_v01           | bộ ảnh dùng cho /api/simulate                   |
| VIMEDWASTE_STATIC_DIR    | (trống)                          | thư mục build Angular → backend phục vụ luôn FE |
| VIMEDWASTE_PASSWORD      | (trống = không khóa)             | mật khẩu đăng nhập (HTTP Basic, user tùy ý)     |
| VIMEDWASTE_SEED_EVENTS   | 0                                | DB trống lúc khởi động → tự sinh n sự kiện mô phỏng |
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from vimedwaste.core.paths import EXTERNAL_DIR, MODELS_DIR, ROOT  # noqa: F401

ONLINE_WINDOW_S = 120
MW40_DIR = Path(os.environ.get("VIMEDWASTE_SIM_DATA", EXTERNAL_DIR / "mw40_v01"))
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "VIMEDWASTE_CORS", "http://localhost:4200,http://127.0.0.1:4200").split(",") if o.strip()]
STATIC_DIR = Path(os.environ["VIMEDWASTE_STATIC_DIR"]) if os.environ.get("VIMEDWASTE_STATIC_DIR") else None
PASSWORD = os.environ.get("VIMEDWASTE_PASSWORD") or None
SEED_EVENTS = int(os.environ.get("VIMEDWASTE_SEED_EVENTS", "0"))


def db_path() -> Path:
    default = ROOT / "backend" / "data" / "vimedwaste.db"
    return Path(os.environ.get("VIMEDWASTE_DB", default))


def events_dir() -> Path:
    d = db_path().parent / "events"
    d.mkdir(parents=True, exist_ok=True)
    return d


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
