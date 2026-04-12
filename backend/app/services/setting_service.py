from sqlalchemy.orm import Session

from app.models.setting import UserSetting
from app.schemas.setting import SettingUpdate


class SettingService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_setting(self, user_id: int) -> UserSetting | None:
        return (
            self.db.query(UserSetting)
            .filter(UserSetting.user_id == user_id)
            .first()
        )

    @staticmethod
    def _is_masked_key(key: str, value) -> bool:
        """检查是否为掩码占位值，避免覆盖真实密钥"""
        return key in ("llm_api_key", "tool_llm_api_key", "intent_llm_api_key", "emotion_llm_api_key", "format_llm_api_key") and isinstance(value, str) and "***" in value

    def upsert_setting(self, user_id: int, data: SettingUpdate) -> UserSetting:
        setting = self.get_user_setting(user_id)
        update_data = data.model_dump(exclude_unset=True)

        if setting is None:
            # 新建时也过滤掩码值
            clean_data = {k: v for k, v in update_data.items() if not self._is_masked_key(k, v)}
            setting = UserSetting(user_id=user_id, **clean_data)
            self.db.add(setting)
        else:
            for key, value in update_data.items():
                # 跳过掩码占位值，避免覆盖真实密钥
                if self._is_masked_key(key, value):
                    continue
                setattr(setting, key, value)

        self.db.commit()
        self.db.refresh(setting)
        return setting
