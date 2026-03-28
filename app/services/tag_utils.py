from collections.abc import Iterable, Mapping


def flatten_tag_dict(tags: Mapping[str, Iterable[str]]) -> list[str]:
    """
    Flatten category → tag lists into a de-duplicated ordered list (insertion order).
    Used for deterministic coalition matching against MongoDB.
    """
    seen: set[str] = set()
    out: list[str] = []
    for values in tags.values():
        for raw in values:
            t = str(raw).strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
    return out
