import math

import numpy as np
import pandas as pd

from vimedwaste.core.config import load_config
from vimedwaste.data.agreement import cohen_kappa, kappa_per_label, resolve


def test_kappa_perfect_and_chance():
    a = np.array([1, 0, 1, 0, 1, 0])
    assert cohen_kappa(a, a) == 1.0
    assert cohen_kappa(a, 1 - a) == -1.0
    assert math.isnan(cohen_kappa(np.zeros(5), np.zeros(5)))


def test_kappa_known_value():
    # po = 0.8, pa = pb = 0.5 → pe = 0.5 → κ = 0.6
    a = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    b = np.array([1, 1, 1, 1, 0, 1, 0, 0, 0, 0])
    assert abs(cohen_kappa(a, b) - 0.6) < 1e-9


def _ann(rows):
    labels = load_config().labels
    out = []
    for image_id, annotator, present, bad in rows:
        r = {"image_id": image_id, "annotator_id": annotator, "batch_id": "b1", "quality_flag": bad}
        r.update({k: int(k in present) for k in labels})
        out.append(r)
    return pd.DataFrame(out)


def test_resolve_agree_and_disagree():
    labels = load_config().labels
    ann = _ann([
        ("a", "dat", {"L01"}, 0), ("a", "lam", {"L01"}, 0),
        ("b", "dat", {"L03"}, 0), ("b", "lam", {"L04"}, 0),
    ])
    final, dis = resolve(ann, labels)
    assert final.image_id.tolist() == ["a"]
    assert final.loc[0, "L01"] == 1 and bool(final.loc[0, "quality_ok"])
    assert set(dis.image_id) == {"b"}

    adj = _ann([("b", "viet", {"L03", "L04"}, 0)])
    final, dis = resolve(ann, labels, adj)
    assert set(final.image_id) == {"a", "b"} and dis.empty
    assert bool(final.set_index("image_id").loc["b", "adjudicated"])


def test_kappa_table_has_every_label():
    labels = load_config().labels
    ann = _ann([("a", "dat", {"L01"}, 0), ("a", "lam", {"L01"}, 0),
                ("b", "dat", set(), 0), ("b", "lam", set(), 0)])
    table = kappa_per_label(ann, labels)
    assert table.label.tolist() == labels
    assert table.set_index("label").loc["L01", "kappa"] == 1.0
