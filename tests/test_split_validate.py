import numpy as np
import pandas as pd

from vimedwaste.config import load_config
from vimedwaste.data.split import build_splits
from vimedwaste.data.validate_metadata import check_metadata, check_splits


def _fake(n_groups=40, per_group=10, seed=0):
    rng = np.random.default_rng(seed)
    labels = load_config().labels
    meta, lab = [], []
    for g in range(n_groups):
        site, date = f"S{g % 4 + 1:02d}", f"2026-11-{g % 28 + 1:02d}"
        for i in range(per_group):
            image_id = f"{g:03d}{i:03d}"
            meta.append({"image_id": image_id, "file_path": f"x/{image_id}.jpg", "site_id": site,
                         "capture_date": date, "bin_type": "B2", "lighting": "normal",
                         "is_simulated": False, "is_ood": False, "source": "vimedwaste"})
            row = {"image_id": image_id, "adjudicated": False, "quality_ok": True}
            row.update({k: int(rng.random() < 0.2) for k in labels})
            lab.append(row)
    meta = pd.DataFrame(meta)
    meta["group_id"] = meta.site_id + "_" + meta.capture_date + "_" + (meta.image_id.str[:3])
    return meta, pd.DataFrame(lab), labels


def test_split_keeps_groups_together_and_ratios():
    meta, lab, labels = _fake()
    cfg = load_config()
    sp = build_splits(meta, lab, labels, cfg.split_ratios, seed=0)
    assert sp.groupby("group_id").split.nunique().max() == 1
    share = sp.split.value_counts(normalize=True)
    for s, r in cfg.split_ratios.items():
        assert abs(share[s] - r) < 0.08
    assert check_splits(sp, meta) == []


def test_external_never_in_test_and_ood_excluded():
    meta, lab, labels = _fake()
    meta.loc[meta.image_id.str.startswith("000"), "source"] = "mw40_v01"
    meta.loc[meta.image_id.str.startswith("001"), "is_ood"] = True
    sp = build_splits(meta, lab, labels, load_config().split_ratios, seed=0)
    merged = sp.merge(meta, on="image_id")
    assert not ((merged.source != "vimedwaste") & (merged.split == "test")).any()
    assert not sp.image_id.str.startswith("001").any()


def test_validate_flags_bad_rows():
    meta, _, _ = _fake(n_groups=2, per_group=2)
    assert check_metadata(meta.drop(columns="group_id")) == []
    bad = meta.copy()
    bad.loc[0, "bin_type"] = "B9"
    bad.loc[1, "image_id"] = bad.loc[0, "image_id"]
    errs = check_metadata(bad)
    assert any("bin_type" in e for e in errs) and any("trùng" in e for e in errs)

    sp = pd.DataFrame({"image_id": meta.image_id[:2], "group_id": ["g", "g"], "split": ["train", "test"]})
    assert any("nhiều tập" in e for e in check_splits(sp, meta))
