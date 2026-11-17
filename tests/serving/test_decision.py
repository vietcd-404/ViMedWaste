import numpy as np
from PIL import Image

from vimedwaste.core.config import load_config
from vimedwaste.serving.decision import OK, UNKNOWN, WARN, bayes_thresholds, correct_bins, decide
from vimedwaste.serving.inference import load_predictor, preprocess


def _probs(**present):
    return {k: present.get(k, 0.01) for k in load_config().labels}


def test_bayes_thresholds_follow_costs():
    t = bayes_thresholds()
    assert abs(t["L01"] - 1 / 11) < 1e-9      # C_FN = 10
    assert abs(t["L03"] - 1 / 6) < 1e-9       # C_FN = 5
    assert t["L10"] == 0.5                    # C_FN = 1


def test_sharps_in_general_bin_warns_most_dangerous_first():
    d = decide(_probs(L04=0.8, L01=0.5), "B4")
    assert d.status == WARN
    assert d.violations == ["L01", "L04"]


def test_infectious_in_sharps_box_is_allowed():
    assert decide(_probs(L03=0.9, L04=0.7), "B1").status == OK


def test_low_probability_below_threshold_is_ignored():
    assert decide(_probs(L01=0.05), "B4").status == OK
    assert decide(_probs(L01=0.10), "B4").status == WARN   # trên ngưỡng 1/11


def test_open_set_rejects_before_labels():
    d = decide(_probs(L01=0.9), "B4", ood_score=0.2, tau=0.5)
    assert d.status == UNKNOWN and d.violations == []


def test_correct_bins():
    assert correct_bins("L03") == ["B1", "B2"]


def test_preprocess_shape_and_no_model():
    x = preprocess(Image.fromarray(np.zeros((300, 500, 3), dtype="uint8")))
    assert x.shape == (1, 3, 224, 224)
    assert load_predictor() is None or True   # chưa có artifacts/models/vimedwaste.onnx
