"""Khóa toàn bộ app bằng một mật khẩu (HTTP Basic) khi đặt VIMEDWASTE_PASSWORD.

Đủ cho bản demo công khai: trình duyệt tự hiện hộp đăng nhập và nhớ cho cả giao diện lẫn API;
thiết bị Pi gửi cùng header. Chưa phải phân quyền theo người dùng.
"""
from __future__ import annotations

import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

OPEN_PATHS = {"/api/health"}          # để nền tảng hosting kiểm tra sống/chết


class PasswordMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, password: str):
        super().__init__(app)
        self.password = password.encode()

    def _ok(self, header: str | None) -> bool:
        if not header or not header.lower().startswith("basic "):
            return False
        try:
            _, _, pw = base64.b64decode(header[6:]).partition(b":")
        except ValueError:
            return False
        return secrets.compare_digest(pw, self.password)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in OPEN_PATHS or request.method == "OPTIONS" or self._ok(request.headers.get("authorization")):
            return await call_next(request)
        return Response("Cần đăng nhập", status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="ViMedWaste", charset="UTF-8"'})
