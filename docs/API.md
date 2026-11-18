# API reference

The interactive OpenAPI explorer is available at <http://127.0.0.1:8000/docs>
while the server is running.

## Public endpoints

### `GET /api/health`

Returns model and service availability.

```json
{
  "status": "ok",
  "model": { "loaded": true, "classCount": 38 },
  "gemini": { "available": true },
  "plantnet": { "configured": true }
}
```

### `GET /api/model/info`

Returns the resolved model path, class count, thresholds, and TTA settings.

### `GET /api/stats`

Returns dashboard counters, condition/plant distributions, and recent records.

### `GET /api/diseases`

Returns the 38-class reference library. Each entry includes plant, condition,
symptoms, severity, recommended actions, and prevention notes.

### `POST /api/detect`

Uploads one leaf image and runs the identification pipeline.

- Content type: `multipart/form-data`
- Required field: `image`
- Optional fields: `latitude`, `longitude`
- Response: a result object containing `status`, `plant`, `disease`,
  `isHealthy`, `imageUrl`, `localInfo`, optional `ai.explanation`, and optional
  `weather`.

Example:

```bash
curl -F "image=@leaf.jpg" http://127.0.0.1:8000/api/detect
```

### `GET /api/history`

Lists saved identifications.

| Query parameter | Description |
| --- | --- |
| `limit` | Maximum number of records |
| `query` | Free-text search over plant/condition |
| `status` | `success`, `uncertain`, `unsupported`, or `rejected` |

### `GET /api/history/{id}`

Returns one saved identification, including stored explanation data.

### `DELETE /api/history/{id}`

Deletes one record and its saved image.

### `DELETE /api/history`

Clears all saved records and uploaded images.

## Admin endpoints

Admin routes require a signed session cookie created by `POST /api/admin/login`.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/admin/login` | Start admin session |
| `POST` | `/api/admin/logout` | End admin session |
| `GET` | `/api/admin/status` | Check current session |
| `GET` | `/api/admin/stats` | Aggregated study statistics |
| `GET` | `/api/admin/system` | Model, services, and configuration status |

## Status values

| Value | Meaning |
| --- | --- |
| `success` | A plant and condition were identified |
| `uncertain` | The image was reviewed but needs human confirmation |
| `unsupported` | The plant is outside the reference set |
| `rejected` | The image was unsuitable for review |

## Error responses

Errors follow the FastAPI convention:

```json
{ "detail": "Image must be a JPG, PNG, or WEBP file." }
```
