# Architecture

## Runtime model

The application is a single FastAPI service launched by `run.py`. One process
serves the dashboard, admin panel, static assets, saved images, and JSON API.

```text
Browser
  │
  ├── / , /admin , /static/* , /media/*      → Jinja templates + static files
  │
  └── /api/*                                 → JSON routers
                                                   │
                                                   ▼
                                           detection_service
                                          ┌────────┼─────────┐
                                          ▼        ▼         ▼
                                      model     image      support
                                     service    guard      adapters
                                          │                  │
                                          ▼                  ▼
                                   trained_model.keras   optional services
                                                          + Open-Meteo
                                          │
                                          ▼
                                   SQLite + local uploads
```

## Request flow for an identification

1. `routers/detect.py` validates the multipart upload.
2. `services/image_guard.py` checks format, size, dimensions, blur, and basic
   leaf-likeness.
3. `services/model_service.py` loads the Keras model once and runs the 38-class
   prediction with 128 × 128 RGB preprocessing and optional TTA.
4. `db.py` saves the image under `data/uploads/` and the result in
   `data/plant_disease.db`.
5. If the local match is reliable, the local result is used. If it is not,
   `detection_service.py` consults the configured support adapters before
   producing the final detailed report.
6. `app/static/js/app.js` renders the API result into the academic result
   sections shown in the browser.

## Module responsibilities

| Module | Responsibility |
| --- | --- |
| `app/config.py` | Loads environment variables and resolves local paths |
| `app/db.py` | SQLite schema, inserts, queries, and statistics |
| `app/disease_data.py` | Class-name and disease-library lookups |
| `app/security.py` | Password hashing and signed admin sessions |
| `app/routers/meta.py` | Health, model info, disease library, weather |
| `app/routers/detect.py` | Image upload and identification |
| `app/routers/history.py` | Saved-record operations |
| `app/routers/admin.py` | Protected statistics and system details |
| `app/services/model_service.py` | Model lifecycle and inference |
| `app/services/image_guard.py` | Image quality checks |
| `app/services/detection_service.py` | End-to-end identification pipeline |
| `app/services/gemini_service.py` | Backend visual analysis adapter |
| `app/services/plantnet_service.py` | Optional species reference adapter |
| `app/services/weather_service.py` | Optional local weather context |

## Design notes

- The trained model is always tried first; the external path is a fallback for
  uncertain results or plants outside the reference set.
- Backend API response shapes are kept stable. Presentation decisions are made
  in the frontend so backend behavior is not coupled to UI wording.
- All secrets remain server-side. The browser never receives provider keys.
- Runtime data is local by design and excluded from version control.
- Every Python module includes a module docstring; complex functions carry
  inline docstrings describing their contract.
