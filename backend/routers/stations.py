"""Trạm và API thiết bị Pi gọi (heartbeat, capture)."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from . import read_image
from ..schemas import StationConfig
from ..services import events, stations

router = APIRouter(prefix="/api/stations", tags=["Trạm"])


@router.get("")
def list_stations():
    return stations.list_stations()


@router.get("/{station_id}")
def get_station(station_id: str):
    return stations.get_station(station_id)


@router.put("/{station_id}/config")
def put_config(station_id: str, body: StationConfig):
    return stations.update_config(station_id, [z.model_dump() for z in body.zones], body.settings.model_dump())


@router.get("/{station_id}/snapshot")
def snapshot(station_id: str):
    return Response(content=stations.snapshot_bytes(station_id), media_type="image/jpeg")


@router.post("/{station_id}/heartbeat")
def heartbeat(station_id: str):
    return stations.heartbeat(station_id)


@router.post("/{station_id}/capture")
async def capture(station_id: str, zone_no: int = Form(...), image: UploadFile = File(...),
                  before_image: UploadFile | None = File(None)):
    """Thiết bị gọi sau khi tay rút ra: chạy mô hình, ghi sự kiện."""
    im = await read_image(image, required=True)
    return events.process_capture(station_id, zone_no, im, await read_image(before_image))


@router.post("/{station_id}/test-capture")
async def test_capture(station_id: str, zone_no: int = Form(...), image: UploadFile | None = File(None)):
    return stations.test_capture(station_id, zone_no, await read_image(image))
