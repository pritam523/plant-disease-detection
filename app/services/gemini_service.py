"""Gemini adapter: detailed visual plant-health analysis.

Gemini supports the local classifier when the local model is reliable. When the
local model cannot make a dependable match, Gemini becomes the primary
diagnostic assistant and its answer is clearly labelled as AI-assisted.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import time
from collections import OrderedDict
from typing import Any

import httpx
from PIL import Image, ImageOps

from ..config import settings

SUPPORT_SYSTEM_PROMPT = """You are a careful plant-pathology assistant supporting a local image classifier.
You will be given a leaf photo and the classifier's top predictions as context.

Rules:
- The local classifier is the primary diagnostic signal; use its output as context, not as absolute truth.
- First decide whether the photo actually shows a plant leaf. If it clearly does not, set isLeaf to false.
- Decide whether the plant is one of the supported plants listed in the context. If it is not, set supportedPlant to false and do not give disease-specific treatment advice.
- Be practical and science-based. Never invent chemical dosages, pesticide names, or unverified home cures. If unsure, say so and recommend a local agricultural extension service.
- Keep every section short: at most 3 concise bullet-like strings.
- Return ONLY a JSON object with exactly these keys:
  isLeaf (boolean), plant (string), supportedPlant (boolean), assessment (string),
  causes (array of strings), symptoms (array of strings), spread (array of strings),
  prevention (array of strings), treatment (array of strings), futureCare (array of strings),
  sources (array of URL strings), uncertainty (string).
"""

PRIMARY_SYSTEM_PROMPT = """You are the primary plant-health assistant for a web application. A local trained classifier could not make a dependable match to its 38 known classes. Inspect the uploaded image directly and answer like an experienced, careful plant pathologist.

Rules:
- First decide whether the image shows a plant leaf, flower, fruit, or plant stem. If it clearly does not, set isLeaf to false and explain briefly.
- Identify the plant as precisely as the visual evidence allows. Use the Pl@ntNet species candidates in the context as supporting evidence, but trust the image if they conflict and explain the conflict.
- Identify the most likely health condition. If the plant appears healthy, set healthy to true and condition to "Healthy".
- Write a detailed assessment that describes what you actually see, how confident you are, and what could produce similar symptoms.
- Provide differential diagnoses in plain language, each with a likelihood and a distinguishing clue.
- Give practical, science-based actions: immediate steps, prevention, treatment options, and future care. Never invent chemical dosages or brand names. Recommend a local agricultural extension service for product choices and regional rules.
- Be honest about uncertainty and poor image quality. Explain what a better photo should show.
- Include reputable source URLs only if you are confident they exist. Do not invent citations.
- Return ONLY a JSON object with exactly these keys:
  isLeaf (boolean), plant (string), supportedPlant (boolean), healthy (boolean),
  condition (string), confidence (number from 0 to 1), assessment (string),
  keyFindings (array of strings), differentials (array of strings),
  causes (array of strings), symptoms (array of strings), spread (array of strings),
  prevention (array of strings), treatment (array of strings), futureCare (array of strings),
  sources (array of URL strings), uncertainty (string).
"""

EMPTY_RESULT: dict[str, Any] = {
    "isLeaf": None,
    "plant": "",
    "supportedPlant": None,
    "healthy": None,
    "condition": "",
    "confidence": None,
    "assessment": "",
    "keyFindings": [],
    "differentials": [],
    "causes": [],
    "symptoms": [],
    "spread": [],
    "prevention": [],
    "treatment": [],
    "futureCare": [],
    "sources": [],
    "uncertainty": "",
}

BOOL_KEYS = {"isLeaf", "supportedPlant", "healthy"}
LIST_KEYS = {key for key, value in EMPTY_RESULT.items() if isinstance(value, list)}


def _prepare_image(image_bytes: bytes) -> str:
    with Image.open(io.BytesIO(image_bytes)) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")
    image.thumbnail((settings.GEMINI_MAX_IMAGE_PX, settings.GEMINI_MAX_IMAGE_PX))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    return parsed if isinstance(parsed, dict) else {}


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    result = dict(EMPTY_RESULT)
    for key in EMPTY_RESULT:
        if key not in raw:
            continue
        value = raw[key]
        if key in BOOL_KEYS:
            result[key] = bool(value) if isinstance(value, bool) else None
        elif key == "confidence":
            try:
                number = float(value)
                result[key] = min(1.0, max(0.0, number))
            except (TypeError, ValueError):
                result[key] = None
        elif key in LIST_KEYS:
            if isinstance(value, list):
                result[key] = [str(item).strip() for item in value if str(item).strip()][:6]
            elif isinstance(value, str) and value.strip():
                result[key] = [value.strip()]
        else:
            result[key] = str(value).strip()
    return result


class GeminiService:
    def __init__(self) -> None:
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.calls = 0
        self.last_error = ""
        self.last_success: str | None = None

    @property
    def available(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "model": settings.GEMINI_MODEL,
            "groundingEnabled": settings.GEMINI_GROUNDING_ENABLED,
            "calls": self.calls,
            "lastSuccess": self.last_success,
            "lastError": self.last_error,
            "cacheSize": len(self._cache),
        }

    def analyze(
        self,
        image_bytes: bytes,
        context: dict[str, Any],
        primary: bool = False,
    ) -> dict[str, Any]:
        if not self.available:
            return {
                "available": False,
                "primary": primary,
                "reason": "GEMINI_API_KEY is not configured.",
                "explanation": dict(EMPTY_RESULT),
                "sources": [],
            }

        cache_key = hashlib.sha256(
            image_bytes
            + json.dumps(context, sort_keys=True, default=str).encode("utf-8")
            + str(primary).encode("ascii")
        ).hexdigest()
        if cache_key in self._cache:
            cached = self._cache.pop(cache_key)
            self._cache[cache_key] = cached
            return {
                "available": True,
                "primary": primary,
                "cached": True,
                "explanation": cached,
                "sources": cached.get("sources", []),
            }

        user_prompt = (
            "Context (JSON):\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
            + "\n\nInspect the image and answer with the required JSON object."
        )
        parts: list[dict[str, Any]] = [
            {"text": user_prompt},
            {"inlineData": {"mimeType": "image/jpeg", "data": _prepare_image(image_bytes)}},
        ]
        body: dict[str, Any] = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": PRIMARY_SYSTEM_PROMPT if primary else SUPPORT_SYSTEM_PROMPT,
                    }
                ]
            },
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1800 if primary else 1400,
                "responseMimeType": "application/json",
            },
        }
        if settings.GEMINI_GROUNDING_ENABLED:
            body["tools"] = [{"googleSearch": {}}]

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        last_message = "Unknown Gemini error"
        for attempt in range(3):
            self.calls += 1
            try:
                with httpx.Client(timeout=settings.GEMINI_TIMEOUT) as client:
                    response = client.post(url, params={"key": settings.GEMINI_API_KEY}, json=body)
                if response.status_code == 200:
                    payload = response.json()
                    candidate = (payload.get("candidates") or [{}])[0]
                    text = ""
                    for part in (candidate.get("content") or {}).get("parts", []):
                        if part.get("text"):
                            text += part["text"]
                    explanation = _normalise(_extract_json(text))
                    for chunk in (candidate.get("groundingMetadata") or {}).get("groundingChunks", []):
                        web = chunk.get("web") or {}
                        if web.get("uri") and web["uri"] not in explanation["sources"]:
                            explanation["sources"].append(web["uri"])
                    self.last_error = ""
                    self.last_success = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    self._cache[cache_key] = explanation
                    while len(self._cache) > settings.GEMINI_CACHE_SIZE:
                        self._cache.popitem(last=False)
                    return {
                        "available": True,
                        "primary": primary,
                        "cached": False,
                        "explanation": explanation,
                        "sources": explanation["sources"],
                    }
                error_payload = response.json()
                last_message = (
                    error_payload.get("error", {}).get("message")
                    or f"HTTP {response.status_code}"
                )
                if response.status_code not in {429, 500, 503}:
                    break
            except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
                last_message = str(exc)[:300]
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))

        self.last_error = last_message[:300]
        return {
            "available": False,
            "primary": primary,
            "reason": f"Gemini request failed: {last_message[:180]}",
            "explanation": dict(EMPTY_RESULT),
            "sources": [],
        }


gemini_service = GeminiService()
