"""Nhập bộ Medical Waste 4.0 v0.1 làm dữ liệu ngoài (người phụ trách: Việt).

Nguồn: https://zenodo.org/records/7643417 · CC BY 4.0
Trích dẫn: Bruno A. và cs., ICASSPW 2023, DOI 10.1109/ICASSPW59220.2023.10193520

- Chỉ lấy ảnh RGB (*.jpeg), bỏ cặp ảnh stereo _l.png/_r.png.
- Ánh xạ lớp: gauze → L03; 6 lớp glove → L04; urine_bag → L05;
  medical_cap, medical_glasses, shoe_cover_* → OOD gần; test_tube → bỏ (nhãn phụ thuộc tình trạng).
- Tên file là mốc thời gian (ms). Ảnh cách nhau > 10 phút tính là phiên chụp mới → group_id.
- Mỗi lớp gần như chỉ có một phiên ngắn, ảnh liên tiếp rất giống nhau. Vì vậy chia train/val theo
  KHỐI THỜI GIAN trong từng lớp (70 % đầu → train, 30 % cuối → val), không chia ngẫu nhiên.
  Không có tập test: dữ liệu ngoài không bao giờ vào test.
- Không sao chép ảnh; file_path trỏ về thư mục gốc. Bảng ghi riêng trong data/external/mw40_v01/.

Ví dụ:
  python -m vimedwaste.data.import_mw40 --src "../Medical Waste 4.0"
"""
from __future__ import annotations

import argparse
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..core.config import ROOT, load_config
from ..core.schema import METADATA_COLUMNS, NO_BIN, SPLIT_COLUMNS, label_columns
from ..core.utils import write_result

SOURCE = "mw40_v01"
LICENSE = "CC BY 4.0"
SOURCE_URL = "https://zenodo.org/records/7643417"
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, SOURCE_URL)
SESSION_GAP_MS = 10 * 60 * 1000
TRAIN_FRACTION = 0.70

CLASS_MAP = {
    "gauze": "L03",
    "glove_pair_latex": "L04", "glove_pair_nitrile": "L04", "glove_pair_surgery": "L04",
    "glove_single_latex": "L04", "glove_single_nitrile": "L04", "glove_single_surgery": "L04",
    "urine_bag": "L05",
    "medical_cap": "OOD", "medical_glasses": "OOD",
    "shoe_cover_pair": "OOD", "shoe_cover_single": "OOD",
    "test_tube": None,
}


def scan(src: Path) -> pd.DataFrame:
    rows = []
    for cls_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        if cls_dir.name not in CLASS_MAP:
            raise ValueError(f"Lớp lạ trong bộ dữ liệu: {cls_dir.name}")
        for f in sorted(cls_dir.glob("*.jpeg")):
            rows.append({"source_class": cls_dir.name, "path": f, "ts": int(f.stem)})
    return pd.DataFrame(rows)


def assign_sessions_and_blocks(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["source_class", "ts"]).copy()
    new_session = df.groupby("source_class").ts.diff().fillna(SESSION_GAP_MS + 1) > SESSION_GAP_MS
    df["session"] = new_session.groupby(df.source_class).cumsum().astype(int)
    rank = df.groupby("source_class").cumcount()
    n = df.groupby("source_class").ts.transform("size")
    df["split"] = (rank < (n * TRAIN_FRACTION).round()).map({True: "train", False: "val"})
    # Nhóm = khối thời gian (lớp × tập). Ảnh sát ranh giới hai khối vẫn có thể gần trùng:
    # đo bằng dedup --splits, không coi khối là độc lập hoàn toàn.
    df["group_id"] = SOURCE + "_" + df.source_class + "_" + df.split
    return df


def build_tables(src: Path) -> dict[str, pd.DataFrame]:
    cfg = load_config()
    df = assign_sessions_and_blocks(scan(src))
    df["mapped_to"] = df.source_class.map(CLASS_MAP)
    df["image_id"] = [uuid.uuid5(NAMESPACE, f"{c}/{p.name}").hex for c, p in zip(df.source_class, df.path)]
    df["status"] = df.mapped_to.map(lambda m: "skipped" if pd.isna(m) else ("ood" if m == "OOD" else "used"))

    manifest = pd.DataFrame({
        "image_id": df.image_id, "source_file": [p.as_posix() for p in df.path],
        "source_class": df.source_class, "mapped_to": df.mapped_to.fillna(""), "status": df.status,
        "license": LICENSE, "source_url": SOURCE_URL,
    })

    kept = df[df.status != "skipped"]
    meta = pd.DataFrame({
        "image_id": kept.image_id,
        "file_path": [Path(os.path.relpath(p, ROOT)).as_posix() for p in kept.path],
        "site_id": SOURCE,
        "capture_date": [datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d") for t in kept.ts],
        "bin_type": NO_BIN, "lighting": "unknown", "is_simulated": False,
        "is_ood": kept.status == "ood", "source": SOURCE,
        "group_id": kept.group_id, "source_class": kept.source_class,
    })[[*METADATA_COLUMNS, "group_id", "source_class"]]

    used = kept[kept.status == "used"]
    labels = pd.DataFrame({"image_id": used.image_id})
    for k in cfg.labels:
        labels[k] = (used.mapped_to == k).astype(int).to_numpy()
    labels["adjudicated"] = False
    labels["quality_ok"] = True
    labels = labels[label_columns(cfg.labels)]

    splits = used[SPLIT_COLUMNS].reset_index(drop=True)
    return {"manifest": manifest, "metadata": meta, "labels": labels, "splits": splits}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, required=True, help="thư mục đã giải nén Medical Waste 4.0")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "external" / SOURCE)
    args = ap.parse_args()

    tables = build_tables(args.src.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(args.out / f"{name}.csv", index=False, encoding="utf-8")

    man, sp = tables["manifest"], tables["splits"]
    labels = tables["labels"].merge(sp, on="image_id")
    summary = {
        "source": SOURCE, "license": LICENSE, "source_url": SOURCE_URL,
        "status_counts": man.status.value_counts().to_dict(),
        "per_class": man.groupby(["source_class", "mapped_to"]).size().reset_index(name="n").to_dict(orient="records"),
        "label_by_split": labels.groupby("split")[["L03", "L04", "L05"]].sum().to_dict(),
        "n_groups": int(tables["metadata"].group_id.nunique()),
    }
    path = write_result(f"import_{SOURCE}", summary)
    print(man.groupby(["source_class", "mapped_to", "status"]).size().to_string())
    print("\nẢnh dùng cho nhãn theo tập:")
    print(labels.groupby("split")[["L03", "L04", "L05"]].sum().to_string())
    print(f"\nĐã ghi {', '.join(tables)} → {args.out} · {path}")


if __name__ == "__main__":
    main()
