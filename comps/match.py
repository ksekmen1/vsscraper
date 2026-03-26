from __future__ import annotations

import re
from typing import Optional


_PRICE_LINE = re.compile(r"\b(?:EUR|USD|GBP|DKK|SEK|NOK|CHF|PLN|€|\$|£)\b", re.IGNORECASE)


def extract_model_from_vestiaire_title(title: str, brand: str) -> str:
    """
    Vestiaire card text tends to look like:
      BALENCIAGA
      Neo Classic leather crossbody bag
      5.753 DKK
      France

    We want the 'model line' (best-effort).
    """
    if not title:
        return ""

    lines = [ln.strip() for ln in title.splitlines() if ln.strip()]
    if not lines:
        return ""

    b = (brand or "").strip().lower()
    cleaned = []
    for ln in lines:
        if b and ln.lower() == b:
            continue
        if _PRICE_LINE.search(ln):
            continue
        # Drop single-country line if it's likely a location (last line often is)
        cleaned.append(ln)

    if not cleaned:
        # fallback: drop brand only
        cleaned = [ln for ln in lines if not (b and ln.lower() == b)]

    # Prefer the first descriptive line.
    return cleaned[0] if cleaned else ""


def build_ebay_keywords(brand: str, model: str) -> str:
    # Exact model match is difficult; we bias keywords toward brand + model phrase.
    # You can tighten later with quoting if needed: f'"{brand}" "{model}" bag'
    b = (brand or "").strip()
    m = (model or "").strip()
    parts = [p for p in [b, m, "bag"] if p]
    return " ".join(parts)

