"""Thông tin hệ thống: sức khỏe, danh mục nhãn/thùng, mô hình, dự đoán một ảnh."""
from __future__ import annotations

import base64

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from vimedwaste.core.config import load_config

from . import read_image
from ..services import catalog, model_service

router = APIRouter(prefix="/api", tags=["Hệ thống"])


@router.get("/health")
def health():
    return {"status": "ok", "model_available": model_service.model_info()["available"]}


@router.get("/labels")
def labels():
    items = catalog.labels()
    return {"labels": items, "bins": catalog.bins(),
            "compatibility": {l["code"]: l["correct_bins"] for l in items}}


@router.get("/model")
def model():
    return model_service.model_detail()


@router.post("/predict")
async def predict(image: UploadFile = File(...), bin_type: str = Form(...)):
    if bin_type not in load_config().bins:
        raise HTTPException(status_code=422, detail="bin_type phải thuộc B1–B5")
    im = await read_image(image, required=True)
    decision, d = model_service.predict(im, bin_type)
    png = model_service.gradcam_png(im, model_service.gradcam_target(d))
    decision["gradcam"] = "data:image/png;base64," + base64.b64encode(png).decode() if png else None
    return decision
