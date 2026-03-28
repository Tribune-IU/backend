"""
MongoDB document shapes for Tribune (snake_case, Pydantic v2).

Collections: ``users``, ``documents``, ``alerts`` — see ``app.db.collections.CollectionName``.
"""

from app.models.alert import AlertDocument
from app.models.document import DocumentRecord
from app.models.user import TagDict, UserDocument

__all__ = [
    "AlertDocument",
    "DocumentRecord",
    "TagDict",
    "UserDocument",
]
