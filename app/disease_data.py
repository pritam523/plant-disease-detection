"""Helpers around the project's existing class names and disease library."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import settings


@lru_cache(maxsize=1)
def class_names() -> list[str]:
    with open(settings.CLASS_NAMES_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def disease_library() -> dict[str, dict[str, Any]]:
    path: Path = settings.DISEASES_PATH
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    entries = data.get("diseases", data) if isinstance(data, dict) else data
    return {entry["className"]: entry for entry in entries if "className" in entry}


def parse_class_name(class_name: str) -> tuple[str, str, bool]:
    """Return (plant, disease, is_healthy) from a class-name like `Apple___healthy`."""
    info = disease_library().get(class_name, {})
    plant = info.get("plant") or class_name.split("___")[0].replace("_", " ").strip()
    disease = info.get("disease") or (
        class_name.split("___", 1)[1].replace("_", " ").strip()
        if "___" in class_name
        else "Unknown"
    )
    return plant, disease, disease.lower() == "healthy"


def get_disease_info(class_name: str | None) -> dict[str, Any]:
    if not class_name:
        return {}
    return dict(disease_library().get(class_name, {}))


def public_classes() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, name in enumerate(class_names()):
        info = disease_library().get(name, {})
        plant, disease, healthy = parse_class_name(name)
        result.append(
            {
                "index": index,
                "className": name,
                "plant": plant,
                "disease": disease,
                "isHealthy": healthy,
                "severity": info.get("severity", "Unknown"),
                "symptoms": info.get("symptoms", []),
                "prevention": info.get("prevention", []),
                "recommendedActions": info.get("recommendedActions", []),
            }
        )
    return result
