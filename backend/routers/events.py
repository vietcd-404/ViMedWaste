"""Sự kiện: danh sách, chi tiết, ảnh, phản hồi, trạng thái xử lý."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from ..schemas import Feedback, Handling
from ..services import events

router = APIRouter(prefix="/api/events", tags=["Sự kiện"])


@router.get("")
def list_events(status: str | None = None, station_id: str | None = None, limit: int = Query(50, ge=1, le=500)):
    return events.list_events(status, station_id, limit)


@router.get("/{event_id}")
def get_event(event_id: int):
    return events.get_event(event_id)


@router.get("/{event_id}/image/{kind}")
def event_image(event_id: int, kind: Literal["before", "after", "gradcam"]):
    path = events.event_image(event_id, kind)
    return FileResponse(path, media_type="image/png" if path.suffix == ".png" else "image/jpeg")


@router.post("/{event_id}/feedback")
def feedback(event_id: int, body: Feedback):
    return events.set_feedback(event_id, body.verdict, body.note)


@router.post("/{event_id}/handling")
def handling(event_id: int, body: Handling):
    return events.set_handling(event_id, body.handling)
