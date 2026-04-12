from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.token_service import TokenService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token_service = TokenService(db)
    summary = token_service.get_usage_summary(current_user.id)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "today_tokens": summary["today_tokens"],
            "month_tokens": summary["month_tokens"],
            "total_tokens": summary["total_tokens"],
            "monthly_budget": summary["monthly_budget"],
        },
    }


@router.get("/token-by-role")
async def get_token_by_role(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token_service = TokenService(db)
    data = token_service.get_usage_by_role(current_user.id, days)
    return {"code": 200, "message": "success", "data": data}


@router.get("/token-daily")
async def get_token_daily(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token_service = TokenService(db)
    data = token_service.get_daily_usage(current_user.id, days)
    return {"code": 200, "message": "success", "data": data}


@router.get("/token-by-model")
async def get_token_by_model(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token_service = TokenService(db)
    data = token_service.get_usage_by_model(current_user.id, days)
    return {"code": 200, "message": "success", "data": data}
