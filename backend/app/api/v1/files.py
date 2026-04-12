import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/browse")
async def browse_directory(path: str = Query(default="")):
    base = Path(settings.sandbox_dir).resolve()
    if path:
        target = (base / path).resolve()
    else:
        target = base

    if target != base and base not in target.parents:
        raise HTTPException(status_code=403, detail="Access denied: path outside sandbox")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            entries.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
                "path": str(entry.relative_to(base)),
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "current": str(target.relative_to(base)) if target != base else "",
            "entries": entries,
        },
    }
