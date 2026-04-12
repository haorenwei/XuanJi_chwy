from pathlib import Path

from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.models.tool import Tool, ToolVersion
from app.schemas.tool import ToolCreate, ToolImportItem, ToolUpdate


class ToolService:
    def __init__(self, db: Session):
        self.db = db

    def create_tool(self, data: ToolCreate, user_id: int | None = None) -> Tool:
        tool = Tool(
            name=data.name,
            description=data.description,
            description_zh=getattr(data, "description_zh", None),
            code=data.code,
            language=data.language,
            tool_type=getattr(data, "tool_type", "atomic"),
            created_by=user_id,
        )
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def search_tools(self, query: str) -> list[Tool]:
        return (
            self.db.query(Tool)
            .filter(
                Tool.name.ilike(f"%{query}%")
                | Tool.description.ilike(f"%{query}%")
                | Tool.description_zh.ilike(f"%{query}%")
            )
            .limit(10)
            .all()
        )

    def get_by_name(self, name: str) -> Tool | None:
        return self.db.query(Tool).filter(Tool.name == name).first()

    def get_all(self, tool_type: str | None = None) -> list[Tool]:
        q = self.db.query(Tool)
        if tool_type:
            q = q.filter(Tool.tool_type == tool_type)
        return q.order_by(Tool.created_at.desc()).all()

    def save_tool_file(self, name: str, code: str) -> Path:
        """Save tool code to backend/app/tools/ directory."""
        tools_dir = Path(__file__).parent.parent / "tools"
        tools_dir.mkdir(exist_ok=True)
        file_path = tools_dir / f"{name}.py"
        file_path.write_text(code, encoding="utf-8")
        return file_path

    def update_tool(self, tool_id: int, data: ToolUpdate, user_id: int) -> Tool:
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        if tool.is_builtin:
            raise HTTPException(status_code=403, detail="Cannot edit builtin tools")
        # Save version snapshot before updating
        self.save_version_snapshot(tool_id, change_summary="Auto-saved before update", created_by=user_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tool, field, value)
        tool.version += 1
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def delete_tool(self, tool_id: int) -> None:
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        if tool.is_builtin:
            raise HTTPException(status_code=403, detail="Cannot delete builtin tools")
        self.db.delete(tool)
        self.db.commit()

    def export_all(self) -> list[Tool]:
        return self.db.query(Tool).order_by(Tool.created_at.desc()).all()

    def import_tools(
        self, items: list[ToolImportItem], user_id: int
    ) -> dict:
        created = 0
        updated = 0
        skipped = 0
        for item in items:
            existing = self.get_by_name(item.name)
            if existing:
                if existing.is_builtin:
                    skipped += 1
                    continue
                existing.description = item.description
                existing.description_zh = item.description_zh
                existing.code = item.code
                existing.language = item.language
                existing.tool_type = item.tool_type
                existing.version += 1
                updated += 1
            else:
                tool = Tool(
                    name=item.name,
                    description=item.description,
                    description_zh=item.description_zh,
                    code=item.code,
                    language=item.language,
                    tool_type=item.tool_type,
                    created_by=user_id,
                )
                self.db.add(tool)
                created += 1
        self.db.commit()
        return {"created": created, "updated": updated, "skipped": skipped}

    def register_or_update(
        self,
        name: str,
        description: str,
        code: str,
        user_id: int | None = None,
        description_zh: str | None = None,
        tool_type: str = "atomic",
    ) -> Tool:
        """Register a new tool or update an existing one."""
        existing = self.get_by_name(name)
        if existing:
            existing.code = code
            existing.description = description
            if description_zh is not None:
                existing.description_zh = description_zh
            if tool_type:
                existing.tool_type = tool_type
            existing.version += 1
            self.db.commit()
            self.db.refresh(existing)
            self.save_tool_file(name, code)
            return existing
        else:
            tool = self.create_tool(
                ToolCreate(
                    name=name,
                    description=description,
                    description_zh=description_zh,
                    code=code,
                    tool_type=tool_type,
                ),
                user_id=user_id,
            )
            self.save_tool_file(name, code)
            return tool

    # ── Version Management ──────────────────────────────────────────────

    def get_tool_versions(self, tool_id: int) -> list[ToolVersion]:
        """Get version history for a tool, ordered by version descending."""
        return (
            self.db.query(ToolVersion)
            .filter(ToolVersion.tool_id == tool_id)
            .order_by(ToolVersion.version.desc())
            .all()
        )

    def save_version_snapshot(
        self,
        tool_id: int,
        change_summary: str | None = None,
        created_by: int | None = None,
    ) -> ToolVersion:
        """Save a version snapshot of the current tool state."""
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")

        version = ToolVersion(
            tool_id=tool.id,
            version=tool.version,
            code=tool.code,
            description=tool.description,
            description_zh=tool.description_zh,
            change_summary=change_summary,
            created_by=created_by,
        )
        self.db.add(version)
        self.db.flush()
        return version

    def rollback_version(self, tool_id: int, target_version: int) -> Tool:
        """Rollback a tool to a specific version."""
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")

        target = (
            self.db.query(ToolVersion)
            .filter(ToolVersion.tool_id == tool_id, ToolVersion.version == target_version)
            .first()
        )
        if not target:
            raise HTTPException(status_code=404, detail=f"Version {target_version} not found")

        # Save current state as backup before rollback
        self.save_version_snapshot(
            tool_id,
            change_summary=f"Backup before rollback to v{target_version}",
        )

        # Restore tool fields from target version
        tool.code = target.code or ""
        tool.description = target.description or tool.description
        tool.description_zh = target.description_zh

        tool.version += 1
        self.db.commit()
        self.db.refresh(tool)
        return tool
