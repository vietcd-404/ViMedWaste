import numpy as np
import pandas as pd
from PIL import Image

from vimedwaste.data.anonymize import anonymize_batch
from vimedwaste.data.dedup import compute_hashes, near_duplicate_pairs


def _photo(path, seed, with_exif=True):
    rng = np.random.default_rng(seed)
    arr = (rng.random((64, 96, 3)) * 255).astype("uint8")
    im = Image.fromarray(arr)
    exif = Image.Exif()
    if with_exif:
        exif[0x010F] = "PhoneMaker"          # Make
        exif[0x0110] = "PhoneModel"          # Model
    im.save(path, format="JPEG", exif=exif.tobytes())


def test_anonymize_strips_exif_and_renames(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    _photo(raw / "IMG_0001.jpg", 0)
    _photo(raw / "IMG_0002.jpg", 1)
    _photo(raw / "IMG_0003.jpg", 2)
    meta = anonymize_batch(raw, tmp_path / "anon", tmp_path / "mapping.csv", tmp_path / "metadata.csv",
                           site="S01", date="2026-11-20", bin_type="B2", lighting="normal",
                           exclude={"IMG_0003.jpg"})
    assert len(meta) == 2
    for f in (tmp_path / "anon").iterdir():
        assert "IMG" not in f.name
        with Image.open(f) as im:
            assert len(im.getexif()) == 0
    mapping = pd.read_csv(tmp_path / "mapping.csv")
    assert set(mapping.original_name) == {"IMG_0001.jpg", "IMG_0002.jpg"}


def test_dedup_finds_copy(tmp_path):
    _photo(tmp_path / "a.jpg", 0)
    Image.open(tmp_path / "a.jpg").resize((80, 54)).save(tmp_path / "a_small.jpg")
    _photo(tmp_path / "b.jpg", 5)
    meta = pd.DataFrame({"image_id": ["a", "a2", "b"], "file_path": ["a.jpg", "a_small.jpg", "b.jpg"]})
    pairs = near_duplicate_pairs(compute_hashes(meta, tmp_path), max_distance=6)
    assert {tuple(sorted(p)) for p in pairs[["image_id_a", "image_id_b"]].values} == {("a", "a2")}
