from typing import ClassVar, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LogLevels = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App path settings
    API_ROOT_PATH: str = Field("/api", description="Базовый путь приложения (FastAPI root_path)")

    # Logging settings
    LOG_LEVEL: LogLevels = Field("INFO", description="Уровень логирования")

    # Telegram formatting settings
    TELEGRAM_MAX_MESSAGE_LENGTH: int = Field(4096, ge=1, description="Максимальная длина сообщения Telegram")

    @field_validator("API_ROOT_PATH", mode="before")
    @classmethod
    def _parse_api_root_path(cls, v):
        if v is None:
            return "/api"
        if not isinstance(v, str):
            return v

        normalized = v.strip()
        if (normalized.startswith('"') and normalized.endswith('"')) or (
            normalized.startswith("'") and normalized.endswith("'")
        ):
            normalized = normalized[1:-1].strip()

        if normalized in ("", "/"):
            return ""

        if not normalized.startswith("/"):
            normalized = "/" + normalized

        return normalized.rstrip("/")


settings = Settings()
