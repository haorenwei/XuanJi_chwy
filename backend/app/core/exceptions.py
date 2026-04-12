class LLMConfigError(Exception):
    """AI 角色的 LLM 配置缺失或不完整时抛出。"""

    def __init__(self, role_name: str, missing_fields: list[str] | None = None):
        self.role_name = role_name
        self.missing_fields = missing_fields or []
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.missing_fields:
            fields = "、".join(self.missing_fields)
            return (
                f"AI配置缺失：{self.role_name} 未配置 {fields}。"
                f"请前往「记忆体」页面完成配置。"
            )
        return (
            f"AI配置缺失：{self.role_name} 未配置。"
            f"请前往「记忆体」页面完成配置。"
        )
