"""Sinh sự kiện mô phỏng từ ảnh Medical Waste 4.0, đi qua đúng đường xử lý của /capture."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

import pandas as pd
from PIL import Image

from .events import process_capture
from .stations import list_stations
from ..settings import MW40_DIR, ROOT


def simulate(n: int = 12, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    meta = pd.read_csv(MW40_DIR / "metadata.csv")
    used = meta[~meta.is_ood.astype(bool)]
    ood = meta[meta.is_ood.astype(bool)]
    n_ood = max(1, round(n * 0.25)) if n >= 2 else 0          # khoảng 1/4 là vật lạ
    picks = pd.concat([used.sample(n - n_ood, random_state=rng.randint(0, 10**6)),
                       ood.sample(n_ood, random_state=rng.randint(0, 10**6))])

    # Thời điểm rải đều từ 7h sáng hôm nay đến hiện tại
    stations = list_stations()
    now = datetime.now().astimezone()
    start = now.replace(hour=7, minute=0, second=0, microsecond=0)
    if start >= now:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    span = max(1, int((now - start).total_seconds()) - 60)
    times = sorted(start + timedelta(seconds=rng.randint(0, span)) for _ in range(len(picks)))

    out = []
    for (_, r), t in zip(picks.sample(frac=1, random_state=rng.randint(0, 10**6)).iterrows(), times):
        st = rng.choice(stations)
        z = rng.choice(st["zones"])
        image = Image.open(ROOT / r.file_path).convert("RGB")
        out.append(process_capture(st["id"], z["zone_no"], image, time=t.isoformat(timespec="seconds"),
                                   simulated=True, source_file=r.file_path))
    return out
