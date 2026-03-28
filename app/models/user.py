from pydantic import Field

from app.models.base import MongoDocumentBase

TagDict = dict[str, list[str]]
"""Maps a category (e.g. topics, geography) to tag strings for matching."""


class UserDocument(MongoDocumentBase):
    """`users` collection: onboarding bio plus structured tags from profile parsing."""

    bio: str = Field(..., min_length=1, description="Plain-language self description from the user.")
    parsed_profile: TagDict = Field(
        default_factory=dict,
        description="Dictionary of tags by category; values are tag strings (coalition matcher flattens these).",
    )
