from pydantic import BaseModel, ConfigDict, Field
from typing import Any

class UserProfileData(BaseModel):
    location_zones: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)

class SaveProfileBody(BaseModel):
    user_id: str
    profile_data: UserProfileData

class AiTags(BaseModel):
    topics: list[str] = Field(default_factory=list)
    impact_radius: str = Field(default="")
    affected_groups: list[str] = Field(default_factory=list)

class DocumentMetadata(BaseModel):
    document_id: str = Field(default="")
    title: str = Field(default="Untitled")
    source: str = Field(default="unknown")
    date_filed: str = Field(default="")
    hearing_date: str = Field(default="")
    status: str = Field(default="")
    url: str = Field(default="")
    ai_tags: AiTags = Field(default_factory=AiTags)
    summary: str = Field(default="")

class SaveDocumentBody(BaseModel):
    packet_identifier: str
    item_identifier: str
    data: DocumentMetadata
