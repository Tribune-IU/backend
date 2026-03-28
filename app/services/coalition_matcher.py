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
    lower_doc_tags = [str(t).lower() for t in document_tag_list]
    return [
        {
            "$addFields": {
                "user_tag_list": {
                    "$map": {
                        "input": {
                            "$reduce": {
                                "input": {"$objectToArray": {"$ifNull": ["$parsed_profile", {}]}},
                                "initialValue": [],
                                "in": {"$concatArrays": ["$$value", "$$this.v"]},
                            }
                        },
                        "as": "tag",
                        "in": {"$toLower": "$$tag"}
                    }
                }
            }
        },
        {
            "$match": {
                "$expr": {
                    "$gt": [
                        {"$size": {"$setIntersection": ["$user_tag_list", lower_doc_tags]}},
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
    Return raw user documents whose flattened parsed_profile tags generously intersect
    any tag from document_tags (e.g. substring match) to accommodate unstructured seed data.
    """
    doc_tag_list = flatten_tag_dict(document_tags)
    if not doc_tag_list:
        return []

    from app.services.tag_utils import check_tags_overlap

    coll = db[CollectionName.USERS]
    cursor = coll.find({"parsed_profile": {"$exists": True}})
    
    matched_users = []
    async for u in cursor:
        profile = u.get("parsed_profile", {})
        user_tag_list = flatten_tag_dict(profile)
        
        if check_tags_overlap(user_tag_list, doc_tag_list):
            matched_users.append(u)
            
    return matched_users


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
