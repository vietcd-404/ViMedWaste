"""Kiểu dữ liệu đầu vào của API (pydantic). Hợp đồng đầy đủ: docs/API.md."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from vimedwaste.core.config import load_config


class Zone(BaseModel):
    zone_no: int = Field(ge=1)
    bin_type: str
    box: list[float] = Field(min_length=4, max_length=4)   # [x, y, w, h], tỷ lệ 0..1

    @field_validator("bin_type")
    @classmethod
    def _bin(cls, v: str) -> str:
        if v not in load_config().bins:
            raise ValueError("bin_type phải thuộc B1–B5")
        return v

    @field_validator("box")
    @classmethod
    def _box(cls, v: list[float]) -> list[float]:
        x, y, w, h = v
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.0001 and y + h <= 1.0001):
            raise ValueError("box phải là [x, y, w, h] trong khoảng 0..1")
        return v


class StationSettings(BaseModel):
    still_seconds: float = Field(ge=0.2, le=10)
    motion_sensitivity: float = Field(ge=0, le=1)
    buzzer_volume: float = Field(ge=0, le=1)
    dry_run: bool


class StationConfig(BaseModel):
    zones: list[Zone]
    settings: StationSettings

    @field_validator("zones")
    @classmethod
    def _unique(cls, v: list[Zone]) -> list[Zone]:
        if len({z.zone_no for z in v}) != len(v):
            raise ValueError("zone_no không được trùng")
        return v


class Feedback(BaseModel):
    verdict: Literal["DUNG", "NHAM"]
    note: str | None = None


class Handling(BaseModel):
    handling: Literal["CHUA_XU_LY", "DA_LAY_RA", "CHO_XEM_LAI"]


class SimulateRequest(BaseModel):
    n: int = Field(default=12, ge=1, le=200)
    seed: int | None = None
