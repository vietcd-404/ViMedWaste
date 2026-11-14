"""Bước 5 – Chia tập theo nhóm, cân tần suất nhãn (người phụ trách: Lâm).

- Đơn vị chia là nhóm group_id = site_id + capture_date: mọi ảnh của một nhóm vào cùng một tập.
- Phân bổ nhóm theo tinh thần iterative stratification (Sechidis và cs., 2011), áp cho nhóm:
  xử lý nhãn hiếm nhất trước, đưa nhóm vào tập còn "thiếu" nhãn đó nhiều nhất.
- Ảnh OOD không vào splits. Ảnh có source khác vimedwaste không bao giờ vào test.

Ví dụ:
  python -m vimedwaste.data.split
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import ROOT, load_config
from ..schema import OWN_SOURCE, SPLIT_COLUMNS
from ..utils import read_csv, write_result

TABLES = ROOT / "data" / "tables"


def make_group_id(meta: pd.DataFrame) -> pd.Series:
    return meta.site_id.astype(str) + "_" + meta.capture_date.astype(str)


def stratified_group_split(
    df: pd.DataFrame, labels: list[str], ratios: dict[str, float], seed: int = 0,
    allowed: dict[str, list[str]] | None = None,
) -> pd.Series:
    """df có cột group_id và các cột nhãn 0/1. Trả về Series group_id → split.

    allowed: group_id → các tập được phép (mặc định: tất cả).
    """
    rng = np.random.default_rng(seed)
    splits = list(ratios)
    groups = df.groupby("group_id")
    G = groups[labels].sum()                      # số ảnh dương tính mỗi nhãn trong nhóm
    size = groups.size()
    order = rng.permutation(G.index.to_numpy())   # phá thế hòa ngẫu nhiên nhưng tái lập được
    G, size = G.loc[order], size.loc[order]

    total = G.sum()
    need_label = pd.DataFrame({s: total * r for s, r in ratios.items()}).T   # split × label
    need_size = pd.Series({s: size.sum() * r for s, r in ratios.items()})
    assignment: dict[str, str] = {}

    def place(g: str, focus: str | None) -> None:
        options = (allowed or {}).get(g, splits)
        key = (lambda s: (need_label.at[s, focus], need_size[s])) if focus else (lambda s: need_size[s])
        best = max(options, key=key)
        assignment[g] = best
        need_label.loc[best] -= G.loc[g]
        need_size[best] -= size[g]

    remaining = set(G.index)
    while remaining:
        rem = G.loc[[g for g in G.index if g in remaining]]
        counts = rem.sum()
        counts = counts[counts > 0]
        if counts.empty:
            for g in sorted(remaining, key=lambda g: -size[g]):
                place(g, None)
            break
        focus = counts.idxmin()                   # nhãn hiếm nhất trong số nhóm còn lại
        for g in rem[rem[focus] > 0].sort_values(focus, ascending=False).index:
            place(g, focus)
            remaining.discard(g)
    return pd.Series(assignment, name="split")


def build_splits(meta: pd.DataFrame, labels_df: pd.DataFrame, labels: list[str],
                 ratios: dict[str, float], seed: int) -> pd.DataFrame:
    meta = meta[~meta.is_ood.astype(bool)].copy()
    if "group_id" not in meta:
        meta["group_id"] = make_group_id(meta)
    df = meta[["image_id", "group_id", "source"]].merge(labels_df[["image_id", *labels]], on="image_id")
    external = df[df.source != OWN_SOURCE].group_id.unique()
    allowed = {g: [s for s in ratios if s != "test"] for g in external}
    group_split = stratified_group_split(df, labels, ratios, seed, allowed)
    df["split"] = df.group_id.map(group_split)
    return df[SPLIT_COLUMNS]


def split_report(splits: pd.DataFrame, labels_df: pd.DataFrame, labels: list[str]) -> pd.DataFrame:
    m = splits.merge(labels_df[["image_id", *labels]], on="image_id")
    rep = m.groupby("split")[labels].sum()
    rep.insert(0, "n_images", m.groupby("split").size())
    rep.insert(1, "n_groups", m.groupby("split").group_id.nunique())
    return rep


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metadata", type=Path, default=TABLES / "metadata.csv")
    ap.add_argument("--labels", type=Path, default=TABLES / "labels.csv")
    ap.add_argument("--out", type=Path, default=TABLES / "splits.csv")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    if args.out.exists():
        raise SystemExit(f"{args.out} đã tồn tại. Tập chia đã khóa; xóa tay nếu thật sự cần chia lại.")
    cfg = load_config()
    seed = cfg.split_seed if args.seed is None else args.seed
    meta, labels_df = read_csv(args.metadata), read_csv(args.labels)
    labels_df = labels_df[labels_df.quality_ok.astype(bool)]
    splits = build_splits(meta, labels_df, cfg.labels, cfg.split_ratios, seed)
    splits.to_csv(args.out, index=False)

    rep = split_report(splits, labels_df, cfg.labels)
    print(rep.to_string())
    write_result("split", {"ratios": cfg.split_ratios, "report": rep.reset_index().to_dict(orient="records")}, seed)


if __name__ == "__main__":
    main()
