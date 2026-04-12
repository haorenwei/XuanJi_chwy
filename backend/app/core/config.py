from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "root"
    db_name: str = "xuanji"

    # AI - Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qingqi-qwen3.5:latest"

    # AI - Online LLM
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_api_base_url: str = ""
    llm_model_name: str = ""

    # AI - Intent Recognition LLM (晴)
    intent_llm_provider: str = ""
    intent_llm_api_key: str = ""
    intent_llm_api_base_url: str = ""
    intent_llm_model_name: str = ""

    # AI - Emotion LLM (焕)
    emotion_llm_provider: str = ""
    emotion_llm_api_key: str = ""
    emotion_llm_api_base_url: str = ""
    emotion_llm_model_name: str = ""

    # AI - Format LLM (遥)
    format_llm_provider: str = ""
    format_llm_api_key: str = ""
    format_llm_api_base_url: str = ""
    format_llm_model_name: str = ""

    # App
    secret_key: str = "xuanji-secret-key-change-in-production"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Sandbox
    sandbox_dir: str = "./sandbox"
    sandbox_timeout: int = 30

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            "?charset=utf8mb4"
        )

    @property
    def database_url_without_db(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}"
            "?charset=utf8mb4"
        )

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}


settings = Settings()
