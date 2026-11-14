from vimedwaste.config import load_config


def test_ten_labels_five_bins():
    cfg = load_config()
    assert cfg.labels == [f"L{i:02d}" for i in range(1, 11)]
    assert cfg.bins == ["B1", "B2", "B3", "B4", "B5"]
    assert cfg.A.shape == (10, 5)


def test_compatibility_matrix():
    cfg = load_config()
    assert cfg.allowed("L01", "B1") and not cfg.allowed("L01", "B2")
    assert cfg.allowed("L03", "B1") and cfg.allowed("L03", "B2")   # lây nhiễm không sắc nhọn được vào B1
    assert cfg.allowed("L10", "B4") and not cfg.allowed("L10", "B5")


def test_violations():
    cfg = load_config()
    assert cfg.violations(["L01", "L04"], "B4") == ["L01", "L04"]
    assert cfg.violations(["L03", "L04"], "B2") == []
