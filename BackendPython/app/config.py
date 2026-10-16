from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_web_client_id: str
    jwt_secret: SecretStr
    cosmos_endpoint: str
    cosmos_key: SecretStr
    cosmos_database: str = "MensajesDB"
    cosmos_container: str = "mensajes"
    session_minutes: int = Field(default=60, ge=5, le=1440)
    release_sha: str = "local"

    @field_validator("jwt_secret")
    @classmethod
    def strong_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32 or value.get_secret_value().startswith("REEMPLAZAR"):
            raise ValueError("JWT_SECRET debe contener al menos 32 caracteres aleatorios")
        return value

    @field_validator("google_web_client_id")
    @classmethod
    def google_client(cls, value: str) -> str:
        if not value.endswith(".apps.googleusercontent.com") or "REEMPLAZAR" in value:
            raise ValueError("GOOGLE_WEB_CLIENT_ID debe ser el cliente OAuth de tipo Web")
        return value

    @field_validator("cosmos_endpoint")
    @classmethod
    def secure_endpoint(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("COSMOS_ENDPOINT debe usar HTTPS")
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
