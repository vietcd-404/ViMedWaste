"""Xử lý ảnh phụ trợ: đọc ảnh tải lên, lưu ảnh sự kiện, vùng thay đổi, ảnh snapshot giữ chỗ."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

MAX_SIDE = 1280


def open_image(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    return ImageOps.exif_transpose(im).convert("RGB")


def save_jpeg(im: Image.Image, path: Path) -> Path:
    im = im.copy()
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    im.save(path, format="JPEG", quality=88)
    return path


def crop_box(im: Image.Image, box: list[float]) -> Image.Image:
    x, y, w, h = box
    W, H = im.size
    return im.crop((round(x * W), round(y * H), round((x + w) * W), round((y + h) * H)))


def change_box(before: Image.Image, after: Image.Image, threshold: int = 40) -> list[float] | None:
    """Hộp bao vùng khác nhau giữa hai ảnh (tỷ lệ 0..1 trên ảnh sau). Không khác → None."""
    size = (128, 72) if after.width >= after.height else (72, 128)
    a = np.asarray(before.convert("L").resize(size).filter(ImageFilter.GaussianBlur(1.5)), dtype=np.int16)
    b = np.asarray(after.convert("L").resize(size).filter(ImageFilter.GaussianBlur(1.5)), dtype=np.int16)
    mask = np.abs(a - b) > threshold
    if mask.mean() < 0.002:
        return None
    ys, xs = np.nonzero(mask)
    W, H = size
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return [x0 / W, y0 / H, (x1 - x0) / W, (y1 - y0) / H]


def placeholder(text: str = "Chưa có ảnh camera", size=(1280, 720)) -> bytes:
    im = Image.new("RGB", size, (200, 203, 200))
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        font, text = ImageFont.load_default(), "Chua co anh camera"
    w = draw.textlength(text, font=font)
    draw.text(((size[0] - w) / 2, size[1] / 2 - 20), text, fill=(90, 96, 105), font=font)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
