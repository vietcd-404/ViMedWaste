import numpy as np

from vimedwaste.training.train_mw40 import fit_temperature, joint_energy, metrics


def test_joint_energy_higher_for_confident_logits():
    s = joint_energy(np.array([[5.0, -5.0], [-5.0, -5.0]]))
    assert s[0] > s[1]


def test_fit_temperature_recovers_scale():
    rng = np.random.default_rng(0)
    true_logit = rng.normal(0, 2, size=(2000, 3))
    y = (rng.random((2000, 3)) < 1 / (1 + np.exp(-true_logit))).astype(int)
    t = fit_temperature(true_logit * 3.0, y)       # logit bị phóng đại 3 lần
    assert 2.0 < t < 4.0


def test_metrics_perfect():
    y = np.eye(3, dtype=int)
    m = metrics(y, y.astype(float), y)
    assert m["mAP"] == 1.0 and m["exact_match"] == 1.0
