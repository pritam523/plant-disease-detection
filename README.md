# Plant Disease Detection

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009485)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

A local-first web application for an academic study of plant disease identification from leaf photographs. The application reuses a trained 38-class Keras image model and presents results through a clean, research-oriented dashboard with saved history and a protected admin panel.

> **Note:** The browser interface intentionally uses plain academic language. External support services are backend-only and are never presented as user-facing features.

![Application dashboard](docs/assets/home_page.jpeg)

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Tests](#tests)
- [API overview](#api-overview)
- [Model and data](#model-and-data)
- [Security and privacy](#security-and-privacy)
- [Documentation](#documentation)
- [Credits](#credits)
- [License](#license)

---

## Overview

The system runs as a single Python service. It combines:

- a trained local image classifier for 38 plant/condition classes;
- a local reference library of symptoms, severity, and care information;
- SQLite-backed history and image storage;
- a server-rendered dashboard and admin panel;
- optional backend support services for images that fall outside the trained reference set.

The trained model is always attempted first. When the local result is not dependable, the backend may consult external plant references and a visual reasoning service to produce a detailed identification. All of this is handled server-side; the user only sees a normal identification report.

---

## Features

- **Leaf image identification** with drag-and-drop upload and preview.
- **Structured results** using academic sections:
  - Plant Information
  - Identification Result
  - Plant Description
  - Characteristics
  - Uses
  - Growing Conditions
  - Care Instructions
- **Reference library** covering all 38 supported classes.
- **Persistent history** with search, filters, detail view, and deletion.
- **Admin panel** with statistics, system details, and history management.
- **Image validation** for file type, dimensions, blur, and basic leaf-likeness.
- **Optional weather context** from Open-Meteo (no key required).
- **Automatic fallback** for plants outside the trained class set.
- **Local-only operation** for the core prediction path; no cloud database is required.

---

## Project structure

```text
plant-disease-detection/
├── app/                         # FastAPI application
│   ├── routers/                 # Health, detection, history, admin endpoints
│   ├── services/                # Model, image, reference, and support adapters
│   ├── static/                  # CSS and JavaScript for the dashboard
│   ├── templates/               # Base, dashboard, and admin templates
│   ├── config.py                # Environment-driven settings
│   ├── db.py                    # SQLite persistence
│   ├── disease_data.py          # Class-name and disease-library helpers
│   ├── main.py                  # Application entry point
│   └── security.py              # Admin hashing and signed sessions
├── data/                        # Runtime database and uploads (ignored by Git)
├── disease_data/                # class_names.json and diseases.json
├── docs/                        # Architecture, API, and dataset documentation
│   └── assets/                  # README screenshot
├── model/
│   └── trained_model.keras      # Trained 38-class Keras model (~94 MB)
├── notebooks/                   # Training and evaluation notebooks
├── tests/
│   └── test_smoke.py            # Automated smoke tests
├── .env.example                 # Safe configuration template
├── .gitignore                   # Secrets, runtime data, caches, legacy folders
├── CITATION.cff                 # Academic citation metadata
├── LICENSE                      # MIT License
├── README.md                    # This guide
├── requirements.txt             # Canonical Python dependencies
└── run.py                       # Launcher and maintenance utilities
```

The legacy `client/`, `server/`, and `ml-service/` folders from an earlier experimental stack are intentionally not published in this repository. They remain on the local working machine but are ignored by Git.

---

## Quick start

### Prerequisites

- Python 3.12
- Git (only needed to clone the repository)
- Approximately 2 GB of free disk space for the environment and dependencies

### Windows (PowerShell)

```powershell
git clone https://github.com/pritam523/plant-disease-detection.git
cd plant-disease-detection

py -3.12 -m venv .venv-app
.\.venv-app\Scripts\python.exe -m pip install --upgrade pip
.\.venv-app\Scripts\python.exe -m pip install -r requirements.txt

Copy-Item .env.example .env
.\.venv-app\Scripts\python.exe run.py check
.\.venv-app\Scripts\python.exe run.py
```

### macOS / Linux

```bash
git clone https://github.com/pritam523/plant-disease-detection.git
cd plant-disease-detection

python3.12 -m venv .venv-app
.venv-app/bin/python -m pip install --upgrade pip
.venv-app/bin/python -m pip install -r requirements.txt

cp .env.example .env
.venv-app/bin/python run.py check
.venv-app/bin/python run.py
```

Open:

- User dashboard: <http://127.0.0.1:8000/>
- Admin panel: <http://127.0.0.1:8000/admin>
- API documentation: <http://127.0.0.1:8000/docs>

Press `Ctrl+C` to stop the server.

---

## Configuration

All configuration is read from `.env`. Copy `.env.example` to `.env` and edit as needed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_HOST` | `127.0.0.1` | Local bind address |
| `APP_PORT` | `8000` | Local port |
| `MODEL_PATH` | `model/trained_model.keras` | Trained model location |
| `PREDICTION_CONFIDENCE_THRESHOLD` | `0.50` | Minimum confidence for a reliable local match |
| `PREDICTION_MARGIN_THRESHOLD` | `0.10` | Minimum gap between the top two classes |
| `TTA_ENABLED` | `true` | Enable test-time augmentation |
| `TTA_VIEWS` | `4` | Number of augmented views |
| `IMAGE_GUARD_ENABLED` | `true` | Basic image sanity checks |
| `GEMINI_API_KEY` | empty | Backend visual analysis support |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Configurable model identifier |
| `AI_FALLBACK_ENABLED` | `true` | Enable extended identification path |
| `OPEN_METEO_ENABLED` | `true` | Optional local weather context |
| `PLANTNET_API_KEY` | empty | Optional species reference |
| `ADMIN_PASSWORD_HASH` | empty | Admin password hash |
| `ADMIN_SECRET_KEY` | placeholder | Session signing secret |

Generate a new admin password hash:

```powershell
.\.venv-app\Scripts\python.exe run.py hash-password
```

Paste the printed value into `.env` as `ADMIN_PASSWORD_HASH`, then restart the app.

---

## Tests

Run the automated smoke suite:

```powershell
.\.venv-app\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers health checks, the disease library, invalid uploads, detection plus history, admin authentication, graceful behavior without external keys, and the automatic fallback path.

---

## API overview

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Service and model status |
| `GET` | `/api/model/info` | Model path, classes, and thresholds |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/diseases` | 38-class reference library |
| `POST` | `/api/detect` | Upload an image and run identification |
| `GET` | `/api/history` | List saved identifications |
| `GET` | `/api/history/{id}` | Detail for one identification |
| `DELETE` | `/api/history/{id}` | Delete one identification |
| `DELETE` | `/api/history` | Clear all history |
| `POST` | `/api/admin/login` | Create an admin session |
| `POST` | `/api/admin/logout` | End an admin session |
| `GET` | `/api/admin/stats` | Protected statistics |
| `GET` | `/api/admin/system` | Protected system details |

See [docs/API.md](docs/API.md) for request and response details.

---

## Model and data

- **Model:** `model/trained_model.keras`
- **Input:** 128 × 128 RGB leaf image
- **Classes:** 38 plant/condition combinations
- **Class order:** `disease_data/class_names.json`
- **Reference text:** `disease_data/diseases.json`
- **Runtime data:** `data/plant_disease.db` and `data/uploads/` (created locally, ignored by Git)

The original training dataset is not included because of its size. See [docs/DATASET.md](docs/DATASET.md) for provenance and download information.

Training and evaluation notebooks are available in [`notebooks/`](notebooks/).

---

## Security and privacy

- `.env` is ignored by Git. Never commit API keys or passwords.
- Keys are used only on the server side and are never sent to the browser.
- Change `ADMIN_SECRET_KEY` and generate a real `ADMIN_PASSWORD_HASH` before sharing a deployment.
- Uploaded images and the SQLite database stay in the local `data/` directory.
- The app is intended for local research and demonstration use, not as a public production service.

See [SECURITY.md](SECURITY.md) for reporting and key-handling guidance.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md)
- [Dataset and classes](docs/DATASET.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

---

## Credits

**Made By:**

- Pritam Saha
- Priyota Chowdhury Mumu

This project was prepared as a university study project. It is shared for educational and research use.

---

## License

Released under the [MIT License](LICENSE).
