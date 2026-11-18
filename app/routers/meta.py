"""Health, model information, disease library and optional weather endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from .. import db, disease_data
from ..config import settings
from ..services import model_service, plantnet_service, weather_service
from ..services.gemini_service import gemini_service

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "healthy" if model_service.is_loaded() else "degraded",
        "modelLoaded": model_service.is_loaded(),
        "classCount": len(disease_data.class_names()),
        "geminiConfigured": gemini_service.available,
        "plantnetConfigured": plantnet_service.status()["configured"],
        "aiFallbackEnabled": settings.AI_FALLBACK_ENABLED,
        "version": settings.APP_VERSION,
    }


@router.get("/model/info")
def model_info() -> dict:
    return model_service.info()


@router.get("/stats")
def public_stats() -> dict:
    """Aggregate statistics for the user dashboard (no authentication needed)."""
    return db.stats()


@router.get("/diseases")
def diseases() -> list[dict]:
    return disease_data.public_classes()


@router.get("/diseases/{class_name}")
def disease_detail(class_name: str) -> dict:
    info = disease_data.get_disease_info(class_name)
    if not info:
        raise HTTPException(status_code=404, detail="Disease not found")
    return info


@router.get("/services/status")
def services_status() -> dict:
    return {
        "gemini": gemini_service.status(),
        "weather": {"enabled": settings.OPEN_METEO_ENABLED},
        "plantnet": plantnet_service.status(),
        "aiFallbackEnabled": settings.AI_FALLBACK_ENABLED,
    }


@router.get("/weather")
def weather(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
) -> dict:
    return weather_service.get_weather(latitude, longitude)
