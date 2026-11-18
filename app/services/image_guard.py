"""Lightweight image sanity checks before model inference.

These guards only reject images that are clearly not usable (blank, tiny, or
very unlikely to contain a leaf). They are deliberately conservative so real
photographs of diseased leaves are not discarded.
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import settings


def _plant_likeness(image: Image.Image) -> tuple[float, float]:
    small = ImageOps.exif_transpose(image).convert("RGB").resize((64, 64))
    arr = np.asarray(small, dtype=np.float32) / 255.0
    maximum = arr.max(axis=2)
    minimum = arr.min(axis=2)
    saturation = np.where(maximum > 1e-6, (maximum - minimum) / np.maximum(maximum, 1e-6), 0.0)

    red, green, blue = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    greenish = (green >= red * 1.02) & (green >= blue * 1.02) & (saturation > 0.12)
    yellowish = (red > blue * 1.12) & (green > blue * 1.12) & (saturation > 0.12)
    plant_ratio = float(np.mean(greenish | yellowish))

    gray = red * 0.299 + green * 0.587 + blue * 0.114
    laplacian = (
        -4 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
    )
    # Rescale to the 0-255 pixel range so thresholds are intuitive.
    sharpness = float(laplacian.var()) * (255 ** 2)
    return plant_ratio, sharpness


def inspect(image_bytes: bytes) -> tuple[Image.Image | None, dict[str, Any]]:
    """Return a normalised RGB image plus quality information."""
    info: dict[str, Any] = {"accepted": True, "warnings": [], "reason": ""}
    if len(image_bytes) > settings.IMAGE_MAX_BYTES:
        return None, {
            "accepted": False,
            "warnings": [],
            "reason": f"Image is too large (max {settings.IMAGE_MAX_BYTES // (1024 * 1024)} MB).",
        }

    try:
        with Image.open(io.BytesIO(image_bytes)) as raw:
            raw.load()
            image = ImageOps.exif_transpose(raw).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        return None, {"accepted": False, "warnings": [], "reason": "The file is not a valid image."}

    width, height = image.size
    info["width"] = width
    info["height"] = height
    if min(width, height) < settings.IMAGE_MIN_SIDE:
        return None, {
            "accepted": False,
            "warnings": [],
            "reason": f"Image is too small (minimum {settings.IMAGE_MIN_SIDE}px per side).",
        }

    if settings.IMAGE_GUARD_ENABLED:
        plant_ratio, sharpness = _plant_likeness(image)
        info["plant_ratio"] = round(plant_ratio, 4)
        info["sharpness"] = round(sharpness, 2)

        if plant_ratio < 0.03 and sharpness < 60:
            info["accepted"] = False
            info["reason"] = "This does not look like a plant leaf photo. Upload a clear leaf image."
            return image, info
        if sharpness < 45:
            info["warnings"].append("The image looks very blurry; results may be unreliable.")
        if plant_ratio < 0.08:
            info["warnings"].append("Low plant-like colour content; check that the leaf fills the frame.")

    return image, info
