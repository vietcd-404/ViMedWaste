"""Thống kê tổng quan và sinh dữ liệu mô phỏng."""
from __future__ import annotations

from fastapi import APIRouter

from ..schemas import SimulateRequest
from ..services import simulation, stats

router = APIRouter(prefix="/api", tags=["Thống kê"])


@router.get("/stats/overview")
def overview(date: str | None = None):
    return stats.overview(date)


@router.post("/simulate")
def simulate(body: SimulateRequest | None = None):
    """Chỉ dùng khi demo: sự kiện sinh ra có simulated=true."""
    body = body or SimulateRequest()
    created = simulation.simulate(body.n, body.seed)
    return {"created": len(created), "event_ids": [e["id"] for e in created]}
