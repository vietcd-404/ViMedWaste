"""Số liệu cho trang Tổng quan."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime

from vimedwaste.core.config import load_config
from vimedwaste.serving.decision import UNKNOWN, WARN

from .stations import list_stations
from ..db import connect


def overview(date: str | None = None) -> dict:
    date = date or datetime.now().astimezone().date().isoformat()
    with connect() as c:
        rows = c.execute("SELECT status, handling, simulated, decision_json FROM events WHERE substr(time, 1, 10) = ?",
                         (date,)).fetchall()
    warnings = [r for r in rows if r["status"] == WARN]
    handled = sum(r["handling"] == "DA_LAY_RA" for r in warnings)
    counts = Counter(k for r in warnings for k in json.loads(r["decision_json"])["violations"])
    names = load_config().names
    return {
        "date": date, "total": len(rows), "warnings": len(warnings),
        "handled_pct": round(100.0 * handled / len(warnings), 1) if warnings else 0.0,
        "unknown": sum(r["status"] == UNKNOWN for r in rows),
        "top_mislabels": [{"code": k, "name": names[k], "count": n} for k, n in counts.most_common(5)],
        "stations": [{"id": s["id"], "name": s["name"], "online": s["online"]} for s in list_stations()],
        "simulated": any(r["simulated"] for r in rows),
    }
