from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.setting import UserSetting
from app.models.token_usage import TokenUsage


class TokenService:
    def __init__(self, db: Session):
        self.db = db

    def record_usage(
        self,
        user_id: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        model: str | None = None,
        role_name: str | None = None,
    ) -> TokenUsage:
        """Insert a token usage record."""
        record = TokenUsage(
            user_id=user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            role_name=role_name,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_usage_summary(self, user_id: int) -> dict:
        """Return usage summary: today_tokens, month_tokens, total_tokens, monthly_budget."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        today_tokens = (
            self.db.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0))
            .filter(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= today_start,
            )
            .scalar()
        )

        month_tokens = (
            self.db.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0))
            .filter(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= month_start,
            )
            .scalar()
        )

        total_tokens = (
            self.db.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0))
            .filter(TokenUsage.user_id == user_id)
            .scalar()
        )

        # Get monthly budget from UserSetting
        setting = (
            self.db.query(UserSetting)
            .filter(UserSetting.user_id == user_id)
            .first()
        )
        monthly_budget = (
            setting.token_monthly_budget if setting else None
        )

        return {
            "today_tokens": int(today_tokens),
            "month_tokens": int(month_tokens),
            "total_tokens": int(total_tokens),
            "monthly_budget": monthly_budget,
        }

    def check_budget(self, user_id: int) -> bool:
        """Check if monthly usage exceeds budget. Returns True if over budget."""
        summary = self.get_usage_summary(user_id)
        budget = summary["monthly_budget"]
        if budget is None:
            return False
        return summary["month_tokens"] >= budget

    def get_usage_by_role(self, user_id: int, days: int = 30) -> list[dict]:
        """Return token usage grouped by role_name and model for the last N days."""
        from datetime import timedelta
        now = datetime.now()
        start = now - timedelta(days=days)

        results = (
            self.db.query(
                TokenUsage.role_name,
                TokenUsage.model,
                func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.count(TokenUsage.id).label("call_count"),
            )
            .filter(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= start,
            )
            .group_by(TokenUsage.role_name, TokenUsage.model)
            .all()
        )

        return [
            {
                "role_name": r.role_name or "unknown",
                "model": r.model or "unknown",
                "prompt_tokens": int(r.prompt_tokens),
                "completion_tokens": int(r.completion_tokens),
                "total_tokens": int(r.total_tokens),
                "call_count": int(r.call_count),
            }
            for r in results
        ]

    def get_daily_usage(self, user_id: int, days: int = 30) -> list[dict]:
        """Return daily token usage grouped by role_name for the last N days."""
        from datetime import timedelta
        now = datetime.now()
        start = now - timedelta(days=days)
        results = (
            self.db.query(
                func.date(TokenUsage.created_at).label("date"),
                TokenUsage.role_name,
                func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
            )
            .filter(TokenUsage.user_id == user_id, TokenUsage.created_at >= start)
            .group_by(func.date(TokenUsage.created_at), TokenUsage.role_name)
            .order_by(func.date(TokenUsage.created_at))
            .all()
        )
        return [
            {
                "date": str(r.date),
                "role_name": r.role_name or "unknown",
                "prompt_tokens": int(r.prompt_tokens),
                "completion_tokens": int(r.completion_tokens),
                "total_tokens": int(r.total_tokens),
            }
            for r in results
        ]

    def get_usage_by_model(self, user_id: int, days: int = 30) -> list[dict]:
        """Return token usage grouped by model for the last N days."""
        from datetime import timedelta
        now = datetime.now()
        start = now - timedelta(days=days)
        results = (
            self.db.query(
                TokenUsage.model,
                func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.count(TokenUsage.id).label("call_count"),
            )
            .filter(TokenUsage.user_id == user_id, TokenUsage.created_at >= start)
            .group_by(TokenUsage.model)
            .all()
        )
        return [
            {
                "model": r.model or "unknown",
                "prompt_tokens": int(r.prompt_tokens),
                "completion_tokens": int(r.completion_tokens),
                "total_tokens": int(r.total_tokens),
                "call_count": int(r.call_count),
            }
            for r in results
        ]
