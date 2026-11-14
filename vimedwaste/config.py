"""Đọc configs/labels.yaml và dựng ma trận tương thích A."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "labels.yaml"


@dataclass(frozen=True)
class LabelConfig:
    labels: list[str]
    bins: list[str]
    names: dict[str, str]
    c_fn: dict[str, float]
    A: np.ndarray  # shape (K, B), 1 = được phép
    kappa_min: float
    quality_tag: str
    split_ratios: dict[str, float]
    split_seed: int
    phash_max_distance: int

    def allowed(self, label: str, bin_id: str) -> bool:
        return bool(self.A[self.labels.index(label), self.bins.index(bin_id)])

    def violations(self, present: list[str], bin_id: str) -> list[str]:
        """Các nhãn có mặt nhưng không được phép bỏ vào thùng bin_id."""
        return [k for k in present if not self.allowed(k, bin_id)]


@lru_cache(maxsize=None)
def load_config(path: str | Path = DEFAULT_CONFIG) -> LabelConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    labels = list(raw["labels"])
    bins = list(raw["bins"])
    A = np.zeros((len(labels), len(bins)), dtype=np.int8)
    for k, allowed in raw["compatibility"].items():
        for b in allowed:
            A[labels.index(k), bins.index(b)] = 1
    if (A.sum(axis=1) == 0).any():
        raise ValueError("Mỗi nhãn phải có ít nhất một thùng hợp lệ")
    return LabelConfig(
        labels=labels,
        bins=bins,
        names={k: v["name"] for k, v in raw["labels"].items()},
        c_fn={k: float(v["c_fn"]) for k, v in raw["labels"].items()},
        A=A,
        kappa_min=float(raw["annotation"]["kappa_min"]),
        quality_tag=raw["annotation"]["quality_tag"],
        split_ratios=dict(raw["split"]["ratios"]),
        split_seed=int(raw["split"]["seed"]),
        phash_max_distance=int(raw["dedup"]["phash_max_distance"]),
    )
