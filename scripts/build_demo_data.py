"""Tạo bộ ảnh demo nhỏ cho bản deploy: lấy đều mỗi lớp của Medical Waste 4.0, thu nhỏ, ghi data/demo/.

Bản deploy chỉ cần ảnh để sinh sự kiện mô phỏng (/api/simulate), không cần 555 MB ảnh gốc.

  python scripts/build_demo_data.py --per-class 14 --max-side 960
"""
from __future__ import annotations

import argparse
import shutil

import pandas as pd
from PIL import Image

from vimedwaste.core.paths import DATA_DIR, EXTERNAL_DIR, ROOT


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-class", type=int, default=14)
    ap.add_argument("--max-side", type=int, default=960)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    meta = pd.read_csv(EXTERNAL_DIR / "mw40_v01" / "metadata.csv", dtype={"image_id": str})
    picks = (meta.groupby("source_class", group_keys=False)
                 .apply(lambda g: g.sample(min(len(g), args.per_class), random_state=args.seed)))

    out = DATA_DIR / "demo"
    shutil.rmtree(out, ignore_errors=True)
    (out / "images").mkdir(parents=True)
    rows = []
    for r in picks.itertuples():
        dst = out / "images" / f"{r.image_id}.jpg"
        with Image.open(ROOT / r.file_path) as im:
            im = im.convert("RGB")
            im.thumbnail((args.max_side, args.max_side))
            im.save(dst, quality=88)
        rows.append({**r._asdict(), "file_path": dst.relative_to(ROOT).as_posix()})
    pd.DataFrame(rows).drop(columns="Index").to_csv(out / "metadata.csv", index=False)

    size = sum(p.stat().st_size for p in (out / "images").iterdir()) / 2**20
    print(f"{len(rows)} ảnh ({picks.is_ood.sum()} OOD) · {size:.1f} MB → {out}")


if __name__ == "__main__":
    main()
