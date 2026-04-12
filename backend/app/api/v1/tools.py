from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.tool import Tool
from app.models.user import User
from app.schemas.tool import (
    ToolBrief,
    ToolCreate,
    ToolExportItem,
    ToolImportItem,
    ToolResponse,
    ToolUpdate,
    ToolVersionResponse,
)
from app.services.tool_service import ToolService

router = APIRouter(prefix="/tools", tags=["tools"])


# ── Fixed-path endpoints (must be before /{tool_id}) ────────────────────


@router.get("/")
async def list_tools(
    db: Session = Depends(get_db),
):
    tools = db.query(Tool).order_by(Tool.created_at.desc()).limit(100).all()
    return {
        "code": 200,
        "message": "success",
        "data": [ToolBrief.model_validate(t).model_dump() for t in tools],
    }


@router.post("/")
async def create_tool(
    data: ToolCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ToolService(db)
    tool = svc.create_tool(data, user_id=current_user.id)
    return {
        "code": 200,
        "message": "Tool created",
        "data": ToolResponse.model_validate(tool).model_dump(),
    }


@router.get("/search")
async def search_tools(q: str, db: Session = Depends(get_db)):
    tools = (
        db.query(Tool)
        .filter(
            Tool.name.ilike(f"%{q}%") | Tool.description.ilike(f"%{q}%")
        )
        .limit(20)
        .all()
    )
    return {
        "code": 200,
        "message": "success",
        "data": [ToolBrief.model_validate(t).model_dump() for t in tools],
    }


@router.get("/export")
async def export_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ToolService(db)
    tools = svc.export_all()
    return {
        "code": 200,
        "message": "success",
        "data": [ToolExportItem.model_validate(t).model_dump() for t in tools],
    }


@router.post("/import")
async def import_tools(
    items: list[ToolImportItem],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ToolService(db)
    result = svc.import_tools(items, user_id=current_user.id)
    return {
        "code": 200,
        "message": "Import completed",
        "data": result,
    }


# ── Parameterized endpoints ─────────────────────────────────────────────


@router.get("/{tool_id}")
async def get_tool(tool_id: int, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "code": 200,
        "message": "success",
        "data": ToolResponse.model_validate(tool).model_dump(),
    }


@router.put("/{tool_id}")
async def update_tool(
    tool_id: int,
    data: ToolUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ToolService(db)
    tool = svc.update_tool(tool_id, data, user_id=current_user.id)
    return {
        "code": 200,
        "message": "Tool updated",
        "data": ToolResponse.model_validate(tool).model_dump(),
    }


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ToolService(db)
    svc.delete_tool(tool_id)
    return {"code": 200, "message": "Tool deleted", "data": None}


@router.get("/{tool_id}/versions")
async def get_versions(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ToolService(db)
    versions = svc.get_tool_versions(tool_id)
    return {
        "code": 200,
        "message": "success",
        "data": [ToolVersionResponse.model_validate(v).model_dump() for v in versions],
    }


@router.post("/{tool_id}/rollback/{version}")
async def rollback_version(
    tool_id: int,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ToolService(db)
    tool = svc.rollback_version(tool_id, version)
    return {
        "code": 200,
        "message": f"Rolled back to version {version}",
        "data": ToolResponse.model_validate(tool).model_dump(),
    }
