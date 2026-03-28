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


def check_tags_overlap(tags_a: list[str], tags_b: list[str]) -> bool:
    """
    Check if any token in tags_a generously overlaps (substring) with any token in tags_b.
    This resolves strict taxonomy constraints across unstructured pre-parsed JSON seeds.
    """
    lower_a = [str(a).lower() for a in tags_a]
    lower_b = [str(b).lower() for b in tags_b]
    
    for ta in lower_a:
        for tb in lower_b:
            if ta in tb or tb in ta:
                return True
    return False
