"""Sự kiện: ảnh chụp từ trạm → mô hình → quyết định → lưu; phản hồi và trạng thái xử lý."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from vimedwaste.core.config import load_config
from vimedwaste.serving.decision import OK, UNKNOWN, WARN

from . import NotFound, imaging, model_service
from .stations import get_station, station_names, zone
from ..db import connect
from ..settings import events_dir, now_iso

DEFAULT_HANDLING = {WARN: "CHUA_XU_LY", UNKNOWN: "CHO_XEM_LAI", OK: None}
HANDLING_TEXT = {"DA_LAY_RA": "Vật đã được lấy ra, bỏ đúng thùng", "CHUA_XU_LY": "Chuyển về chưa xử lý",
                 "CHO_XEM_LAI": "Chuyển sang chờ xem lại"}


def _first_timeline(d, bin_type: str, dry_run: bool, time: str) -> list[dict]:
    names = load_config().names
    if d.status == WARN:
        return [{"time": time, "text": "Phát hiện vật bỏ sai: " + ", ".join(names[k] for k in d.violations)},
                {"time": time, "text": "Chế độ chạy thử: chỉ ghi nhật ký, không bật đèn/còi" if dry_run
                 else f"Bật đèn đỏ và còi ở thùng {bin_type}"}]
    if d.status == UNKNOWN:
        return [{"time": time, "text": "Ảnh không quen thuộc (S(x) < τ): ghi không xác định, không báo động"}]
    return [{"time": time, "text": "Bỏ đúng thùng, không cảnh báo"}]


def process_capture(station_id: str, zone_no: int, image: Image.Image, before: Image.Image | None = None,
                    *, time: str | None = None, simulated: bool = False, source_file: str | None = None) -> dict:
    """Đường xử lý chung cho thiết bị thật (/capture) và mô phỏng (/simulate)."""
    station = get_station(station_id)
    bin_type = zone(station, zone_no)["bin_type"]
    decision, d = model_service.predict(image, bin_type)
    time = time or now_iso()

    # 1. Ghi sự kiện để có id đặt tên file ảnh
    with connect() as c:
        prev = c.execute(
            "SELECT after_path FROM events WHERE station_id = ? AND zone_no = ? AND time <= ? "
            "ORDER BY time DESC, id DESC LIMIT 1", (station_id, zone_no, time)).fetchone()
        cur = c.execute(
            "INSERT INTO events (time, station_id, zone_no, bin_type, status, title, handling, simulated, "
            "decision_json, timeline_json, source_file) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (time, station_id, zone_no, bin_type, d.status, decision["title"], DEFAULT_HANDLING[d.status],
             int(simulated), json.dumps(decision, ensure_ascii=False),
             json.dumps(_first_timeline(d, bin_type, station["settings"]["dry_run"], time), ensure_ascii=False),
             source_file))
        event_id = cur.lastrowid

    # 2. Lưu ảnh sau / trước; không có ảnh trước thì dùng ảnh sau gần nhất của cùng vùng
    folder = events_dir()
    after_path = imaging.save_jpeg(image, folder / f"{event_id}_after.jpg")
    before_path = None
    if before is not None:
        before_path = imaging.save_jpeg(before, folder / f"{event_id}_before.jpg")
    elif prev and prev["after_path"] and Path(prev["after_path"]).exists():
        before_path = Path(prev["after_path"])
        before = Image.open(before_path).convert("RGB")
    box = imaging.change_box(before, Image.open(after_path).convert("RGB")) if before is not None else None

    # 3. Grad-CAM (nếu có PyTorch)
    png = model_service.gradcam_png(image, model_service.gradcam_target(d))
    gradcam_path = None
    if png:
        gradcam_path = folder / f"{event_id}_gradcam.png"
        gradcam_path.write_bytes(png)

    with connect() as c:
        c.execute("UPDATE events SET after_path = ?, before_path = ?, gradcam_path = ?, change_box_json = ? WHERE id = ?",
                  (str(after_path), str(before_path) if before_path else None,
                   str(gradcam_path) if gradcam_path else None, json.dumps(box) if box else None, event_id))
        c.execute("UPDATE stations SET snapshot_path = ?, last_seen = ? WHERE id = ?",
                  (str(after_path), now_iso(), station_id))
    return get_event(event_id)


def _summary(row, names: dict) -> dict:
    return {"id": row["id"], "time": row["time"], "station_id": row["station_id"],
            "station_name": names.get(row["station_id"], row["station_id"]),
            "zone_no": row["zone_no"], "bin_type": row["bin_type"], "status": row["status"],
            "title": row["title"], "handling": row["handling"], "feedback": row["feedback"],
            "simulated": bool(row["simulated"])}


def list_events(status: str | None = None, station_id: str | None = None, limit: int = 50) -> list[dict]:
    sql, args = "SELECT * FROM events WHERE 1 = 1", []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if station_id:
        sql += " AND station_id = ?"
        args.append(station_id)
    sql += " ORDER BY time DESC, id DESC LIMIT ?"
    args.append(limit)
    names = station_names()
    with connect() as c:
        return [_summary(r, names) for r in c.execute(sql, args)]


def _row(event_id: int):
    with connect() as c:
        row = c.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        raise NotFound(f"Không có sự kiện {event_id}")
    return row


def get_event(event_id: int) -> dict:
    row = _row(event_id)
    url = f"/api/events/{event_id}/image"
    return {
        **_summary(row, station_names()),
        "decision": json.loads(row["decision_json"]),
        "images": {"before": f"{url}/before" if row["before_path"] else None,
                   "after": f"{url}/after",
                   "gradcam": f"{url}/gradcam" if row["gradcam_path"] else None},
        "change_box": json.loads(row["change_box_json"]) if row["change_box_json"] else None,
        "timeline": json.loads(row["timeline_json"]),
    }


def event_image(event_id: int, kind: str) -> Path:
    path = _row(event_id)[f"{kind}_path"]
    if not path or not Path(path).exists():
        raise NotFound(f"Sự kiện {event_id} không có ảnh {kind}")
    return Path(path)


def _append_timeline(c, event_id: int, text: str) -> None:
    timeline = json.loads(c.execute("SELECT timeline_json FROM events WHERE id = ?", (event_id,)).fetchone()[0])
    timeline.append({"time": now_iso(), "text": text})
    c.execute("UPDATE events SET timeline_json = ? WHERE id = ?", (json.dumps(timeline, ensure_ascii=False), event_id))


def set_feedback(event_id: int, verdict: str, note: str | None = None) -> dict:
    """NHAM → ảnh vào hàng chờ gán nhãn lại để huấn luyện bổ sung."""
    row = _row(event_id)
    with connect() as c:
        c.execute("UPDATE events SET feedback = ? WHERE id = ?", (verdict, event_id))
        if verdict == "NHAM":
            c.execute("INSERT INTO relabel_queue (event_id, image_path, note, created_at) VALUES (?, ?, ?, ?)",
                      (event_id, row["after_path"], note, now_iso()))
            _append_timeline(c, event_id, "Báo nhầm: ảnh đưa vào hàng chờ gán nhãn lại")
        else:
            _append_timeline(c, event_id, "Người quản lý xác nhận kết quả đúng")
    return get_event(event_id)


def set_handling(event_id: int, handling: str) -> dict:
    _row(event_id)
    with connect() as c:
        c.execute("UPDATE events SET handling = ? WHERE id = ?", (handling, event_id))
        _append_timeline(c, event_id, HANDLING_TEXT[handling])
    return get_event(event_id)


def relabel_queue() -> list[dict]:
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM relabel_queue ORDER BY id")]
