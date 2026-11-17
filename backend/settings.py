"""Đường dẫn và hằng số của backend. Đọc biến môi trường lúc gọi để test đổi được DB tạm."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from vimedwaste.core.paths import EXTERNAL_DIR, MODELS_DIR, ROOT  # noqa: F401
MW40_DIR = EXTERNAL_DIR / "mw40_v01"
ONLINE_WINDOW_S = 120
CORS_ORIGINS = ["http://localhost:4200", "http://127.0.0.1:4200"]


def db_path() -> Path:
    default = ROOT / "backend" / "data" / "vimedwaste.db"
    return Path(os.environ.get("VIMEDWASTE_DB", default))


def events_dir() -> Path:
    d = db_path().parent / "events"
    d.mkdir(parents=True, exist_ok=True)
    return d


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
