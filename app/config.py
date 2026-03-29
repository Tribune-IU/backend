from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mongodb_uri: str = Field(
        default="mongodb://localhost:27017", validation_alias="MONGO_SRV"
    )
    mongodb_db_name: str = "tribune"

    # Chat stub limits (document text is still bounded server-side).
    chat_max_message_chars: int = 4_000
    chat_max_context_chars: int = 12_000


settings = Settings()
