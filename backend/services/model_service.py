"""Suy luận và Grad-CAM. Mô hình ONNX nạp lại khi file thay đổi; Grad-CAM dùng torch nếu có."""
from __future__ import annotations

import io
import json

import numpy as np
from PIL import Image

from vimedwaste.serving import inference
from vimedwaste.core.config import load_config
from vimedwaste.serving.decision import UNKNOWN, Decision, correct_bins, decide

from . import catalog
from ..settings import MODELS_DIR


class ModelUnavailable(RuntimeError):
    pass


_cache: dict = {"mtime": None, "predictor": None, "meta": None}


def _state() -> dict:
    path = inference.MODEL_PATH
    mtime = path.stat().st_mtime if path.exists() else None
    if mtime != _cache["mtime"]:
        _cache.update(mtime=mtime, predictor=inference.load_predictor(path) if mtime else None,
                      meta=_read_meta(), gradcam=None)
    return _cache


def _read_meta() -> dict:
    p = MODELS_DIR / "meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def model_info() -> dict:
    s = _state()
    meta = s["meta"] or {}
    return {"available": s["predictor"] is not None, "trained_on": meta.get("trained_on"),
            "warning": meta.get("warning")}


def model_detail() -> dict:
    s = _state()
    return {"available": s["predictor"] is not None, **(s["meta"] or {})}


def decision_dict(d: Decision) -> dict:
    names = load_config().names
    labels = [{
        "code": k, "name": names[k], "prob": float(p), "threshold": float(d.thresholds[k]),
        "present": k in d.present, "violation": k in d.violations, "correct_bins": correct_bins(k),
    } for k, p in d.probs.items()]
    return {
        "status": d.status, "bin_type": d.bin_id, "title": catalog.title(d.status, d.violations, d.bin_id),
        "labels": labels, "violations": list(d.violations),
        "ood_score": d.ood_score, "tau": d.tau, "accepted": d.status != UNKNOWN,
        "model": model_info(),
    }


def predict(im: Image.Image, bin_type: str) -> tuple[dict, Decision]:
    s = _state()
    if s["predictor"] is None:
        raise ModelUnavailable("Chưa có mô hình (artifacts/models/vimedwaste.onnx)")
    probs, score = s["predictor"].predict(im)
    tau = (s["meta"] or {}).get("tau")
    d = decide(probs, bin_type, ood_score=score, tau=tau)
    return decision_dict(d), d


# ---------- Grad-CAM ----------

def _gradcam_model():
    s = _state()
    if s.get("gradcam") is not None:
        return s["gradcam"]
    head_path = MODELS_DIR / "head.pt"
    try:
        import torch
        from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0
    except ImportError:
        return None
    if not head_path.exists():
        return None
    ckpt = torch.load(head_path, map_location="cpu")
    net = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1).eval()
    head = torch.nn.Linear(1280, len(load_config().labels))
    head.load_state_dict(ckpt["state_dict"])
    s["gradcam"] = (net, head.eval(), float(ckpt["temperature"]))
    return s["gradcam"]


def _crop224(im: Image.Image) -> Image.Image:
    """Cùng phép resize + crop giữa như inference.preprocess, để ảnh nền khớp bản đồ nhiệt."""
    im = im.convert("RGB")
    w, h = im.size
    k = 256 / min(w, h)
    im = im.resize((round(w * k), round(h * k)), Image.BILINEAR)
    w, h = im.size
    left, top = (w - 224) // 2, (h - 224) // 2
    return im.crop((left, top, left + 224, top + 224))


def gradcam_png(im: Image.Image, label: str) -> bytes | None:
    model = _gradcam_model()
    if model is None:
        return None
    import torch

    net, head, temperature = model
    idx = load_config().labels.index(label)
    x = torch.from_numpy(inference.preprocess(im))
    acts = net.features(x)                   # 1 × 1280 × 7 × 7
    acts.retain_grad()
    feat = net.avgpool(acts).flatten(1)
    logit = head(feat)[0, idx] / temperature
    logit.backward()
    weights = acts.grad.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * acts).sum(dim=1))[0].detach().numpy()
    if cam.max() > 0:
        cam = cam / cam.max()
    heat = Image.fromarray(np.uint8(cam * 255)).resize((224, 224), Image.BILINEAR)
    return _overlay(_crop224(im), np.asarray(heat, dtype=np.float32) / 255.0)


def _overlay(base: Image.Image, cam: np.ndarray) -> bytes:
    # Bảng màu vàng → đỏ, độ trong suốt theo cường độ.
    r = np.full_like(cam, 230.0)
    g = 200.0 * (1 - cam)
    b = np.full_like(cam, 40.0)
    color = np.stack([r, g, b], axis=-1)
    alpha = (cam * 0.6)[..., None]
    out = np.asarray(base, dtype=np.float32) * (1 - alpha) + color * alpha
    buf = io.BytesIO()
    Image.fromarray(np.uint8(out.clip(0, 255))).save(buf, format="PNG")
    return buf.getvalue()


def gradcam_target(d: Decision) -> str:
    if d.violations:
        return d.violations[0]
    return max(d.probs, key=d.probs.get)
