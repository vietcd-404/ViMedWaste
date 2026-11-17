"""SQLite: trạm, sự kiện, hàng chờ gán nhãn lại. Mỗi lần gọi mở một kết nối ngắn."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

from .settings import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, location TEXT NOT NULL,
    last_seen TEXT, zones_json TEXT NOT NULL, settings_json TEXT NOT NULL, snapshot_path TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, station_id TEXT NOT NULL,
    zone_no INTEGER NOT NULL, bin_type TEXT NOT NULL, status TEXT NOT NULL, title TEXT NOT NULL,
    handling TEXT, feedback TEXT, simulated INTEGER NOT NULL DEFAULT 0,
    decision_json TEXT NOT NULL, before_path TEXT, after_path TEXT, gradcam_path TEXT,
    change_box_json TEXT, timeline_json TEXT NOT NULL, source_file TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_time ON events(time);
CREATE TABLE IF NOT EXISTS relabel_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, image_path TEXT,
    note TEXT, created_at TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {"still_seconds": 1.0, "motion_sensitivity": 0.5, "buzzer_volume": 0.6, "dry_run": False}
DEFAULT_ZONES = [
    {"zone_no": 1, "bin_type": "B1", "box": [0.04, 0.2, 0.22, 0.6]},
    {"zone_no": 2, "bin_type": "B2", "box": [0.28, 0.2, 0.22, 0.6]},
    {"zone_no": 3, "bin_type": "B4", "box": [0.52, 0.2, 0.22, 0.6]},
    {"zone_no": 4, "bin_type": "B5", "box": [0.76, 0.2, 0.22, 0.6]},
]
SEED_STATIONS = [
    ("tram-01", "Xe tiêm 01"),
    ("tram-02", "Buồng thủ thuật"),
    ("tram-03", "Xe tiêm 02"),
]


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)
        if c.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO stations (id, name, location, zones_json, settings_json) VALUES (?, ?, ?, ?, ?)",
                [(sid, name, "[Tên khoa]", json.dumps(DEFAULT_ZONES), json.dumps(DEFAULT_SETTINGS))
                 for sid, name in SEED_STATIONS],
            )
