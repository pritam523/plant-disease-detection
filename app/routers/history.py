"""Detection history: list, detail, delete one, clear all."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .. import db

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    query: str = "",
    status: str = "",
) -> dict:
    items = db.list_predictions(limit=limit, offset=offset, query=query, status=status)
    return {"items": items, "total": db.count_predictions(), "limit": limit, "offset": offset}


@router.get("/{record_id}")
def history_detail(record_id: str) -> dict:
    item = db.get_prediction(record_id)
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    return item


@router.delete("/{record_id}")
def history_delete(record_id: str) -> dict:
    image_path = db.delete_prediction(record_id)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Record not found")
    if image_path:
        db.delete_image(image_path)
    return {"message": "Record deleted", "id": record_id}


@router.delete("")
def history_clear() -> dict:
    paths = db.clear_predictions()
    for image_path in paths:
        db.delete_image(image_path)
    return {"message": f"Cleared {len(paths)} records", "deleted": len(paths)}
