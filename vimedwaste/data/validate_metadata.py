"""Kiểm tra ràng buộc lược đồ trước mỗi lần xuất dataset (người phụ trách: Em).

Kiểm tra những bảng có mặt trong thư mục: metadata, annotations, labels, splits.
Thoát với mã 1 nếu có lỗi, để chặn bước phát hành.

Ví dụ:
  python -m vimedwaste.data.validate_metadata --tables data/tables --check-files
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from ..config import ROOT, load_config
from ..schema import (LIGHTING_VALUES, METADATA_COLUMNS, NO_BIN, OWN_SOURCE, SPLIT_COLUMNS,
                      SPLIT_VALUES, annotation_columns, label_columns)
from ..utils import read_csv


def _missing_columns(df: pd.DataFrame, cols: list[str], name: str) -> list[str]:
    miss = [c for c in cols if c not in df.columns]
    return [f"{name}: thiếu cột {miss}"] if miss else []


def check_metadata(meta: pd.DataFrame, base: Path | None = None) -> list[str]:
    cfg = load_config()
    errs = _missing_columns(meta, METADATA_COLUMNS, "metadata")
    if errs:
        return errs
    if meta.image_id.duplicated().any():
        errs.append(f"metadata: {meta.image_id.duplicated().sum()} image_id trùng")
    nulls = meta[METADATA_COLUMNS].isna().sum()
    errs += [f"metadata: cột {c} có {n} ô trống" for c, n in nulls.items() if n]

    own = meta.source == OWN_SOURCE
    bad_bin = own & ~meta.bin_type.isin(cfg.bins)
    bad_bin |= ~own & ~meta.bin_type.isin([*cfg.bins, NO_BIN])
    if bad_bin.any():
        errs.append(f"metadata: {bad_bin.sum()} ảnh có bin_type không hợp lệ")
    if (~meta.lighting.isin(LIGHTING_VALUES)).any():
        errs.append(f"metadata: lighting phải thuộc {sorted(LIGHTING_VALUES)}")
    if pd.to_datetime(meta.capture_date, format="%Y-%m-%d", errors="coerce").isna().any():
        errs.append("metadata: capture_date phải có dạng YYYY-MM-DD")
    for c in ("is_simulated", "is_ood"):
        if not meta[c].astype(str).str.lower().isin({"true", "false"}).all():
            errs.append(f"metadata: {c} phải là true/false")
    if base is not None:
        missing = [p for p in meta.file_path if not (base / p).exists()]
        if missing:
            errs.append(f"metadata: {len(missing)} file ảnh không tồn tại, ví dụ {missing[:3]}")
    return errs


def check_annotations(ann: pd.DataFrame, meta: pd.DataFrame) -> list[str]:
    cfg = load_config()
    errs = _missing_columns(ann, annotation_columns(cfg.labels), "annotations")
    if errs:
        return errs
    if ann.duplicated(["image_id", "annotator_id"]).any():
        errs.append("annotations: có ảnh được cùng một người gán hai lần")
    if (~ann.image_id.isin(meta.image_id)).any():
        errs.append("annotations: có image_id không có trong metadata")
    if not ann[[*cfg.labels, "quality_flag"]].isin([0, 1]).all().all():
        errs.append("annotations: giá trị nhãn phải là 0/1")
    return errs


def check_labels(labels: pd.DataFrame, meta: pd.DataFrame) -> list[str]:
    cfg = load_config()
    errs = _missing_columns(labels, label_columns(cfg.labels), "labels")
    if errs:
        return errs
    if labels.image_id.duplicated().any():
        errs.append("labels: image_id trùng")
    if (~labels.image_id.isin(meta.image_id)).any():
        errs.append("labels: có image_id không có trong metadata")
    if not labels[cfg.labels].isin([0, 1]).all().all():
        errs.append("labels: giá trị nhãn phải là 0/1")
    return errs


def check_splits(splits: pd.DataFrame, meta: pd.DataFrame) -> list[str]:
    errs = _missing_columns(splits, SPLIT_COLUMNS, "splits")
    if errs:
        return errs
    m = splits.merge(meta[["image_id", "is_ood", "source"]], on="image_id", how="left")
    if m.source.isna().any():
        errs.append("splits: có image_id không có trong metadata")
    if (~splits.split.isin(SPLIT_VALUES)).any():
        errs.append(f"splits: split phải thuộc {sorted(SPLIT_VALUES)}")
    if m.is_ood.astype(str).str.lower().eq("true").any():
        errs.append("splits: ảnh OOD không được nằm trong splits")
    if ((m.source != OWN_SOURCE) & (m.split == "test")).any():
        errs.append("splits: ảnh ngoài không được vào tập test")
    per_group = splits.groupby("group_id").split.nunique()
    if (per_group > 1).any():
        errs.append(f"splits: {int((per_group > 1).sum())} nhóm nằm ở nhiều tập (rò rỉ)")
    return errs


def validate(tables: Path, base: Path | None = None) -> list[str]:
    meta_path = tables / "metadata.csv"
    if not meta_path.exists():
        return [f"không tìm thấy {meta_path}"]
    meta = read_csv(meta_path)
    errs = check_metadata(meta, base)
    checks = {"annotations.csv": check_annotations, "labels.csv": check_labels, "splits.csv": check_splits}
    for name, fn in checks.items():
        if (tables / name).exists():
            errs += fn(read_csv(tables / name), meta)
    return errs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", type=Path, default=ROOT / "data" / "tables")
    ap.add_argument("--check-files", action="store_true", help="kiểm tra file ảnh có tồn tại")
    ap.add_argument("--base", type=Path, default=ROOT, help="gốc của cột file_path")
    args = ap.parse_args()

    errs = validate(args.tables, args.base if args.check_files else None)
    if errs:
        print("KHÔNG ĐẠT:")
        for e in errs:
            print(" -", e)
        sys.exit(1)
    print(f"ĐẠT: {args.tables} thỏa mọi ràng buộc.")


if __name__ == "__main__":
    main()
