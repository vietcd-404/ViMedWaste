"""Mọi đường dẫn của dự án ở một chỗ. Đổi cấu trúc thư mục thì chỉ sửa file này."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # thư mục ViMedWaste/

CONFIGS_DIR = ROOT / "configs"
DATA_DIR = ROOT / "data"                            # dữ liệu: KHÔNG đưa ảnh gốc và mapping lên Git
TABLES_DIR = DATA_DIR / "tables"                    # bảng của ảnh tự chụp
EXTERNAL_DIR = DATA_DIR / "external"                # dữ liệu ngoài (Medical Waste 4.0, …)
FEATURES_DIR = DATA_DIR / "features"                # cache đặc trưng trích từ backbone

ARTIFACTS_DIR = ROOT / "artifacts"                  # mọi thứ do code sinh ra
MODELS_DIR = ARTIFACTS_DIR / "models"               # vimedwaste.onnx, meta.json, head.pt
RESULTS_DIR = ARTIFACTS_DIR / "results"             # *.json kèm commit + seed
