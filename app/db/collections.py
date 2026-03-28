from enum import StrEnum


class CollectionName(StrEnum):
    """MongoDB collection names (snake_case, plural resources)."""

    USERS = "users"
    DOCUMENTS = "documents"
    ALERTS = "alerts"
