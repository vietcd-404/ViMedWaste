"""Thông tin hiển thị cho nhãn và thùng (tên, nhóm, ví dụ, màu, tiêu đề sự kiện)."""
from __future__ import annotations

from functools import lru_cache

import yaml

from vimedwaste.core.config import DEFAULT_CONFIG, load_config
from vimedwaste.serving.decision import OK, UNKNOWN, bayes_thresholds, correct_bins

GROUP_NAMES = {
    "lay_nhiem_sac_nhon": "Lây nhiễm sắc nhọn",
    "lay_nhiem_khong_sac_nhon": "Lây nhiễm không sắc nhọn",
    "nguy_hai": "Nguy hại không lây nhiễm",
    "tai_che": "Phục vụ tái chế",
    "thong_thuong": "Rắn thông thường",
}

# 06_DAC_TA_TRIEN_KHAI.md, mục 2.2
EXAMPLES = {
    "L01": "Kim tiêm, bơm liền kim, kim truyền, kim châm cứu",
    "L02": "Dao mổ, ống/lọ thủy tinh vỡ, lam kính vỡ",
    "L03": "Bông, băng, gạc đã dùng",
    "L04": "Găng khám, găng phẫu thuật đã dùng",
    "L05": "Dây truyền đã tháo kim, ống thông, túi nước tiểu",
    "L06": "Lọ, chai, vỉ có biểu tượng nguy hại",
    "L07": "Nhiệt kế, huyết áp kế thủy ngân vỡ",
    "L08": "Chai dịch truyền, lọ thuốc không dính máu",
    "L09": "Hộp thuốc giấy, thùng carton",
    "L10": "Thức ăn thừa, khăn giấy, túi nilon",
}

SHORT_NAMES = {
    "L01": "Kim tiêm", "L02": "Vật sắc nhọn", "L03": "Gạc, bông", "L04": "Găng tay",
    "L05": "Dây truyền, túi dịch", "L06": "Bao bì nguy hại", "L07": "Thiết bị thủy ngân",
    "L08": "Chai, lọ", "L09": "Giấy, carton", "L10": "Rác sinh hoạt",
}

BINS = {
    "B1": {"short": "Hộp kháng thủng vàng", "color": "#F2C94C", "border": "#8A6D1E", "word": "hộp vàng"},
    "B2": {"short": "Túi/thùng vàng", "color": "#F2C94C", "border": "#C9A227", "word": "vàng"},
    "B3": {"short": "Đen, nguy hại", "color": "#1F2328", "border": "#1F2328", "word": "đen"},
    "B4": {"short": "Xanh, thông thường", "color": "#2F8A3F", "border": "#22673F", "word": "xanh"},
    "B5": {"short": "Trắng, tái chế", "color": "#FFFFFF", "border": "#9AA3AD", "word": "trắng"},
}


@lru_cache(maxsize=1)
def _raw() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def bins() -> list[dict]:
    names = _raw()["bins"]
    return [{"code": b, "name": names[b], **{k: BINS[b][k] for k in ("short", "color", "border")}}
            for b in load_config().bins]


def labels() -> list[dict]:
    cfg = load_config()
    thr = bayes_thresholds(cfg)
    groups = {k: v["group"] for k, v in _raw()["labels"].items()}
    return [{
        "code": k, "name": cfg.names[k], "group": groups[k], "group_name": GROUP_NAMES[groups[k]],
        "correct_bins": correct_bins(k, cfg), "c_fn": cfg.c_fn[k], "threshold": thr[k],
        "example": EXAMPLES[k],
    } for k in cfg.labels]


def title(status: str, violations: list[str], bin_type: str) -> str:
    if status == OK:
        return "Bỏ đúng thùng"
    if status == UNKNOWN:
        return "Không xác định"
    return f"{SHORT_NAMES[violations[0]]} trong thùng {BINS[bin_type]['word']}"
