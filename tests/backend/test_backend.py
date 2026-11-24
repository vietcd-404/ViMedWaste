import io

import pandas as pd
import pytest
from PIL import Image

from vimedwaste.serving import inference

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from backend.settings import MW40_DIR, ROOT  # noqa: E402

HAS_MODEL = inference.MODEL_PATH.exists()
needs_model = pytest.mark.skipif(not HAS_MODEL, reason="chưa có artifacts/models/vimedwaste.onnx")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIMEDWASTE_DB", str(tmp_path / "test.db"))
    from backend.main import app
    with TestClient(app) as c:
        yield c


def _image_bytes(source_class: str = "glove_pair_nitrile") -> bytes:
    meta = pd.read_csv(MW40_DIR / "metadata.csv")
    path = ROOT / meta[meta.source_class == source_class].iloc[0].file_path
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, format="JPEG")
    return buf.getvalue()


def test_health_labels_stations(client):
    assert client.get("/api/health").json()["status"] == "ok"
    body = client.get("/api/labels").json()
    assert [l["code"] for l in body["labels"]] == [f"L{i:02d}" for i in range(1, 11)]
    assert body["compatibility"]["L03"] == ["B1", "B2"]
    assert body["labels"][4]["name"] == "Dây truyền, ống dẫn, túi dịch"   # tên có dấu phẩy không bị cắt
    assert len(body["bins"]) == 5
    stations = client.get("/api/stations").json()
    assert [s["id"] for s in stations] == ["tram-01", "tram-02", "tram-03"]
    assert len(stations[0]["zones"]) == 4 and stations[0]["online"] is False


def test_put_config_and_validation(client):
    cfg = {"zones": [{"zone_no": 1, "bin_type": "B3", "box": [0.1, 0.1, 0.3, 0.5]}],
           "settings": {"still_seconds": 1.5, "motion_sensitivity": 0.4, "buzzer_volume": 0.2, "dry_run": True}}
    st = client.put("/api/stations/tram-01/config", json=cfg).json()
    assert st["zones"][0]["bin_type"] == "B3" and st["settings"]["dry_run"] is True
    bad = {**cfg, "zones": [{"zone_no": 1, "bin_type": "B9", "box": [0, 0, 1, 1]}]}
    assert client.put("/api/stations/tram-01/config", json=bad).status_code == 422
    assert client.get("/api/stations/khong-co").status_code == 404
    assert client.get("/api/stations/tram-01/snapshot").headers["content-type"] == "image/jpeg"
    assert client.post("/api/stations/tram-01/heartbeat").json()["online"] is True


@needs_model
def test_predict_real_image(client):
    r = client.post("/api/predict", files={"image": ("a.jpg", _image_bytes(), "image/jpeg")},
                    data={"bin_type": "B4"})
    d = r.json()
    assert r.status_code == 200
    assert d["status"] == "CANH_BAO" and d["violations"][0] == "L04"
    assert d["title"] == "Găng tay trong thùng xanh"
    assert len(d["labels"]) == 10 and d["model"]["available"] is True
    assert d["gradcam"] is None or d["gradcam"].startswith("data:image/png;base64,")


@needs_model
def test_capture_feedback_handling_stats(client):
    img = _image_bytes()
    ev1 = client.post("/api/stations/tram-01/capture", data={"zone_no": 3},
                      files={"image": ("a.jpg", img, "image/jpeg")}).json()
    assert ev1["bin_type"] == "B4" and ev1["status"] == "CANH_BAO"
    assert ev1["handling"] == "CHUA_XU_LY" and ev1["images"]["before"] is None
    assert client.get(ev1["images"]["after"]).status_code == 200
    # Lần chụp thứ hai cùng vùng: ảnh trước = ảnh sau của lần trước.
    ev2 = client.post("/api/stations/tram-01/capture", data={"zone_no": 3},
                      files={"image": ("b.jpg", _image_bytes("gauze"), "image/jpeg")}).json()
    assert ev2["images"]["before"] is not None
    assert client.get(ev2["images"]["before"]).status_code == 200

    fb = client.post(f"/api/events/{ev1['id']}/feedback", json={"verdict": "NHAM"}).json()
    assert fb["feedback"] == "NHAM" and "hàng chờ" in fb["timeline"][-1]["text"]
    from backend.services import events as event_service
    assert [q["event_id"] for q in event_service.relabel_queue()] == [ev1["id"]]
    h = client.post(f"/api/events/{ev1['id']}/handling", json={"handling": "DA_LAY_RA"}).json()
    assert h["handling"] == "DA_LAY_RA"

    events = client.get("/api/events").json()
    assert [e["id"] for e in events][:2] == [ev2["id"], ev1["id"]]
    stats = client.get("/api/stats/overview").json()
    assert stats["total"] == 2 and stats["warnings"] >= 1 and stats["simulated"] is False
    assert stats["top_mislabels"][0]["code"] in {"L03", "L04"}


@needs_model
def test_simulate(client):
    r = client.post("/api/simulate", json={"n": 3, "seed": 1}).json()
    assert r["created"] == 3
    events = client.get("/api/events").json()
    assert len(events) == 3 and all(e["simulated"] for e in events)
    assert client.get("/api/stats/overview").json()["simulated"] is True


def test_no_model_returns_503(client, monkeypatch, tmp_path):
    monkeypatch.setattr(inference, "MODEL_PATH", tmp_path / "khong-co.onnx")
    r = client.post("/api/predict", files={"image": ("a.png", _png(), "image/png")}, data={"bin_type": "B2"})
    assert r.status_code == 503
    assert client.get("/api/health").json()["model_available"] is False


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (128, 128, 128)).save(buf, format="PNG")
    return buf.getvalue()


def test_training_report(client):
    r = client.get("/api/training").json()
    if not r["available"]:
        pytest.skip("chưa có artifacts/results/train_mw40.json")
    assert {"data", "baselines_val", "main_model", "onnx", "thresholds_bayes"} <= set(r)
    assert r["data"]["n_train"] > 0 and 0 <= r["main_model"]["open_set"]["auroc_val_vs_ood_near"] <= 1
