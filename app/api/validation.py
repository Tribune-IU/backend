from bson import ObjectId

from app.api.errors import ApiError


def parse_object_id(value: str, *, field: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ApiError(
            http_status=400,
            status="INVALID_ARGUMENT",
            message=f"Invalid {field}.",
        )
    return ObjectId(value)
