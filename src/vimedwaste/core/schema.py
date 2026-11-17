"""Lược đồ bốn bảng CSV (Việt thiết kế). Tên cột tập trung ở đây để mọi script dùng chung."""
from __future__ import annotations

METADATA_COLUMNS = [
    "image_id", "file_path", "site_id", "capture_date", "bin_type",
    "lighting", "is_simulated", "is_ood", "source",
]
LIGHTING_VALUES = {"normal", "low", "mixed", "unknown"}
OWN_SOURCE = "vimedwaste"
NO_BIN = "none"  # ảnh ngoài không chụp trong thùng (không dùng "NA": pandas đọc thành ô trống)


def annotation_columns(labels: list[str]) -> list[str]:
    return ["image_id", "annotator_id", "batch_id", *labels, "quality_flag"]


def label_columns(labels: list[str]) -> list[str]:
    return ["image_id", *labels, "adjudicated", "quality_ok"]


SPLIT_COLUMNS = ["image_id", "group_id", "split"]
SPLIT_VALUES = {"train", "val", "test"}
