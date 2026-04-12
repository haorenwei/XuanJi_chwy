from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationResponse, MessageResponse
from app.schemas.emotion import EmotionRecordResponse
from app.schemas.identity import AIIdentityResponse, AIIdentityUpdate
from app.schemas.profile import UserProfileResponse
from app.services.conversation_service import ConversationService
from app.services.emotion_service import EmotionService
from app.services.identity_service import IdentityService
from app.services.profile_service import ProfileService
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ── Conversation endpoints ──────────────────────────────────────────

@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ConversationService(db)
    convs = service.list_conversations(current_user.id, page, limit)
    return convs


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    req: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ConversationService(db)
    conv = service.create_conversation(current_user.id, title=req.title)
    return conv


@router.get("/recent-messages", response_model=list[MessageResponse])
async def get_recent_messages(
    days: int = Query(3, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ConversationService(db)
    messages = service.get_recent_messages(current_user.id, days)
    return messages


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ConversationService(db)
    conv = service.get_conversation(conversation_id, current_user.id)
    if not conv:
        return []
    messages = service.get_messages(conversation_id, limit, before_id)
    return messages


# ── Emotion endpoints ───────────────────────────────────────────────

@router.get("/emotions/latest", response_model=EmotionRecordResponse | None)
async def get_latest_emotion(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EmotionService(db)
    record = service.get_latest_emotion(current_user.id)
    return record


@router.get("/emotions/history", response_model=list[EmotionRecordResponse])
async def get_emotion_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EmotionService(db)
    records = service.get_emotion_history(current_user.id, limit)
    return records


# ── User profile endpoints ──────────────────────────────────────────

@router.get("/profile", response_model=UserProfileResponse | None)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    profile = service.get_or_create_profile(current_user.id)
    return profile


# ── AI Identity endpoints ───────────────────────────────────────────

@router.get("/identities", response_model=list[AIIdentityResponse])
async def list_identities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = IdentityService(db)
    from app.services.identity_service import AI_REGISTRY
    identities = []
    for ai_name in AI_REGISTRY:
        identity = service.get_or_create_identity(current_user.id, ai_name)
        identities.append(identity)
    return identities


@router.get("/identities/{ai_name}", response_model=AIIdentityResponse)
async def get_identity(
    ai_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = IdentityService(db)
    identity = service.get_or_create_identity(current_user.id, ai_name)
    return identity


@router.put("/identities/{ai_name}")
async def update_identity(
    ai_name: str,
    req: AIIdentityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = IdentityService(db)
    results = {}
    for field, value in req.model_dump(exclude_unset=True).items():
        result = service.evolve_field(
            current_user.id, ai_name, field, reason="manual_update", new_value=value
        )
        results[field] = "updated" if result else "locked"
    return {"code": 200, "message": "ok", "data": results}


# ── Memory endpoints ────────────────────────────────────────────────

@router.get("/memories")
async def get_memories(
    query: str = "",
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    if query:
        memories = service.get_relevant_memories(current_user.id, query, limit)
    else:
        from sqlalchemy import desc
        from app.models.memory_summary import MemorySummary
        memories = (
            db.query(MemorySummary)
            .filter(MemorySummary.user_id == current_user.id)
            .order_by(desc(MemorySummary.period_start))
            .limit(limit)
            .all()
        )
    return [
        {
            "id": m.id,
            "period_type": m.period_type,
            "period_start": m.period_start.isoformat() if m.period_start else None,
            "period_end": m.period_end.isoformat() if m.period_end else None,
            "summary_text": m.summary_text,
            "key_emotions": m.key_emotions,
            "key_topics": m.key_topics,
            "important_events": m.important_events,
            "source_message_count": m.source_message_count,
        }
        for m in memories
    ]
