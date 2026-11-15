"""Loads the trained CNN and classifies waste images.

TensorFlow is imported lazily so the web app (and tests) can run before a model exists.
"""
import json
import os
import threading

import cv2
import numpy as np

RECOMMENDATIONS = {
    "plastic": "Rinse the item and place it in the plastic compartment. Remove caps and "
    "labels where possible. Avoid mixing with food-soiled plastic.",
    "paper": "Keep paper dry and clean. Flatten boxes and place them in the paper "
    "compartment. Greasy or wet paper should go to organic waste.",
    "metal": "Empty and rinse cans or tins, then place them in the metal compartment. "
    "Sharp metal should be wrapped safely.",
    "glass": "Empty and rinse the container and place it in the glass compartment. "
    "Handle broken glass carefully and wrap it first.",
    "organic": "Place food scraps and plant waste in the organic compartment. It can be "
    "composted. Do not mix with plastic or packaging.",
}


class ModelNotAvailable(Exception):
    """Raised when no trained model file exists yet."""


class InvalidImage(Exception):
    """Raised when the uploaded file cannot be decoded as an image."""


_lock = threading.Lock()
_cache = {"path": None, "mtime": None, "model": None, "classes": None}


def _load(model_path, class_names_path):
    if not (os.path.exists(model_path) and os.path.exists(class_names_path)):
        raise ModelNotAvailable(
            "The AI model has not been trained yet. Run the scripts in the ml/ folder "
            "(see README) to create ml/model/waste_cnn.keras."
        )
    mtime = os.path.getmtime(model_path)
    with _lock:
        if _cache["path"] == model_path and _cache["mtime"] == mtime:
            return _cache["model"], _cache["classes"]
        from tensorflow import keras  # lazy import

        model = keras.models.load_model(model_path)
        with open(class_names_path, encoding="utf-8") as f:
            classes = json.load(f)
        _cache.update(path=model_path, mtime=mtime, model=model, classes=classes)
        return model, classes


def preprocess_image(path, size):
    """Read an image with OpenCV and return a (1, size, size, 3) float32 RGB array.

    Pixel values stay in 0-255; the model contains its own Rescaling layer.
    """
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise InvalidImage("The uploaded file is not a readable image.")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    return np.expand_dims(img.astype("float32"), axis=0)


def classify(path, config):
    """Return (category, confidence_percent). Raises ModelNotAvailable / InvalidImage."""
    batch = preprocess_image(path, config["IMAGE_SIZE"])
    model, classes = _load(config["MODEL_PATH"], config["CLASS_NAMES_PATH"])
    probs = model.predict(batch, verbose=0)[0]
    idx = int(np.argmax(probs))
    return classes[idx], round(float(probs[idx]) * 100, 2)
