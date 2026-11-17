"""Bước 2 – Ẩn danh một lô ảnh vừa chụp (người phụ trách: Đạt).

Việc script làm:
  - xoay ảnh theo EXIF rồi ghi lại chỉ phần điểm ảnh → toàn bộ EXIF/GPS bị xóa;
  - đổi tên thành UUID ngẫu nhiên, lưu bảng ánh xạ tên gốc vào mapping/ (chỉ người giữ dữ liệu gốc);
  - sinh các dòng metadata.csv cho lô.

Việc phải làm tay (script không tự làm được): làm mờ tên người bệnh/mã hồ sơ trên bao bì
và loại ảnh có người. Ghi tên file cần loại vào --exclude để script bỏ qua.

Ví dụ:
  python -m vimedwaste.data.anonymize --src data/raw/2026-11-20_S01 --site S01 \
      --date 2026-11-20 --bin B2 --lighting normal
"""
from __future__ import annotations

import argparse
import uuid
from pathlib import Path

import pandas as pd
from PIL import Image, ImageOps

from ..core.config import ROOT, load_config
from ..core.schema import LIGHTING_VALUES, METADATA_COLUMNS, OWN_SOURCE
from ..core.utils import append_csv

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


def strip_and_save(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        # Dựng ảnh mới chỉ từ điểm ảnh: không mang theo EXIF, GPS hay thông tin thiết bị.
        clean = Image.frombytes("RGB", im.size, im.tobytes())
        clean.save(dst, format="JPEG", quality=95)


def anonymize_batch(
    src: Path, out_dir: Path, mapping_csv: Path, metadata_csv: Path, *,
    site: str, date: str, bin_type: str, lighting: str,
    is_simulated: bool = False, is_ood: bool = False, exclude: set[str] = frozenset(),
) -> pd.DataFrame:
    cfg = load_config()
    if bin_type not in cfg.bins:
        raise ValueError(f"bin_type phải thuộc {cfg.bins}")
    if lighting not in LIGHTING_VALUES:
        raise ValueError(f"lighting phải thuộc {sorted(LIGHTING_VALUES)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES and p.name not in exclude)
    meta_rows, map_rows = [], []
    for f in files:
        image_id = uuid.uuid4().hex
        dst = out_dir / f"{image_id}.jpg"
        strip_and_save(f, dst)
        map_rows.append({"image_id": image_id, "original_name": f.name, "batch": src.name})
        meta_rows.append({
            "image_id": image_id,
            "file_path": dst.relative_to(ROOT).as_posix() if dst.is_relative_to(ROOT) else dst.as_posix(),
            "site_id": site, "capture_date": date, "bin_type": bin_type, "lighting": lighting,
            "is_simulated": is_simulated, "is_ood": is_ood, "source": OWN_SOURCE,
        })

    meta = pd.DataFrame(meta_rows, columns=METADATA_COLUMNS)
    append_csv(pd.DataFrame(map_rows), mapping_csv)
    append_csv(meta, metadata_csv)
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, required=True, help="thư mục lô ảnh gốc trong data/raw/")
    ap.add_argument("--site", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--bin", required=True, dest="bin_type")
    ap.add_argument("--lighting", default="normal")
    ap.add_argument("--simulated", action="store_true")
    ap.add_argument("--ood", action="store_true", help="lô ảnh vật thể lạ → lưu vào data/ood/")
    ap.add_argument("--exclude", nargs="*", default=[], help="tên file loại bỏ (có người, không đạt)")
    args = ap.parse_args()

    data = ROOT / "data"
    out_dir = data / ("ood" if args.ood else "anon")
    meta = anonymize_batch(
        args.src, out_dir, data / "mapping" / "mapping.csv", data / "tables" / "metadata.csv",
        site=args.site, date=args.date, bin_type=args.bin_type, lighting=args.lighting,
        is_simulated=args.simulated, is_ood=args.ood, exclude=set(args.exclude),
    )
    print(f"Đã ẩn danh {len(meta)} ảnh → {out_dir}")
    print("Nhắc: kiểm tra và làm mờ thông tin bệnh nhân trên bao bì trước khi đưa lên CVAT.")


if __name__ == "__main__":
    main()
