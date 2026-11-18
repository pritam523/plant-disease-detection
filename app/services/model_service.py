"""Primary classifier: loads and runs the provided trained Keras model."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from .. import disease_data  # noqa: E402
from ..config import settings  # noqa: E402

_model: Any = None
_class_names: list[str] = []
_load_error: str = ""
INPUT_SIZE = (128, 128)


def load() -> None:
    global _model, _class_names, _load_error
    _class_names = disease_data.class_names()
    try:
        import tensorflow as tf

        if not Path(settings.MODEL_PATH).exists():
            raise FileNotFoundError(f"Model file not found: {settings.MODEL_PATH}")
        _model = tf.keras.models.load_model(str(settings.MODEL_PATH), compile=False)
        outputs = int(np.asarray(_model.output_shape[-1]))
        if outputs != len(_class_names):
            raise ValueError(
                f"Model outputs {outputs} classes but class_names.json has {len(_class_names)}"
            )
        _load_error = ""
    except Exception as exc:  # pragma: no cover - depends on local environment
        _model = None
        _load_error = str(exc)


def unload() -> None:
    global _model
    _model = None


def is_loaded() -> bool:
    return _model is not None


def info() -> dict[str, Any]:
    return {
        "loaded": is_loaded(),
        "modelPath": str(settings.MODEL_PATH),
        "className": Path(settings.MODEL_PATH).name,
        "classCount": len(_class_names),
        "inputSize": list(INPUT_SIZE),
        "ttaEnabled": settings.TTA_ENABLED,
        "ttaViews": settings.TTA_VIEWS if settings.TTA_ENABLED else 1,
        "confidenceThreshold": settings.CONFIDENCE_THRESHOLD,
        "marginThreshold": settings.MARGIN_THRESHOLD,
        "error": _load_error,
    }


def _preprocess(image: Image.Image) -> np.ndarray:
    # Matches the notebook: RGB, resize to 128x128, float values kept in 0..255.
    rgb = image.convert("RGB").resize(INPUT_SIZE, Image.Resampling.BILINEAR)
    return np.asarray(rgb, dtype=np.float32)


def _views(image: Image.Image) -> list[np.ndarray]:
    base = _preprocess(image)
    views = [base, base[:, ::-1, :], base[::-1, :, :]]
    if settings.TTA_VIEWS > 3:
        width, height = image.size
        side = min(width, height) * 0.90
        left, top = (width - side) / 2, (height - side) / 2
        crop = image.crop((int(left), int(top), int(left + side), int(top + side)))
        views.append(_preprocess(crop))
    if settings.TTA_VIEWS > 4:
        width, height = image.size
        side = min(width, height) * 0.80
        left, top = (width - side) / 2, (height - side) / 2
        crop = image.crop((int(left), int(top), int(left + side), int(top + side)))
        views.append(_preprocess(crop))
    if settings.TTA_VIEWS > 5:
        views.append(base * 0.92)
    return views[: settings.TTA_VIEWS]


def predict(image: Image.Image) -> dict[str, Any]:
    if _model is None:
        raise RuntimeError("The trained model is not loaded.")

    views = _views(image) if settings.TTA_ENABLED else [_preprocess(image)]
    batch = np.stack(views, axis=0)
    probabilities = np.asarray(_model.predict(batch, verbose=0), dtype=np.float64)
    probabilities = probabilities.mean(axis=0)
    order = np.argsort(probabilities)[::-1]

    top = [
        {
            "className": _class_names[int(index)],
            "confidence": round(float(probabilities[int(index)]), 6),
        }
        for index in order[:3]
        if 0 <= int(index) < len(_class_names)
    ]

    best_index = int(order[0])
    confidence = float(probabilities[best_index])
    second = float(probabilities[order[1]]) if len(order) > 1 else 0.0
    margin = confidence - second
    predicted_class = _class_names[best_index]

    status = "success"
    notes: list[str] = []
    if confidence < settings.CONFIDENCE_THRESHOLD:
        status = "uncertain"
        notes.append("Confidence is below the configured threshold.")
    if margin < settings.MARGIN_THRESHOLD:
        status = "uncertain"
        notes.append("The top two classes are too close to be reliable.")

    return {
        "status": status,
        "predictedClass": predicted_class,
        "confidence": round(confidence, 6),
        "margin": round(margin, 6),
        "topPredictions": top,
        "notes": notes,
    }
