"""
Coalition engine (§4-C): deterministic user ↔ document matching via shared tags.

Uses a single aggregation on ``users`` — no LLM. Document tags (typically ``ai_tags``)
are flattened in Python; each user's ``parsed_profile`` is flattened in the database
with ``$objectToArray`` + ``$reduce``, then ``$setIntersection`` detects any overlap.
"""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.collections import CollectionName
from app.models.user import TagDict
from app.services.tag_utils import flatten_tag_dict


def _coerce_ai_tags(raw: Any) -> TagDict:
    if not isinstance(raw, dict):
        return {}
    out: TagDict = {}
    for k, v in raw.items():
        key = str(k)
        if isinstance(v, list):
            out[key] = [str(x) for x in v]
        else:
            out[key] = [str(v)]
    return out


def build_users_matching_tags_pipeline(document_tag_list: list[str]) -> list[dict[str, Any]]:
    """
    Pipeline stages: compute per-user flattened tags, keep users with non-empty
    intersection against ``document_tag_list``.
    """
    return [
        {
            "$addFields": {
                "user_tag_list": {
                    "$reduce": {
                        "input": {"$objectToArray": {"$ifNull": ["$parsed_profile", {}]}},
                        "initialValue": [],
                        "in": {"$concatArrays": ["$$value", "$$this.v"]},
                    }
                }
            }
        },
        {
            "$match": {
                "$expr": {
                    "$gt": [
                        {"$size": {"$setIntersection": ["$user_tag_list", document_tag_list]}},
                        0,
                    ]
                }
            }
        },
        {"$project": {"user_tag_list": 0}},
    ]


async def find_users_matching_document_tags(
    db: AsyncIOMotorDatabase,
    *,
    document_tags: TagDict,
) -> list[dict[str, Any]]:
    """
    Return raw user documents whose flattened ``parsed_profile`` tags intersect
    any tag from ``document_tags`` (e.g. a document's ``ai_tags``).
    """
    tag_list = flatten_tag_dict(document_tags)
    if not tag_list:
        return []

    coll = db[CollectionName.USERS]
    pipeline = build_users_matching_tags_pipeline(tag_list)
    cursor = coll.aggregate(pipeline)
    return [doc async for doc in cursor]


async def find_users_for_document(
    db: AsyncIOMotorDatabase,
    *,
    document: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convenience: read ``ai_tags`` from a Mongo document and run the matcher."""
    return await find_users_matching_document_tags(
        db,
        document_tags=_coerce_ai_tags(document.get("ai_tags")),
    )
