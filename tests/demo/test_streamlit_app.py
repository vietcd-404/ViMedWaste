from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[2] / "demo" / "streamlit_app.py")
PAGES = ["Kiểm tra thùng", "Dữ liệu", "Mô hình", "Tập nhãn & quy tắc"]


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders(page):
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception
    at.sidebar.radio(key="page").set_value(page).run()
    assert not at.exception, at.exception


def test_model_mode_with_tiny_onnx(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    pytest.importorskip("onnxruntime")
    import vimedwaste.serving.inference as inf

    net = torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1), torch.nn.Flatten(), torch.nn.Linear(3, 10))
    path = tmp_path / "tiny.onnx"
    torch.onnx.export(net, torch.zeros(1, 3, 224, 224), str(path), input_names=["image"],
                      output_names=["logits"], opset_version=17, dynamo=False)
    monkeypatch.setattr(inf, "MODEL_PATH", path)
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert not any("Chế độ minh họa" in m.value for m in at.markdown)


def test_check_page_changes_with_bin():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.sidebar.radio(key="bin").set_value("B2").run()
    assert not at.exception
    at.sidebar.radio(key="bin").set_value("B4").run()
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "CẢNH BÁO" in html or "PHÙ HỢP" in html or "KHÔNG XÁC ĐỊNH" in html
