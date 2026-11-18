"""Optional Open-Meteo weather context (free, no key, non-commercial use)."""
from __future__ import annotations

import time
from typing import Any

import httpx

from ..config import settings

_cache: dict[tuple[float, float, int], tuple[float, dict[str, Any]]] = {}


def _weather_text(code: int) -> str:
    if code == 0:
        return "Clear sky"
    if code in {1, 2, 3}:
        return "Partly cloudy"
    if 45 <= code <= 48:
        return "Foggy"
    if 51 <= code <= 67:
        return "Rainy"
    if 71 <= code <= 77:
        return "Snowy"
    if 80 <= code <= 82:
        return "Showers"
    if 95 <= code <= 99:
        return "Thunderstorm"
    return "Variable conditions"


def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    if not settings.OPEN_METEO_ENABLED:
        return {"available": False, "reason": "Open-Meteo integration is disabled."}
    key = (round(latitude, 2), round(longitude, 2), int(time.time() // 300))
    if key in _cache:
        return _cache[key][1]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
        "timezone": "auto",
    }
    try:
        with httpx.Client(timeout=settings.EXTERNAL_TIMEOUT) as client:
            response = client.get(url, params=params)
        response.raise_for_status()
        current = response.json().get("current", {})
        result = {
            "available": True,
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "condition": _weather_text(int(current.get("weather_code", -1))),
            "time": current.get("time"),
            "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
        }
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        result = {"available": False, "reason": f"Weather data unavailable: {str(exc)[:120]}"}

    _cache.clear()
    _cache[key] = (time.time(), result)
    return result
