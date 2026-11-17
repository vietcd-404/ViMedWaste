"""Bước 3 – Chuyển file xuất CVAT thành annotations.csv (người phụ trách: Việt).

Trên CVAT, mỗi ảnh được gán bằng tag mức ảnh: L01 … L10 và tag chất lượng (bad_quality).
Xuất task theo định dạng "CVAT for images 1.1" (annotations.xml). Mỗi người gán là một task riêng.

Tên ảnh trên CVAT phải là <image_id>.jpg như sau bước ẩn danh.

Ví dụ:
  python -m vimedwaste.data.cvat_export --xml exports/lo01_dat.xml --annotator dat --batch lo01
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from ..core.config import ROOT, load_config
from ..core.schema import annotation_columns
from ..core.utils import append_csv


def parse_cvat_xml(xml_path: Path, annotator: str, batch: str) -> pd.DataFrame:
    cfg = load_config()
    known = set(cfg.labels) | {cfg.quality_tag}
    rows = []
    for image in ET.parse(xml_path).getroot().iter("image"):
        image_id = Path(image.get("name")).stem
        tags = {t.get("label") for t in image.iter("tag")}
        unknown = tags - known
        if unknown:
            raise ValueError(f"{image_id}: tag lạ {sorted(unknown)}")
        row = {"image_id": image_id, "annotator_id": annotator, "batch_id": batch}
        row.update({k: int(k in tags) for k in cfg.labels})
        row["quality_flag"] = int(cfg.quality_tag in tags)
        rows.append(row)
    return pd.DataFrame(rows, columns=annotation_columns(cfg.labels))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml", type=Path, required=True)
    ap.add_argument("--annotator", required=True)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "tables" / "annotations.csv")
    args = ap.parse_args()

    df = parse_cvat_xml(args.xml, args.annotator, args.batch)
    if args.out.exists():
        old = pd.read_csv(args.out, dtype={"image_id": str})
        dup = old.merge(df, on=["image_id", "annotator_id"])
        if len(dup):
            raise SystemExit(f"{len(dup)} ảnh đã có lượt gán của {args.annotator}; không ghi đè.")
    append_csv(df, args.out)
    print(f"Đã thêm {len(df)} lượt gán của {args.annotator} (lô {args.batch}) → {args.out}")


if __name__ == "__main__":
    main()
