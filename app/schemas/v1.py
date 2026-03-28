from pydantic import BaseModel, ConfigDict, Field

from app.models.user import TagDict


class CreateUserBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bio: str = Field(..., min_length=1, max_length=50_000)


class UserResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    bio: str
    parsed_profile: TagDict


class CreateUserResponse(BaseModel):
    user: UserResource


class GetUserResponse(BaseModel):
    user: UserResource


class DocumentListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source: str
    ai_tags: TagDict


class ListDocumentsResponse(BaseModel):
    documents: list[DocumentListItem]


class ChatBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    context_chars_used: int


class AlertResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    document_id: str
    ai_summary: str
    ai_draft_comment: str
    is_active: bool = True


class ListAlertsResponse(BaseModel):
    alerts: list[AlertResource]


class SeedLoadStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upserted: int
    modified: int
    total: int
    files: int


class TriggerMonitorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    message: str
    requested_at: str
    seed: SeedLoadStats
