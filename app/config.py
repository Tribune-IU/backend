from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mongodb_uri: str = Field(
        default="mongodb://localhost:27017", validation_alias="MONGO_SRV"
    )
    mongodb_db_name: str = "tribune"

    #: Base URL of the deployed ADK ``api_server`` (no trailing slash required).
    agents_base_url: str = Field(
        default="http://127.0.0.1:8080",
        validation_alias=AliasChoices("AGENTS_BASE_URL", "ADK_SERVER_URL"),
    )

    # Chat stub limits (document text is still bounded server-side).
    chat_max_message_chars: int = 4_000
    chat_max_context_chars: int = 12_000


settings = Settings()
