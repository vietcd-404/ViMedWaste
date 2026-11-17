"""Bước 4 – Đồng thuận gán nhãn và phân xử (người phụ trách: Lâm).

  kappa  : Cohen's κ theo từng nhãn, tính trên từng cặp người gán, rồi trung bình có trọng số
           theo số ảnh chung (06_DAC_TA_TRIEN_KHAI.md, mục 3.4). Ghi artifacts/results/agreement_<lô>.json.
  resolve: ảnh hai lượt khớp nhau → nhãn cuối; ảnh bất đồng → disagreements.csv cho người thứ ba.
           Khi đã có file phân xử (cùng cột với annotations), chạy lại với --adjudication.

Ví dụ:
  python -m vimedwaste.data.agreement kappa
  python -m vimedwaste.data.agreement resolve --adjudication data/tables/adjudication.csv
"""
from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from ..core.config import ROOT, load_config
from ..core.schema import label_columns
from ..core.utils import write_result

TABLES = ROOT / "data" / "tables"


def cohen_kappa(a: np.ndarray, b: np.ndarray) -> float:
    """κ cho hai vector nhị phân. Trả về NaN khi không xác định (cả hai luôn cùng một giá trị)."""
    a, b = np.asarray(a, dtype=int), np.asarray(b, dtype=int)
    po = float(np.mean(a == b))
    pa, pb = a.mean(), b.mean()
    pe = pa * pb + (1 - pa) * (1 - pb)
    if np.isclose(pe, 1.0):
        return float("nan")
    return (po - pe) / (1 - pe)


def kappa_per_label(ann: pd.DataFrame, labels: list[str]) -> pd.DataFrame:
    rows = []
    for a1, a2 in combinations(sorted(ann["annotator_id"].unique()), 2):
        x = ann[ann.annotator_id == a1].set_index("image_id")
        y = ann[ann.annotator_id == a2].set_index("image_id")
        common = x.index.intersection(y.index)
        if len(common) == 0:
            continue
        for k in labels:
            rows.append({
                "label": k, "pair": f"{a1}-{a2}", "n_common": len(common),
                "n_positive": int(((x.loc[common, k] + y.loc[common, k]) > 0).sum()),
                "kappa": cohen_kappa(x.loc[common, k], y.loc[common, k]),
            })
    per_pair = pd.DataFrame(rows)
    if per_pair.empty:
        return per_pair

    def weighted(g: pd.DataFrame) -> pd.Series:
        ok = g.dropna(subset=["kappa"])
        k = np.average(ok.kappa, weights=ok.n_common) if len(ok) else float("nan")
        return pd.Series({"kappa": k, "n_common": g.n_common.sum(), "n_positive": g.n_positive.sum()})

    return per_pair.groupby("label").apply(weighted, include_groups=False).reindex(labels).reset_index()


def resolve(ann: pd.DataFrame, labels: list[str], adjudication: pd.DataFrame | None = None):
    """Trả về (labels_df, disagreements_df)."""
    cols = [*labels, "quality_flag"]
    counts = ann.groupby("image_id").size()
    two = ann[ann.image_id.isin(counts[counts >= 2].index)]
    agg = two.groupby("image_id")[cols].agg(["min", "max"])
    agree = pd.Series(True, index=agg.index)
    for c in cols:
        agree &= agg[(c, "min")] == agg[(c, "max")]

    final = two[two.image_id.isin(agree[agree].index)].drop_duplicates("image_id").set_index("image_id")[cols]
    final["adjudicated"] = False
    disagreements = two[two.image_id.isin(agree[~agree].index)].sort_values(["image_id", "annotator_id"])

    if adjudication is not None and len(adjudication):
        adj = adjudication.drop_duplicates("image_id", keep="last").set_index("image_id")[cols]
        adj["adjudicated"] = True
        final = pd.concat([final[~final.index.isin(adj.index)], adj])
        disagreements = disagreements[~disagreements.image_id.isin(adj.index)]

    final["quality_ok"] = final.pop("quality_flag") == 0
    out = final.reset_index()[label_columns(labels)]
    return out, disagreements


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["kappa", "resolve"])
    ap.add_argument("--annotations", type=Path, default=TABLES / "annotations.csv")
    ap.add_argument("--batch", help="chỉ tính trên một lô (ví dụ lô gán thử)")
    ap.add_argument("--adjudication", type=Path)
    args = ap.parse_args()

    cfg = load_config()
    ann = pd.read_csv(args.annotations, dtype={"image_id": str})
    if args.batch:
        ann = ann[ann.batch_id == args.batch]

    if args.mode == "kappa":
        table = kappa_per_label(ann, cfg.labels)
        print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        failing = table[table.kappa < cfg.kappa_min].label.tolist()
        path = write_result(f"agreement_{args.batch or 'all'}", {
            "kappa_min": cfg.kappa_min, "failing_labels": failing,
            "per_label": table.to_dict(orient="records"),
        })
        print(f"\nNhãn dưới ngưỡng {cfg.kappa_min}: {failing or 'không có'}  → {path}")
    else:
        adj = pd.read_csv(args.adjudication, dtype={"image_id": str}) if args.adjudication else None
        labels_df, dis = resolve(ann, cfg.labels, adj)
        labels_df.to_csv(TABLES / "labels.csv", index=False)
        dis.to_csv(TABLES / "disagreements.csv", index=False)
        print(f"labels.csv: {len(labels_df)} ảnh · còn {dis.image_id.nunique()} ảnh chờ phân xử")


if __name__ == "__main__":
    main()
