import re

from app.models.user import TagDict

# Mock “AI parsing”: keyword buckets until Manish’s pipeline replaces this.
_KEYWORD_TAGS: list[tuple[str, str]] = [
    ("housing", "housing"),
    ("rent", "housing"),
    ("landlord", "housing"),
    ("school", "education"),
    ("education", "education"),
    ("student", "education"),
    ("traffic", "transportation"),
    ("road", "transportation"),
    ("camera", "surveillance"),
    ("police", "public_safety"),
    ("park", "parks"),
    ("zoning", "zoning"),
    ("development", "development"),
    ("hopewell", "hopewell"),
    ("flock", "flock_cameras"),
]


def mock_parsed_profile_from_bio(bio: str) -> TagDict:
    text = bio.lower()
    tokens = set(re.findall(r"[a-z][a-z\-]{2,}", text))
    topics: list[str] = []
    matched_terms: list[str] = []

    for keyword, tag in _KEYWORD_TAGS:
        if keyword in text or keyword in tokens:
            matched_terms.append(keyword)
            if tag not in topics:
                topics.append(tag)

    if not topics:
        topics = ["general_interest"]

    return {"topics": topics, "matched_terms": sorted(set(matched_terms))}
