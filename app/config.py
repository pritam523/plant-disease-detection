"""Central configuration loaded from environment variables / .env."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    """Runtime settings. All secrets stay on the server side."""

    APP_NAME = "Plant Disease Detection"
    APP_VERSION = "1.0.0"
    HOST = os.getenv("APP_HOST", "127.0.0.1")
    PORT = _int("APP_PORT", 8000)

    # Local files (existing project resources are reused, never replaced)
    MODEL_PATH = Path(os.getenv("MODEL_PATH", str(BASE_DIR / "model" / "trained_model.keras")))
    if not MODEL_PATH.exists():
        MODEL_PATH = BASE_DIR / "trained_model.keras"
    CLASS_NAMES_PATH = Path(
        os.getenv("CLASS_NAMES_PATH", str(BASE_DIR / "disease_data" / "class_names.json"))
    )
    DISEASES_PATH = Path(os.getenv("DISEASES_PATH", str(BASE_DIR / "disease_data" / "diseases.json")))

    DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    UPLOAD_DIR = DATA_DIR / "uploads"
    DB_PATH = DATA_DIR / "plant_disease.db"

    # Classifier behaviour
    CONFIDENCE_THRESHOLD = _float("PREDICTION_CONFIDENCE_THRESHOLD", 0.50)
    MARGIN_THRESHOLD = _float("PREDICTION_MARGIN_THRESHOLD", 0.10)
    TTA_ENABLED = _bool("TTA_ENABLED", True)
    TTA_VIEWS = max(1, min(6, _int("TTA_VIEWS", 4)))

    # Image validation / guardrails
    IMAGE_GUARD_ENABLED = _bool("IMAGE_GUARD_ENABLED", True)
    IMAGE_MAX_BYTES = _int("IMAGE_MAX_BYTES", 12 * 1024 * 1024)
    IMAGE_MIN_SIDE = _int("IMAGE_MIN_SIDE", 96)
    IMAGE_MAX_STORAGE_PX = _int("IMAGE_MAX_STORAGE_PX", 1600)

    # Gemini (free tier friendly; model id is configurable for future models)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    GEMINI_GROUNDING_ENABLED = _bool("GEMINI_GROUNDING_ENABLED", False)
    GEMINI_TIMEOUT = _float("GEMINI_TIMEOUT", 20.0)
    GEMINI_MAX_IMAGE_PX = _int("GEMINI_MAX_IMAGE_PX", 768)
    GEMINI_CACHE_SIZE = _int("GEMINI_CACHE_SIZE", 100)

    # Optional supporting services
    OPEN_METEO_ENABLED = _bool("OPEN_METEO_ENABLED", True)
    PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY", "").strip()
    PLANTNET_ENABLED = _bool("PLANTNET_ENABLED", bool(PLANTNET_API_KEY))
    EXTERNAL_TIMEOUT = _float("EXTERNAL_TIMEOUT", 10.0)

    # When the local trained model is not reliable, Gemini and Pl@ntNet may
    # become the primary source of the answer. The local model is still tried
    # first and its candidates remain visible to the user.
    AI_FALLBACK_ENABLED = _bool("AI_FALLBACK_ENABLED", True)

    # Admin authentication (no public user accounts)
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
    ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "").strip() or secrets.token_hex(32)
    ADMIN_SESSION_MAX_AGE = _int("ADMIN_SESSION_MAX_AGE", 8 * 3600)
    ADMIN_MAX_ATTEMPTS = _int("ADMIN_MAX_ATTEMPTS", 5)
    ADMIN_LOCK_SECONDS = _int("ADMIN_LOCK_SECONDS", 15 * 60)


settings = Settings()
