from typing import Any

from bson import ObjectId
from pydantic import Field, field_validator

from app.models.base import MongoDocumentBase


class AlertDocument(MongoDocumentBase):
    """`alerts` collection: join of a user and a document with generated copy."""

    user_id: str = Field(..., description="ObjectId string of the parent user.")
    document_id: str = Field(..., description="ObjectId string of the related document.")

    @field_validator("user_id", "document_id", mode="before")
    @classmethod
    def coerce_ref_ids(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError("user_id and document_id must be valid MongoDB ObjectId strings")

    ai_summary: str = Field(..., description="Short relevance summary for the user.")
    ai_draft_comment: str = Field(..., description="Draft public comment text.")
    is_active: bool = Field(
        default=True,
        description="False when the user dismisses or the alert is superseded.",
    )
