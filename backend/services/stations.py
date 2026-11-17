"""Trạm: danh sách, cấu hình vùng thùng, nhịp sống, snapshot, chụp thử."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PIL import Image

from . import NotFound, imaging, model_service
from ..db import connect
from ..settings import ONLINE_WINDOW_S, now_iso


def _station(row) -> dict:
    last = row["last_seen"]
    online = bool(last) and (datetime.now().astimezone() - datetime.fromisoformat(last)).total_seconds() <= ONLINE_WINDOW_S
    return {"id": row["id"], "name": row["name"], "location": row["location"], "online": online,
            "last_seen": last, "zones": json.loads(row["zones_json"]), "settings": json.loads(row["settings_json"])}


def list_stations() -> list[dict]:
    with connect() as c:
        return [_station(r) for r in c.execute("SELECT * FROM stations ORDER BY id")]


def get_station(station_id: str) -> dict:
    with connect() as c:
        row = c.execute("SELECT * FROM stations WHERE id = ?", (station_id,)).fetchone()
    if row is None:
        raise NotFound(f"Không có trạm {station_id}")
    return _station(row)


def station_names() -> dict[str, str]:
    with connect() as c:
        return {r["id"]: r["name"] for r in c.execute("SELECT id, name FROM stations")}


def update_config(station_id: str, zones: list[dict], settings: dict) -> dict:
    get_station(station_id)
    with connect() as c:
        c.execute("UPDATE stations SET zones_json = ?, settings_json = ? WHERE id = ?",
                  (json.dumps(zones), json.dumps(settings), station_id))
    return get_station(station_id)


def heartbeat(station_id: str) -> dict:
    get_station(station_id)
    with connect() as c:
        c.execute("UPDATE stations SET last_seen = ? WHERE id = ?", (now_iso(), station_id))
    return get_station(station_id)


def snapshot_bytes(station_id: str) -> bytes:
    get_station(station_id)
    with connect() as c:
        path = c.execute("SELECT snapshot_path FROM stations WHERE id = ?", (station_id,)).fetchone()[0]
    if path and Path(path).exists():
        return Path(path).read_bytes()
    return imaging.placeholder()


def zone(station: dict, zone_no: int) -> dict:
    for z in station["zones"]:
        if z["zone_no"] == zone_no:
            return z
    raise NotFound(f"Trạm {station['id']} không có vùng {zone_no}")


def test_capture(station_id: str, zone_no: int, image: Image.Image | None) -> dict:
    """Chạy mô hình trên ảnh tải lên (hoặc snapshot cắt theo vùng), không ghi sự kiện."""
    station = get_station(station_id)
    z = zone(station, zone_no)
    if image is None:
        image = imaging.crop_box(imaging.open_image(snapshot_bytes(station_id)), z["box"])
    decision, _ = model_service.predict(image, z["bin_type"])
    return decision
