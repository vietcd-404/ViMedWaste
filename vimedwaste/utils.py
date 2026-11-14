"""Tiện ích chung: ghi kết quả kèm commit hash và seed để truy được về báo cáo."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import ROOT

RESULTS_DIR = ROOT / "results"


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "no-git"


def write_result(name: str, payload: dict, seed: int | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": git_commit(),
        "seed": seed,
        **payload,
    }
    path = RESULTS_DIR / f"{name}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"image_id": str, "site_id": str, "group_id": str})


def append_csv(df: pd.DataFrame, path: str | Path) -> None:
    """Ghi nối vào CSV; tạo mới kèm header nếu chưa có."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8")
