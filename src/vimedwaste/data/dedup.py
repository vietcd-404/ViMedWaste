"""Lọc ảnh trùng và gần trùng bằng perceptual hash (người phụ trách: Lâm).

Chạy ở hai thời điểm:
  - sau bước ẩn danh: tìm ảnh chụp lặp để loại trước khi gán nhãn;
  - sau bước chia tập (--splits): đếm cặp gần trùng nằm ở HAI tập khác nhau (rò rỉ).

Khoảng cách Hamming ≤ phash_max_distance (configs/labels.yaml) coi là gần trùng.
Ngưỡng 6 là điểm khởi đầu, cần xem tay vài cặp để chỉnh.

Ví dụ:
  python -m vimedwaste.data.dedup --metadata data/tables/metadata.csv
  python -m vimedwaste.data.dedup --metadata data/tables/metadata.csv --splits data/tables/splits.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import imagehash
import numpy as np
import pandas as pd
from PIL import Image

from ..core.config import ROOT, load_config
from ..core.utils import read_csv, write_result


def compute_hashes(meta: pd.DataFrame, base: Path = ROOT, cache: Path | None = None) -> pd.DataFrame:
    """Trả về DataFrame image_id, phash (int 64 bit). Dùng cache nếu đã tính trước."""
    known = pd.DataFrame(columns=["image_id", "phash"])
    if cache and cache.exists():
        known = pd.read_csv(cache, dtype={"image_id": str, "phash": str})
    todo = meta[~meta.image_id.isin(known.image_id)]
    rows = []
    for image_id, rel in zip(todo.image_id, todo.file_path):
        with Image.open(base / rel) as im:
            rows.append({"image_id": image_id, "phash": str(imagehash.phash(im))})
    out = pd.concat([known, pd.DataFrame(rows)], ignore_index=True)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(cache, index=False)
    out = out[out.image_id.isin(meta.image_id)].copy()
    out["phash"] = out.phash.map(lambda h: int(h, 16)).astype(np.uint64)
    return out


def near_duplicate_pairs(hashes: pd.DataFrame, max_distance: int) -> pd.DataFrame:
    ids = hashes.image_id.to_numpy()
    h = hashes.phash.to_numpy(dtype=np.uint64)
    pairs = []
    for i in range(len(h) - 1):
        x = np.bitwise_xor(h[i], h[i + 1:])
        dist = np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
        for j in np.nonzero(dist <= max_distance)[0]:
            pairs.append((ids[i], ids[i + 1 + j], int(dist[j])))
    return pd.DataFrame(pairs, columns=["image_id_a", "image_id_b", "distance"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metadata", type=Path, required=True)
    ap.add_argument("--splits", type=Path, help="kiểm tra rò rỉ giữa các tập")
    ap.add_argument("--base", type=Path, default=ROOT, help="gốc của cột file_path")
    ap.add_argument("--max-distance", type=int)
    ap.add_argument("--tag", default="own", help="hậu tố tên file kết quả")
    args = ap.parse_args()

    cfg = load_config()
    max_d = args.max_distance if args.max_distance is not None else cfg.phash_max_distance
    meta = read_csv(args.metadata)
    out_dir = args.metadata.parent
    hashes = compute_hashes(meta, args.base, out_dir / "phash.csv")
    pairs = near_duplicate_pairs(hashes, max_d)

    summary = {"n_images": len(meta), "max_distance": max_d, "n_pairs": len(pairs),
               "n_images_in_pairs": int(pd.unique(pairs[["image_id_a", "image_id_b"]].values.ravel()).size)}
    if args.splits:
        split = read_csv(args.splits).set_index("image_id").split
        pairs["split_a"] = pairs.image_id_a.map(split)
        pairs["split_b"] = pairs.image_id_b.map(split)
        cross = pairs.dropna(subset=["split_a", "split_b"])
        cross = cross[cross.split_a != cross.split_b]
        summary["n_cross_split_pairs"] = len(cross)
        summary["cross_split_by_pair"] = (cross.split_a + "-" + cross.split_b).value_counts().to_dict()

    pairs.to_csv(out_dir / "near_duplicates.csv", index=False)
    path = write_result(f"dedup_{args.tag}", summary)
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"→ {out_dir / 'near_duplicates.csv'} · {path}")


if __name__ == "__main__":
    main()
