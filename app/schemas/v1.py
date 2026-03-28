from pydantic import BaseModel, ConfigDict, Field

from app.models.user import TagDict


class AuthResponse(BaseModel):
    user_id: str


class CreateUserBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bio: str = Field(..., min_length=1, max_length=50_000)


class SubmitBioBody(BaseModel):
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
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    source: str
    summary: str = ""
    ai_tags: TagDict


class DocumentDetail(BaseModel):
    """Full document, including raw_text, returned by GET /documents/{doc_id}."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    source: str
    summary: str = ""
    raw_text: str = ""
    ai_tags: TagDict


class ListDocumentsResponse(BaseModel):
    documents: list[DocumentListItem]


class ChatMessage(BaseModel):
    """A single turn in the conversation history."""

    role: str = Field(..., description="'user' or 'assistant'")
    text: str


class ChatBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior turns so the agent can follow the thread.",
    )
    user_id: str | None = Field(
        default=None,
        description="If provided, the resident's parsed profile is injected as context.",
    )


class ChatResponse(BaseModel):
    reply: str
    context_chars_used: int


class DraftCommentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Full Q&A conversation that shaped the resident's views.",
    )
    resident_context: str = Field(
        default="",
        description="Optional freeform resident context (neighborhood, role, etc.).",
    )
    user_id: str | None = Field(
        default=None,
        description="If provided, the resident's parsed profile is injected as context.",
    )


class DraftCommentResponse(BaseModel):
    draft_comment: str


class AlertResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    document_id: str
    ai_summary: str
    ai_draft_comment: str
    is_active: bool = True
    coalition_count: int = 0


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
