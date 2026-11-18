"""Automated smoke tests for the local application.

Run: .venv-app\\Scripts\\python.exe -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

SAMPLE_IMAGE = Path(
    os.getenv(
        "SAMPLE_LEAF_IMAGE",
        str(Path(__file__).resolve().parent / "assets" / "sample_leaf.jpg"),
    )
)


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        cls.created: list[str] = []

    @classmethod
    def tearDownClass(cls) -> None:
        for record_id in list(cls.created):
            cls.client.delete(f"/api/history/{record_id}")
        cls.client_context.__exit__(None, None, None)

    def test_01_health_and_model(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["modelLoaded"], data)
        self.assertEqual(data["classCount"], 38)

        info = self.client.get("/api/model/info").json()
        self.assertEqual(info["classCount"], 38)
        self.assertEqual(info["inputSize"], [128, 128])

    def test_02_library(self) -> None:
        response = self.client.get("/api/diseases")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 38)

    def test_03_rejects_non_image(self) -> None:
        response = self.client.post(
            "/api/detect",
            files={"image": ("notes.txt", b"not an image", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)

    @unittest.skipUnless(SAMPLE_IMAGE.exists(), "Sample leaf image not found")
    def test_04_detection_and_history(self) -> None:
        with open(SAMPLE_IMAGE, "rb") as handle:
            response = self.client.post(
                "/api/detect",
                files={"image": (SAMPLE_IMAGE.name, handle.read(), "image/jpeg")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertIn(result["status"], {"success", "uncertain", "unsupported", "rejected"})
        self.assertTrue(result["id"])
        self.assertTrue(result["imageUrl"].startswith("/media/"))
        self.created.append(result["id"])

        history = self.client.get("/api/history").json()
        self.assertIn(result["id"], [item["id"] for item in history["items"]])

        detail = self.client.get(f"/api/history/{result['id']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["id"], result["id"])

        deleted = self.client.delete(f"/api/history/{result['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.created.remove(result["id"])
        self.assertEqual(self.client.get(f"/api/history/{result['id']}").status_code, 404)

    def test_05_admin_auth(self) -> None:
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 401)
        wrong = self.client.post("/api/admin/login", json={"password": "wrong-password"})
        self.assertEqual(wrong.status_code, 401)
        login = self.client.post("/api/admin/login", json={"password": "admin123"})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/system").status_code, 200)
        self.client.post("/api/admin/logout")
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 401)

    def test_06_graceful_without_gemini_key(self) -> None:
        if os.getenv("GEMINI_API_KEY"):
            self.skipTest("Gemini key configured")
        status = self.client.get("/api/services/status").json()["gemini"]
        self.assertFalse(status["available"])

    @unittest.skipUnless(SAMPLE_IMAGE.exists(), "Sample leaf image not found")
    def test_07_ai_fallback_when_local_is_not_reliable(self) -> None:
        uncertain = {
            "status": "uncertain",
            "predictedClass": "Tomato___Early_blight",
            "confidence": 0.473,
            "margin": 0.161,
            "topPredictions": [{"className": "Tomato___Early_blight", "confidence": 0.473}],
            "notes": ["Confidence is below the configured threshold."],
        }
        plantnet = {
            "available": True,
            "species": "Rosa spp.",
            "commonName": "Rose",
            "confidence": 0.54,
            "candidates": [{"species": "Rosa spp.", "commonName": "Rose", "confidence": 0.54}],
        }
        gemini = {
            "available": True,
            "primary": True,
            "explanation": {
                "isLeaf": True,
                "plant": "Rose",
                "supportedPlant": False,
                "healthy": False,
                "condition": "Rose leaf spot",
                "confidence": 0.82,
                "assessment": "Dark angular lesions with yellow halos on a rose leaf.",
                "keyFindings": ["Angular lesions", "Yellow halos"],
                "differentials": ["Black spot — usually rounder spots"],
                "uncertainty": "Confirm with a local extension service.",
            },
            "sources": ["https://extension.umn.edu/"],
        }
        with (
            patch("app.services.detection_service.model_service.predict", return_value=uncertain),
            patch("app.services.detection_service.plantnet_service.identify", return_value=plantnet),
            patch("app.services.detection_service.gemini_service.analyze", return_value=gemini),
        ):
            with open(SAMPLE_IMAGE, "rb") as handle:
                response = self.client.post(
                    "/api/detect",
                    files={"image": (SAMPLE_IMAGE.name, handle.read(), "image/jpeg")},
                )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source"], "ai_assisted")
        self.assertEqual(result["plant"], "Rose")
        self.assertEqual(result["disease"], "Rose leaf spot")
        self.assertEqual(result["confidence"], 0.82)
        self.assertTrue(result["ai"]["primary"])
        self.assertFalse(result["localPrediction"]["reliable"])
        self.assertTrue(result["plantnet"]["available"])
        self.created.append(result["id"])

        detail = self.client.get(f"/api/history/{result['id']}").json()
        self.assertEqual(detail["source"], "ai_assisted")
        self.assertEqual(detail["confidence_source"], "Gemini visual assessment")


if __name__ == "__main__":
    unittest.main()
