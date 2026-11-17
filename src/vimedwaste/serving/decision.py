"""Quy tắc quyết định: từ xác suất 10 nhãn + loại thùng → PHÙ HỢP / CẢNH BÁO / KHÔNG XÁC ĐỊNH.

Pipeline (06_DAC_TA_TRIEN_KHAI.md, mục 4.1):
  điểm lớp mở S(x) < τ  → KHÔNG XÁC ĐỊNH
  ŷ_k = [p_k ≥ t_k]
  vi phạm = {k : ŷ_k = 1 và A[k, b] = 0} → có vi phạm: CẢNH BÁO, không: PHÙ HỢP
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.config import LabelConfig, load_config

OK, WARN, UNKNOWN = "PHU_HOP", "CANH_BAO", "KHONG_XAC_DINH"


def bayes_thresholds(cfg: LabelConfig | None = None, c_fp: float = 1.0) -> dict[str, float]:
    """Ngưỡng tối ưu theo quy tắc Bayes khi xác suất đã hiệu chuẩn: báo nhãn k khi
    p_k · C_FN,k > (1 − p_k) · C_FP  ⇔  p_k > C_FP / (C_FP + C_FN,k)."""
    cfg = cfg or load_config()
    return {k: c_fp / (c_fp + cfg.c_fn[k]) for k in cfg.labels}


def correct_bins(label: str, cfg: LabelConfig | None = None) -> list[str]:
    cfg = cfg or load_config()
    return [b for b in cfg.bins if cfg.allowed(label, b)]


@dataclass
class Decision:
    status: str
    bin_id: str
    probs: dict[str, float]
    thresholds: dict[str, float]
    present: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    ood_score: float | None = None
    tau: float | None = None


def decide(
    probs: dict[str, float], bin_id: str, *, thresholds: dict[str, float] | None = None,
    ood_score: float | None = None, tau: float | None = None, cfg: LabelConfig | None = None,
) -> Decision:
    cfg = cfg or load_config()
    if bin_id not in cfg.bins:
        raise ValueError(f"bin_id phải thuộc {cfg.bins}")
    missing = set(cfg.labels) - set(probs)
    if missing:
        raise ValueError(f"thiếu xác suất cho {sorted(missing)}")
    t = thresholds or bayes_thresholds(cfg)
    base = dict(bin_id=bin_id, probs=dict(probs), thresholds=t, ood_score=ood_score, tau=tau)

    if ood_score is not None and tau is not None and ood_score < tau:
        return Decision(status=UNKNOWN, **base)
    present = [k for k in cfg.labels if probs[k] >= t[k]]
    # Sắp vi phạm theo mức nguy hiểm: chi phí bỏ sót cao trước.
    violations = sorted(cfg.violations(present, bin_id), key=lambda k: -cfg.c_fn[k])
    return Decision(status=WARN if violations else OK, present=present, violations=violations, **base)
