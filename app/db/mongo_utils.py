from typing import Any

from bson import ObjectId


def mongo_doc_to_response(doc: dict[str, Any]) -> dict[str, Any]:
    """Expose Mongo `_id` as string `id` (snake_case JSON)."""
    out: dict[str, Any] = {}
    for key, value in doc.items():
        if key == "_id":
            out["id"] = str(value) if value is not None else None
        elif isinstance(value, ObjectId):
            out[key] = str(value)
        else:
            out[key] = value
    return out


def require_object_id(value: str, *, field_name: str = "id") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValueError(f"Invalid {field_name}")
    return ObjectId(value)
