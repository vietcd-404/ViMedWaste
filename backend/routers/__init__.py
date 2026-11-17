"""Route HTTP, mỗi file một nhóm endpoint. Chỉ nhận/trả dữ liệu; nghiệp vụ nằm trong services/."""
from __future__ import annotations

from fastapi import HTTPException, UploadFile

from ..services import imaging


async def read_image(upload: UploadFile | None, *, required: bool = False):
    """Đọc file tải lên thành ảnh PIL; ảnh hỏng → 400."""
    data = await upload.read() if upload is not None else b""
    if not data:
        if required:
            raise HTTPException(status_code=400, detail="Thiếu ảnh")
        return None
    try:
        return imaging.open_image(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Không đọc được ảnh: {exc}") from exc
