"""Image upload and detection endpoint."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import settings
from ..services.detection_service import ModelUnavailable, detect

router = APIRouter(prefix="/api", tags=["detection"])


@router.post("/detect")
async def detect_image(
    image: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
) -> dict:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file (JPG, PNG or WEBP).")

    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > settings.IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds the {settings.IMAGE_MAX_BYTES // (1024 * 1024)} MB limit.",
        )

    try:
        return await detect(contents, image.filename or "upload", latitude, longitude)
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(exc)[:180]}") from exc
