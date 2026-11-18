"""Protected admin panel API (no public registration)."""
from __future__ import annotations

import platform
import sys
import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from .. import db
from ..config import settings
from ..security import LoginLimiter, create_session, read_session, verify_password
from ..services import model_service, plantnet_service
from ..services.gemini_service import gemini_service

router = APIRouter(prefix="/api/admin", tags=["admin"])
COOKIE_NAME = "pdd_admin_session"
limiter = LoginLimiter(settings.ADMIN_MAX_ATTEMPTS, settings.ADMIN_LOCK_SECONDS)
STARTED_AT = time.time()


class LoginRequest(BaseModel):
    password: str


def _authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME, "")
    payload = read_session(settings.ADMIN_SECRET_KEY, token) if token else None
    return bool(payload and payload.get("role") == "admin")


def _require(request: Request) -> None:
    if not _authenticated(request):
        raise HTTPException(status_code=401, detail="Admin authentication required")


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    client_key = request.client.host if request.client else "unknown"
    if limiter.is_locked(client_key):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=503,
            detail="Admin password is not configured. Set ADMIN_PASSWORD_HASH in .env.",
        )
    if not verify_password(payload.password, settings.ADMIN_PASSWORD_HASH):
        limiter.record_failure(client_key)
        raise HTTPException(status_code=401, detail="Incorrect password")
    limiter.reset(client_key)
    token = create_session(
        settings.ADMIN_SECRET_KEY, {"role": "admin"}, settings.ADMIN_SESSION_MAX_AGE
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.ADMIN_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return {"authenticated": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"authenticated": False}


@router.get("/status")
def status(request: Request) -> dict:
    return {
        "authenticated": _authenticated(request),
        "configPassword": bool(settings.ADMIN_PASSWORD_HASH),
    }


@router.get("/stats")
def dashboard_stats(request: Request) -> dict:
    _require(request)
    return db.stats()


@router.get("/system")
def system_info(request: Request) -> dict:
    _require(request)
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "uptimeSeconds": int(time.time() - STARTED_AT),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "database": str(settings.DB_PATH),
        },
        "model": model_service.info(),
        "gemini": gemini_service.status(),
        "weather": {"enabled": settings.OPEN_METEO_ENABLED, "provider": "Open-Meteo"},
        "plantnet": plantnet_service.status(),
        "config": {
            "confidenceThreshold": settings.CONFIDENCE_THRESHOLD,
            "marginThreshold": settings.MARGIN_THRESHOLD,
            "ttaEnabled": settings.TTA_ENABLED,
            "geminiKeyConfigured": bool(settings.GEMINI_API_KEY),
            "plantnetKeyConfigured": bool(settings.PLANTNET_API_KEY),
            "aiFallbackEnabled": settings.AI_FALLBACK_ENABLED,
        },
    }
