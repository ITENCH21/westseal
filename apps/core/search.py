import re

from django.db.models import Case, IntegerField, Q, When


def _normalize_for_search(value: str) -> str:
    if not value:
        return ""
    text = value.lower().replace("\u00a0", " ").strip()
    text = text.replace("×", "x")
    text = re.sub(r",\s*,+", ",", text)
    # unify dimension separators between numbers: 10х20х3 -> 10x20x3
    text = re.sub(r"(?<=\d)\s*[xх]\s*(?=\d)", "x", text)
    text = re.sub(r"\s+", " ", text)
    return text


def seal_product_search(products_qs, q: str, *, max_candidates: int = 5000, min_candidates: int = 200, limit: int = 2000):
    """
    Returns queryset ordered by relevance.
    - Short/code queries (< 6 chars): strict icontains only — no fuzzy broadening.
    - Longer queries: partial icontains first, fuzzy ranking (RapidFuzz) if < min_candidates.
    """
    q = (q or "").strip()
    if not q:
        return products_qs

    q_norm = _normalize_for_search(q)
    if len(q_norm) < 3:
        return products_qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(attributes_text__icontains=q))

    icontains_q = Q(name__icontains=q) | Q(description__icontains=q) | Q(attributes_text__icontains=q)

    # For short codes (≤5 chars) — strict icontains only, ordered by name match first
    if len(q_norm) <= 5:
        name_match = Q(name__icontains=q)
        attr_match = Q(attributes_text__icontains=q)
        from django.db.models import Value
        order = Case(
            When(name_match, then=0),
            When(attr_match, then=1),
            default=2,
            output_field=IntegerField(),
        )
        return products_qs.filter(icontains_q).order_by(order, "name")

    candidates = list(
        products_qs.filter(icontains_q)
        .values("id", "name", "attributes_text")
        .order_by("id")[:max_candidates]
    )

    if len(candidates) < min_candidates:
        # broaden for typo search (still capped)
        candidates = list(products_qs.values("id", "name", "attributes_text").order_by("id")[:max_candidates])

    try:
        from rapidfuzz import fuzz  # type: ignore
    except Exception:
        return products_qs.filter(icontains_q)

    # Min score scales with query length: longer query → can be fuzzier
    min_score = max(72, 78 - len(q_norm))

    scored = []
    for item in candidates:
        hay = _normalize_for_search(f"{item.get('name') or ''} {item.get('attributes_text') or ''}")
        if not hay:
            continue
        score = fuzz.WRatio(q_norm, hay)
        if q_norm in hay:
            score = min(100, score + 10)
        if score >= min_score:
            scored.append((item["id"], score))

    if not scored:
        return products_qs.filter(icontains_q)

    scored.sort(key=lambda x: x[1], reverse=True)
    best_ids = [pid for pid, _ in scored[:limit]]
    order = Case(*[When(id=pid, then=pos) for pos, pid in enumerate(best_ids)], output_field=IntegerField())
    return products_qs.filter(id__in=best_ids).order_by(order)
