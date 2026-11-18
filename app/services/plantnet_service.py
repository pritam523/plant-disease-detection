"""Optional Pl@ntNet species identification adapter.

Pl@ntNet is used as a supporting species cross-check and, when the local model
is not reliable, as one of the inputs for the external AI-assisted answer.
"""
from __future__ import annotations

from typing import Any

import httpx

from ..config import settings


def status() -> dict[str, Any]:
    return {
        "enabled": settings.PLANTNET_ENABLED,
        "configured": bool(settings.PLANTNET_API_KEY),
        "note": "Free tier: 500 identifications/day. Used to cross-check species identity.",
    }


def identify(image_bytes: bytes) -> dict[str, Any]:
    if not settings.PLANTNET_ENABLED or not settings.PLANTNET_API_KEY:
        return {
            "available": False,
            "reason": "Pl@ntNet API key not configured.",
            "candidates": [],
        }

    url = "https://my-api.plantnet.org/v2/identify/all"
    try:
        with httpx.Client(timeout=settings.EXTERNAL_TIMEOUT) as client:
            response = client.post(
                url,
                params={"api-key": settings.PLANTNET_API_KEY},
                data={"organs": "leaf"},
                files={"images": ("leaf.jpg", image_bytes, "image/jpeg")},
            )
        if response.status_code != 200:
            return {
                "available": False,
                "reason": f"Pl@ntNet HTTP {response.status_code}",
                "candidates": [],
            }

        results = response.json().get("results") or []
        candidates: list[dict[str, Any]] = []
        for result in results[:3]:
            species = result.get("species") or {}
            candidates.append(
                {
                    "species": species.get("scientificNameWithoutAuthor")
                    or species.get("scientificName")
                    or "Unknown",
                    "commonName": (species.get("commonNames") or [""])[0],
                    "confidence": result.get("score"),
                }
            )

        best = candidates[0] if candidates else {}
        return {
            "available": True,
            "species": best.get("species", ""),
            "commonName": best.get("commonName", ""),
            "confidence": best.get("confidence"),
            "candidates": candidates,
            "attribution": "Identification supported by Pl@ntNet API",
        }
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        return {
            "available": False,
            "reason": f"Pl@ntNet unavailable: {str(exc)[:120]}",
            "candidates": [],
        }
