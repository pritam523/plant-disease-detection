"""End-to-end detection pipeline.

The trained local model is always tried first. If it cannot make a dependable
match, Pl@ntNet and Gemini are used together as the primary source of the
answer. Their contribution is always labelled in the API response and UI.
"""
from __future__ import annotations

import asyncio
import io
import uuid
from datetime import datetime, timezone
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from .. import db, disease_data
from ..config import settings
from . import image_guard, model_service, plantnet_service, weather_service
from .gemini_service import gemini_service


class ModelUnavailable(Exception):
    pass


def save_upload(image_bytes: bytes, original_filename: str, image: Image.Image | None = None) -> str:
    """Store a normalised JPEG locally and return a path relative to DATA_DIR."""
    try:
        if image is None:
            with Image.open(io.BytesIO(image_bytes)) as raw:
                image = ImageOps.exif_transpose(raw).convert("RGB")
        image = image.copy()
        image.thumbnail(
            (settings.IMAGE_MAX_STORAGE_PX, settings.IMAGE_MAX_STORAGE_PX),
            Image.Resampling.LANCZOS,
        )
        now = datetime.now(timezone.utc)
        directory = settings.UPLOAD_DIR / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.jpg"
        image.convert("RGB").save(directory / filename, format="JPEG", quality=88, optimize=True)
        return str((directory / filename).relative_to(settings.DATA_DIR)).replace("\\", "/")
    except (UnidentifiedImageError, OSError, ValueError):
        return ""


def _supported_plants() -> list[str]:
    return sorted({name.split("___")[0].replace("_", " ").strip() for name in disease_data.class_names()})


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _local_prediction(image: Image.Image | None) -> dict[str, Any]:
    if image is None or not model_service.is_loaded():
        reason = (
            "The image could not be decoded for local inference."
            if image is None
            else "The trained model is not loaded."
        )
        return {
            "status": "unavailable",
            "predictedClass": None,
            "confidence": None,
            "margin": None,
            "topPredictions": [],
            "notes": [reason],
        }
    return model_service.predict(image)


def _safe_plantnet(image_bytes: bytes) -> dict[str, Any]:
    try:
        return plantnet_service.identify(image_bytes)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return {"available": False, "reason": f"Pl@ntNet unavailable: {str(exc)[:120]}", "candidates": []}


def _safe_gemini(
    image_bytes: bytes,
    context: dict[str, Any],
    primary: bool,
) -> dict[str, Any]:
    try:
        return gemini_service.analyze(image_bytes, context, primary=primary)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return {
            "available": False,
            "primary": primary,
            "reason": f"Gemini request failed: {str(exc)[:180]}",
            "explanation": {},
            "sources": [],
        }


async def detect(
    image_bytes: bytes,
    original_filename: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    image, quality = image_guard.inspect(image_bytes)
    image_path = save_upload(image_bytes, original_filename, image)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    notes: list[str] = list(quality.get("warnings") or [])

    prediction = _local_prediction(image)
    local_reliable = prediction["status"] == "success" and bool(quality.get("accepted"))
    local_view = {
        "status": prediction["status"],
        "predictedClass": prediction.get("predictedClass"),
        "confidence": prediction.get("confidence"),
        "margin": prediction.get("margin"),
        "topPredictions": prediction.get("topPredictions") or [],
        "notes": list(prediction.get("notes") or []),
        "reliable": local_reliable,
    }
    notes.extend(local_view["notes"])

    plant, disease, healthy = "", "", False
    local_info: dict[str, Any] = {}
    confidence_source = "Local model"
    final_confidence = prediction.get("confidence")
    final_status = prediction["status"]
    source = "local_model"

    if local_reliable:
        plant, disease, healthy = disease_data.parse_class_name(prediction["predictedClass"] or "")
        local_info = disease_data.get_disease_info(prediction["predictedClass"])
    else:
        notes.append("The local dataset model did not find a reliable match for this image.")

    weather: dict[str, Any] = {"available": False}
    if latitude is not None and longitude is not None:
        weather = await asyncio.to_thread(weather_service.get_weather, latitude, longitude)

    # Extended identification is used only when the trained model is not
    # dependable; the local prediction is still retained for the record.
    use_external_primary = settings.AI_FALLBACK_ENABLED and not local_reliable
    plantnet: dict[str, Any] = {
        "available": False,
        "reason": "Not needed for a confident local match.",
        "candidates": [],
    }
    if use_external_primary and settings.PLANTNET_ENABLED:
        plantnet = await asyncio.to_thread(_safe_plantnet, image_bytes)
        if plantnet.get("available"):
            species = plantnet.get("commonName") or plantnet.get("species") or "unknown species"
            notes.append(
                f"Pl@ntNet cross-check: {species} ({plantnet.get('species', 'species not reported')}), "
                f"score {_percent(plantnet.get('confidence'))}."
            )
        else:
            notes.append(f"Pl@ntNet could not check this image: {plantnet.get('reason', 'unavailable')}")

    context: dict[str, Any] = {
        "supportedPlants": _supported_plants(),
        "localModel": local_view,
        "modelPrediction": prediction,
        "imageQuality": quality,
        "plantnet": plantnet,
        "weather": weather if weather.get("available") else None,
        "fallbackReason": (
            "The local classifier could not reliably match this image to the 38 trained classes."
            if use_external_primary
            else "The local classifier made a reliable match; Gemini is supporting only."
        ),
    }
    gemini_result = await asyncio.to_thread(_safe_gemini, image_bytes, context, use_external_primary)
    explanation = gemini_result.get("explanation") or {}

    if local_reliable:
        # A confident local result stays primary. Gemini notes are shown but do
        # not silently replace the trained model's label.
        if explanation.get("isLeaf") is False:
            notes.append("Gemini could not confirm that this is a plant leaf; review the result.")
        elif explanation.get("supportedPlant") is False:
            notes.append("Gemini suggests the plant may be outside the trained classes; review the result.")
    elif use_external_primary and gemini_result.get("available"):
        source = "ai_assisted"
        if explanation.get("isLeaf") is False:
            final_status = "rejected"
            notes.append("Gemini could not identify a plant leaf in this image.")
        elif explanation.get("condition") or explanation.get("assessment"):
            final_status = "success"
            plant = str(explanation.get("plant") or plantnet.get("commonName") or plantnet.get("species") or "")
            disease = str(explanation.get("condition") or "Condition not specified")
            healthy_value = explanation.get("healthy")
            healthy = bool(healthy_value) if isinstance(healthy_value, bool) else disease.lower() == "healthy"
            final_confidence = explanation.get("confidence")
            if final_confidence is None:
                final_confidence = plantnet.get("confidence") if plantnet.get("available") else None
            confidence_source = "Gemini visual assessment"
            if explanation.get("uncertainty"):
                notes.append(str(explanation["uncertainty"]))
        else:
            final_status = "unsupported" if plantnet.get("available") else "uncertain"
            plant = str(plantnet.get("commonName") or plantnet.get("species") or "")
            disease = "Species identified; condition needs visual review" if plant else ""
            confidence_source = "Pl@ntNet species score" if plantnet.get("available") else "Local model"
            final_confidence = plantnet.get("confidence") if plantnet.get("available") else final_confidence
    elif use_external_primary:
        notes.append("Gemini could not provide an AI-assisted diagnosis.")
        if plantnet.get("available"):
            final_status = "unsupported"
            plant = str(plantnet.get("commonName") or plantnet.get("species") or "")
            disease = "Species identified; condition needs visual review" if plant else ""
            confidence_source = "Pl@ntNet species score"
            final_confidence = plantnet.get("confidence")

    messages = {
        "success": (
            "AI-assisted identification complete. No reliable trained-dataset match was used."
            if source == "ai_assisted"
            else "Analysis complete."
        ),
        "uncertain": "The classifier and AI services could not provide a reliable identification.",
        "unsupported": "The plant or condition appears to be outside the trained dataset.",
        "rejected": "This image could not be analysed as a plant photo.",
    }
    message = messages.get(final_status, "Analysis complete.")

    record: dict[str, Any] = {
        "created_at": created_at,
        "status": final_status,
        "source": source,
        "message": message,
        "predicted_class": prediction.get("predictedClass") if local_reliable else (disease or None),
        "plant": plant,
        "disease": disease,
        "confidence": final_confidence,
        "confidence_source": confidence_source,
        "margin": prediction.get("margin") if local_reliable else None,
        "top_predictions": prediction.get("topPredictions") or [],
        "is_healthy": healthy,
        "image_path": image_path,
        "original_filename": original_filename or "upload",
        "quality": quality,
        "ai_explanation": explanation if gemini_result.get("available") else {},
        "sources": gemini_result.get("sources") or [] if gemini_result.get("available") else [],
        "weather": weather,
        "plantnet": plantnet,
        "local_prediction": local_view,
        "notes": "\n".join([note for note in notes if note]),
    }

    response: dict[str, Any] = {
        "id": "",
        "createdAt": created_at,
        "status": final_status,
        "source": source,
        "message": message,
        "imageUrl": "/media/" + image_path if image_path else "",
        "quality": quality,
        "notes": [note for note in notes if note],
        "plant": plant,
        "disease": disease,
        "isHealthy": healthy,
        "confidence": final_confidence,
        "confidenceSource": confidence_source,
        "margin": prediction.get("margin") if local_reliable else None,
        "topPredictions": prediction.get("topPredictions") or [],
        "localPrediction": local_view,
        "localInfo": local_info,
        "ai": gemini_result,
        "weather": weather,
        "plantnet": plantnet,
    }

    # Persist the full technical record, then return the same shape to the UI.
    # The frontend decides which fields are appropriate to display.
    response["id"] = db.insert_prediction(record)
    return response
