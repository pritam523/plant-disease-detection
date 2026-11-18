"""SQLite persistence for predictions/history (survives restarts)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id                  TEXT PRIMARY KEY,
    created_at          TEXT NOT NULL,
    status              TEXT NOT NULL,
    predicted_class     TEXT,
    plant               TEXT,
    disease             TEXT,
    confidence          REAL,
    margin              REAL,
    top_predictions     TEXT NOT NULL DEFAULT '[]',
    is_healthy          INTEGER NOT NULL DEFAULT 0,
    image_path          TEXT NOT NULL,
    original_filename   TEXT NOT NULL,
    quality             TEXT NOT NULL DEFAULT '{}',
    ai_explanation      TEXT NOT NULL DEFAULT '{}',
    sources             TEXT NOT NULL DEFAULT '[]',
    weather             TEXT NOT NULL DEFAULT '{}',
    plantnet            TEXT NOT NULL DEFAULT '{}',
    source              TEXT NOT NULL DEFAULT 'local_model',
    confidence_source   TEXT,
    local_prediction    TEXT NOT NULL DEFAULT '{}',
    message             TEXT NOT NULL DEFAULT '',
    notes               TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(settings.DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _migrate(connection: sqlite3.Connection) -> None:
    """Add newer columns to databases created by earlier app versions."""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(predictions)")}
    additions = {
        "source": "TEXT NOT NULL DEFAULT 'local_model'",
        "confidence_source": "TEXT",
        "local_prediction": "TEXT NOT NULL DEFAULT '{}'",
        "message": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE predictions ADD COLUMN {name} {definition}")


def init_db() -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with _connection() as connection:
        connection.executescript(SCHEMA)
        _migrate(connection)


def new_id() -> str:
    return uuid.uuid4().hex


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def insert_prediction(record: dict[str, Any]) -> str:
    record_id = record.get("id") or new_id()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO predictions (
                id, created_at, status, predicted_class, plant, disease,
                confidence, margin, top_predictions, is_healthy, image_path,
                original_filename, quality, ai_explanation, sources, weather,
                plantnet, source, confidence_source, local_prediction, message, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                record.get("created_at") or _now(),
                record.get("status", "unknown"),
                record.get("predicted_class"),
                record.get("plant"),
                record.get("disease"),
                record.get("confidence"),
                record.get("margin"),
                _dump(record.get("top_predictions") or []),
                1 if record.get("is_healthy") else 0,
                record["image_path"],
                record.get("original_filename", "upload"),
                _dump(record.get("quality") or {}),
                _dump(record.get("ai_explanation") or {}),
                _dump(record.get("sources") or []),
                _dump(record.get("weather") or {}),
                _dump(record.get("plantnet") or {}),
                record.get("source", "local_model") or "local_model",
                record.get("confidence_source"),
                _dump(record.get("local_prediction") or {}),
                record.get("message", "") or "",
                record.get("notes", "") or "",
            ),
        )
    return record_id


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in (
        "top_predictions", "quality", "ai_explanation", "sources", "weather",
        "plantnet", "local_prediction",
    ):
        try:
            item[key] = json.loads(item.get(key) or ("[]" if key in {"top_predictions", "sources"} else "{}"))
        except (json.JSONDecodeError, TypeError):
            item[key] = [] if key in {"top_predictions", "sources"} else {}
    item["is_healthy"] = bool(item.get("is_healthy"))
    item["image_url"] = "/media/" + str(item["image_path"]).replace("\\", "/").lstrip("/")
    return item


def get_prediction(record_id: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM predictions WHERE id = ?", (record_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_predictions(
    limit: int = 50,
    offset: int = 0,
    query: str = "",
    status: str = "",
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if query:
        clauses.append("(plant LIKE ? OR disease LIKE ? OR original_filename LIKE ? OR predicted_class LIKE ?)")
        pattern = f"%{query}%"
        params.extend([pattern] * 4)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.extend([limit, offset])
    with _connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM predictions{where} ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def count_predictions() -> int:
    with _connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])


def delete_prediction(record_id: str) -> str | None:
    with _connection() as connection:
        row = connection.execute("SELECT image_path FROM predictions WHERE id = ?", (record_id,)).fetchone()
        if not row:
            return None
        connection.execute("DELETE FROM predictions WHERE id = ?", (record_id,))
    return str(row["image_path"])


def clear_predictions() -> list[str]:
    with _connection() as connection:
        rows = connection.execute("SELECT image_path FROM predictions").fetchall()
        connection.execute("DELETE FROM predictions")
    return [str(row["image_path"]) for row in rows]


def stats() -> dict[str, Any]:
    with _connection() as connection:
        rows = connection.execute(
            "SELECT status, is_healthy, disease, plant, confidence, source FROM predictions"
        ).fetchall()
        recent = connection.execute(
            "SELECT * FROM predictions ORDER BY created_at DESC, rowid DESC LIMIT 8"
        ).fetchall()

    total = len(rows)
    success = [row for row in rows if row["status"] == "success"]
    healthy = sum(1 for row in success if row["is_healthy"])
    diseased = len(success) - healthy
    uncertain = sum(1 for row in rows if row["status"] == "uncertain")
    rejected = sum(1 for row in rows if row["status"] in {"rejected", "unsupported"})
    ai_assisted = sum(1 for row in rows if (row["source"] or "") == "ai_assisted")

    by_disease: dict[str, int] = {}
    by_plant: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for row in rows:
        source = row["source"] or "local_model"
        by_source[source] = by_source.get(source, 0) + 1
    for row in success:
        by_disease[row["disease"] or "Unknown"] = by_disease.get(row["disease"] or "Unknown", 0) + 1
        by_plant[row["plant"] or "Unknown"] = by_plant.get(row["plant"] or "Unknown", 0) + 1

    average_confidence = (
        sum(float(row["confidence"] or 0) for row in success) / len(success) if success else 0.0
    )

    return {
        "total": total,
        "successful": len(success),
        "healthy": healthy,
        "diseased": diseased,
        "uncertain": uncertain,
        "rejected_or_unsupported": rejected,
        "ai_assisted": ai_assisted,
        "average_confidence": round(average_confidence, 4),
        "by_source": sorted(
            ({"name": name, "value": value} for name, value in by_source.items()),
            key=lambda item: item["value"],
            reverse=True,
        ),
        "by_disease": sorted(
            ({"name": name, "value": value} for name, value in by_disease.items()),
            key=lambda item: item["value"],
            reverse=True,
        ),
        "by_plant": sorted(
            ({"name": name, "value": value} for name, value in by_plant.items()),
            key=lambda item: item["value"],
            reverse=True,
        ),
        "recent": [_row_to_dict(row) for row in recent],
    }


def delete_image(image_path: str) -> None:
    full_path = settings.DATA_DIR / image_path
    try:
        if full_path.exists() and full_path.is_file():
            full_path.unlink()
    except OSError:
        pass
