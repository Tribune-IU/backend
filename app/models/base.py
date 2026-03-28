from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MongoDocumentBase(BaseModel):
    """Shared rules for BSON-backed documents (snake_case fields, AIP-friendly JSON)."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str | None = Field(
        default=None,
        alias="_id",
        description="Hex string of MongoDB ObjectId; omitted on create.",
    )

    @field_validator("id", mode="before")
    @classmethod
    def coerce_object_id(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError("id must be a valid MongoDB ObjectId string")
