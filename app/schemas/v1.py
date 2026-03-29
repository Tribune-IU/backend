from pydantic import BaseModel, ConfigDict, Field

from app.models.user import TagDict


class AuthBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(default="", description="Accepted for UX; not validated or stored.")


class AuthResponse(BaseModel):
    user_id: str
    username: str


class CreateUserBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bio: str = Field(..., min_length=1, max_length=50_000)


class SubmitBioBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bio: str = Field(..., min_length=1, max_length=50_000)


class UserResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    username: str = ""
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
    hearing_date: str = ""
    ai_tags: TagDict


class DocumentDetail(BaseModel):
    """Full document, including raw_text, returned by GET /documents/{doc_id}."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    source: str
    summary: str = ""
    raw_text: str = ""
    hearing_date: str = ""
    pdf_url: str = ""
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


class RelevanceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="MongoDB ObjectId of the requesting user.")


class RelevanceResponse(BaseModel):
    relevance: str = Field(..., description="<100-word personalised explanation of why this document affects the user.")
    cached: bool = Field(default=False, description="True when returned from DB cache rather than regenerated.")


class SaveProgressBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    chat_history: list[ChatMessage] = Field(default_factory=list)
    draft_comment: str = Field(default="")
    draft_snapshot_length: int = Field(default=0)


class AlertResource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    document_id: str
    ai_summary: str
    ai_draft_comment: str
    is_active: bool = True
    coalition_count: int = 0
    # Persisted session state
    why_it_affects_me: str = ""
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    draft_comment: str = ""
    draft_snapshot_length: int = 0


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
