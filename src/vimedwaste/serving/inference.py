"""Chạy mô hình ONNX nếu đã có (ND3 trở đi). Chưa có mô hình → load_predictor() trả về None.

Quy ước file mô hình: artifacts/models/vimedwaste.onnx, đầu vào ảnh 1×3×224×224 đã chuẩn hóa ImageNet,
đầu ra 10 logit đã chia nhiệt độ T (06_DAC_TA_TRIEN_KHAI.md, mục 4.11).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image

from ..core.config import load_config
from ..core.paths import MODELS_DIR

MODEL_PATH = MODELS_DIR / "vimedwaste.onnx"
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(im: Image.Image) -> np.ndarray:
    """Resize cạnh ngắn 256 → crop giữa 224 → chuẩn hóa mean/std ImageNet (mục 4.2)."""
    im = im.convert("RGB")
    w, h = im.size
    s = 256 / min(w, h)
    im = im.resize((round(w * s), round(h * s)), Image.BILINEAR)
    w, h = im.size
    left, top = (w - 224) // 2, (h - 224) // 2
    x = np.asarray(im.crop((left, top, left + 224, top + 224)), dtype=np.float32) / 255.0
    x = (x - MEAN) / STD
    return x.transpose(2, 0, 1)[None]


class OnnxPredictor:
    def __init__(self, path: Path = MODEL_PATH):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        # Máy được cấp ít CPU (hosting miễn phí, Pi) mà thấy nhiều nhân → mặc định mở quá nhiều luồng.
        # VIMEDWASTE_ORT_THREADS=1 để chạy một luồng; 0 hoặc bỏ trống = để onnxruntime tự chọn.
        threads = int(os.environ.get("VIMEDWASTE_ORT_THREADS", "0"))
        if threads > 0:
            opts.intra_op_num_threads = threads
            opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.labels = load_config().labels

    def predict(self, im: Image.Image) -> tuple[dict[str, float], float]:
        """Trả về (xác suất từng nhãn, điểm JointEnergy cho lớp mở)."""
        z = self.session.run(None, {self.input_name: preprocess(im)})[0][0].astype(np.float64)
        probs = 1.0 / (1.0 + np.exp(-z))
        joint_energy = float(np.sum(np.logaddexp(0.0, z)))
        return dict(zip(self.labels, probs.tolist())), joint_energy


def load_predictor(path: Path = MODEL_PATH) -> OnnxPredictor | None:
    if not path.exists():
        return None
    try:
        return OnnxPredictor(path)
    except ImportError:
        return None
