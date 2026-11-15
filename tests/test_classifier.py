import glob
import os

import cv2
import numpy as np
import pytest

from app.services import classifier
from config import Config

ROOT = os.path.dirname(os.path.dirname(__file__))


def _write(tmp_path, img, name="x.png"):
    p = str(tmp_path / name)
    cv2.imwrite(p, img)
    return p


def test_preprocess_shape_dtype_and_range(tmp_path):
    img = np.random.randint(0, 255, (73, 211, 3), dtype=np.uint8)  # non-square on purpose
    out = classifier.preprocess_image(_write(tmp_path, img), 128)
    assert out.shape == (1, 128, 128, 3) and out.dtype == np.float32
    assert 0 <= out.min() and out.max() <= 255  # raw pixels; the model normalises internally


def test_preprocess_converts_bgr_to_rgb(tmp_path):
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    img[:, :] = (255, 0, 0)  # BGR blue
    out = classifier.preprocess_image(_write(tmp_path, img), 16)
    assert out[0, 0, 0, 2] == 255 and out[0, 0, 0, 0] == 0  # RGB: blue channel is last


def test_unreadable_file_raises(tmp_path):
    p = tmp_path / "bad.png"
    p.write_bytes(b"this is not an image")
    with pytest.raises(classifier.InvalidImage):
        classifier.preprocess_image(str(p), 128)


def test_missing_model_raises(tmp_path):
    img = np.zeros((20, 20, 3), dtype=np.uint8)
    with pytest.raises(classifier.ModelNotAvailable):
        classifier.classify(_write(tmp_path, img), {"IMAGE_SIZE": 128, "MODEL_PATH": "none.keras", "CLASS_NAMES_PATH": "none.json"})


def test_every_category_has_a_recommendation():
    assert set(classifier.RECOMMENDATIONS) == set(Config.CATEGORIES)


@pytest.mark.skipif(
    not (os.path.exists(Config.MODEL_PATH) and glob.glob(os.path.join(ROOT, "data", "dataset", "test", "*", "*.jpg"))),
    reason="needs the trained model and the prepared dataset",
)
def test_real_model_sanity_on_held_out_images():
    """Smoke test with the real model: a few held-out images per class, loose accuracy floor."""
    cfg = {"IMAGE_SIZE": Config.IMAGE_SIZE, "MODEL_PATH": Config.MODEL_PATH, "CLASS_NAMES_PATH": Config.CLASS_NAMES_PATH}
    hits = total = 0
    for cat in Config.CATEGORIES:
        for path in sorted(glob.glob(os.path.join(ROOT, "data", "dataset", "test", cat, "*.jpg")))[:6]:
            pred, conf = classifier.classify(path, cfg)
            assert pred in Config.CATEGORIES and 0 <= conf <= 100
            hits += pred == cat
            total += 1
    assert hits / total >= 0.6, f"only {hits}/{total} correct"
