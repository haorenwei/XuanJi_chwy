from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.setting import SettingResponse, SettingUpdate
from app.services.setting_service import SettingService
from app.services.token_service import TokenService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SettingService(db)
    setting = service.get_user_setting(current_user.id)
    return {
        "code": 200,
        "message": "success",
        "data": SettingResponse.model_validate(setting).model_dump() if setting else None,
    }


@router.put("/")
async def update_settings(
    data: SettingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SettingService(db)
    setting = service.upsert_setting(current_user.id, data)
    return {
        "code": 200,
        "message": "success",
        "data": SettingResponse.model_validate(setting).model_dump(),
    }


@router.get("/token-usage")
async def get_token_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_service = TokenService(db)
    summary = token_service.get_usage_summary(current_user.id)
    return {
        "code": 200,
        "message": "success",
        "data": summary,
    }
