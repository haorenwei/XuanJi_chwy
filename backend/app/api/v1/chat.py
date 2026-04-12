import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.agent import Agent
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.setting_service import SettingService
from app.services.token_service import TokenService

router = APIRouter(prefix="/chat", tags=["chat"])


def _record_token_usage(db: Session, user_id: int, usage: dict | None = None, usages: list | None = None):
    """Helper to record token usage. Supports single usage or a list of usages."""
    token_service = TokenService(db)

    items = usages if usages else ([usage] if usage else [])
    for u in items:
        if not u:
            continue
        token_service.record_usage(
            user_id=user_id,
            prompt_tokens=u.get("prompt_tokens", 0),
            completion_tokens=u.get("completion_tokens", 0),
            total_tokens=u.get("total_tokens", 0),
            model=u.get("model"),
            role_name=u.get("role_name"),
        )


@router.post("/")
async def chat(
    req: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    setting_service = SettingService(db)
    user_setting = setting_service.get_user_setting(current_user.id)
    agent = Agent(db=db, user_id=current_user.id, user_setting=user_setting)

    # Get last user message
    user_message = ""
    for msg in reversed(req.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        return {"code": 400, "message": "No user message found", "data": None}

    if req.stream:
        async def generate():
            try:
                async for event in agent.process_message(
                    user_message,
                    working_dir=req.working_dir,
                    conversation_id=req.conversation_id,
                ):
                    # Check if client has disconnected
                    if await request.is_disconnected():
                        break
                    # Capture usage from the done event and record it
                    if event.get("type") == "done":
                        usages = event.get("usages") or []
                        if usages:
                            _record_token_usage(db, current_user.id, usages=usages)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except asyncio.CancelledError:
                logger.info("SSE 连接被中断")
            except Exception as e:
                logger.error(f"SSE 流处理异常: {e}", exc_info=True)
                try:
                    yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
                except Exception:
                    pass

        return StreamingResponse(generate(), media_type="text/event-stream")

    # Non-streaming: collect all message chunks
    result_text = ""
    last_usages = None
    async for event in agent.process_message(
        user_message,
        working_dir=req.working_dir,
        conversation_id=req.conversation_id,
    ):
        if event["type"] == "message":
            result_text += event["content"]
        if event.get("type") == "done":
            last_usages = event.get("usages")

    if last_usages:
        _record_token_usage(db, current_user.id, usages=last_usages)

    return {"code": 200, "message": "success", "data": {"content": result_text}}
