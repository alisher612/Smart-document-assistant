
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Smart Document Assistant API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"

    FRONTEND_ORIGIN: str = "http://localhost:5173"

    LOG_LEVEL: str = "INFO"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "smart_document_assistant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.FRONTEND_ORIGIN.split(",")
            if origin.strip()
        ]


settings = Settings()
