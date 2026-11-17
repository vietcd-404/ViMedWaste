"""Các tùy chọn khi deploy: khóa mật khẩu, phục vụ giao diện tĩnh."""
import base64
import importlib

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _app(monkeypatch, tmp_path, **env):
    monkeypatch.setenv("VIMEDWASTE_DB", str(tmp_path / "t.db"))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import backend.settings
    import backend.main
    importlib.reload(backend.settings)
    return importlib.reload(backend.main).app


def _basic(pw: str) -> dict:
    return {"Authorization": "Basic " + base64.b64encode(f"x:{pw}".encode()).decode()}


def test_password_locks_everything_except_health(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path, VIMEDWASTE_PASSWORD="bimat")
    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 200
        r = c.get("/api/labels")
        assert r.status_code == 401 and "Basic" in r.headers["www-authenticate"]
        assert c.get("/api/labels", headers=_basic("sai")).status_code == 401
        assert c.get("/api/labels", headers=_basic("bimat")).status_code == 200


def test_serves_angular_with_spa_fallback(monkeypatch, tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<app-root></app-root>", encoding="utf-8")
    (static / "main.js").write_text("console.log(1)", encoding="utf-8")
    app = _app(monkeypatch, tmp_path, VIMEDWASTE_STATIC_DIR=str(static), VIMEDWASTE_PASSWORD="")
    with TestClient(app) as c:
        assert "app-root" in c.get("/").text
        assert "app-root" in c.get("/su-kien/3").text          # route phía client
        assert c.get("/main.js").text == "console.log(1)"
        assert c.get("/api/khong-co").status_code == 404
        assert c.get("/api/health").json()["status"] == "ok"
        assert "app-root" in c.get("/../../etc/passwd").text   # không thoát ra ngoài thư mục
