from __future__ import annotations

import os
from typing import Dict, List, Optional

from .ebay import find_sold_items
from .fx import convert
from .match import build_ebay_keywords, extract_model_from_vestiaire_title
from .stats import compute_price_stats


def _fmt_dkk(value: Optional[float]) -> str:
    if value is None:
        return ""
    # Danish format is often 12.345, but keep it simple for MVP.
    return f"{value:,.0f} DKK".replace(",", ".")


def enrich_with_ebay_sold_comps(
    vestiaire_items: List[Dict[str, str]],
    *,
    brand: str,
    target_currency: str = "DKK",
    per_item_limit: int = 15,
) -> List[Dict[str, str]]:
    """
    Mutates and returns vestiaire_items, adding:
      - model
      - ebay_comp_count
      - ebay_comp_median_dkk / p25 / p75
      - suggested_list_dkk / suggested_quick_dkk
    """
    app_id = os.getenv("EBAY_APP_ID", "").strip()
    if not app_id:
        for it in vestiaire_items:
            it["comp_note"] = "Set EBAY_APP_ID to enable sold comps"
        return vestiaire_items

    for it in vestiaire_items:
        model = extract_model_from_vestiaire_title(it.get("title", ""), brand=brand)
        it["model"] = model

        keywords = build_ebay_keywords(brand=brand, model=model)
        try:
            comps = find_sold_items(
                app_id=app_id, keywords=keywords, entries_per_page=per_item_limit
            )
        except Exception:
            comps = []

        comp_prices_dkk: List[float] = []
        for c in comps:
            val = convert(c.price, c.currency, target_currency)
            if val is not None:
                comp_prices_dkk.append(val)

        stats = compute_price_stats(comp_prices_dkk)
        it["ebay_comp_count"] = str(stats.count)
        it["ebay_comp_median_dkk"] = _fmt_dkk(stats.median)
        it["ebay_comp_p25_dkk"] = _fmt_dkk(stats.p25)
        it["ebay_comp_p75_dkk"] = _fmt_dkk(stats.p75)

        # Suggestions for your own platform (simple heuristic).
        # - list price: ~10% above median
        # - quick sale: p25
        suggested_list = (stats.median * 1.10) if stats.median is not None else None
        suggested_quick = stats.p25

        it["suggested_list_dkk"] = _fmt_dkk(suggested_list)
        it["suggested_quick_dkk"] = _fmt_dkk(suggested_quick)

        if stats.count == 0:
            it["comp_note"] = "No sold comps found (or currency conversion failed)"
        else:
            it["comp_note"] = f"eBay sold comps using keywords: {keywords}"

    return vestiaire_items

