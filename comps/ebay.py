from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests


@dataclass(frozen=True)
class EbaySoldComp:
    title: str
    price: float
    currency: str
    url: str


def _is_sandbox_app_id(app_id: str) -> bool:
    # eBay sandbox keys commonly include "-SBX-" (like the one you pasted).
    return "-SBX-" in (app_id or "").upper()


def _finding_api_base_url(app_id: str) -> str:
    if _is_sandbox_app_id(app_id):
        return "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
    return "https://svcs.ebay.com/services/search/FindingService/v1"


def find_sold_items(
    *,
    app_id: str,
    keywords: str,
    entries_per_page: int = 20,
) -> List[EbaySoldComp]:
    """
    Uses eBay Finding API (findCompletedItems) with SoldItemsOnly=true.

    Requires EBAY_APP_ID (aka AppID / Client ID) from eBay developer portal.
    """
    if not app_id:
        return []

    params = {
        "OPERATION-NAME": "findCompletedItems",
        "SERVICE-VERSION": "1.13.0",
        "SECURITY-APPNAME": app_id,
        "RESPONSE-DATA-FORMAT": "JSON",
        "REST-PAYLOAD": "true",
        "keywords": keywords,
        "paginationInput.entriesPerPage": str(max(1, min(entries_per_page, 100))),
        "itemFilter(0).name": "SoldItemsOnly",
        "itemFilter(0).value": "true",
        "itemFilter(1).name": "HideDuplicateItems",
        "itemFilter(1).value": "true",
    }

    try:
        resp = requests.get(
            _finding_api_base_url(app_id),
            params=params,
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # Don't crash the whole app if eBay is down / key is wrong.
        return []

    try:
        items = (
            data["findCompletedItemsResponse"][0]["searchResult"][0].get("item", [])
        )
    except Exception:
        return []

    out: List[EbaySoldComp] = []
    for it in items:
        try:
            title = (it.get("title") or [""])[0] if isinstance(it.get("title"), list) else (it.get("title") or "")
            view_url = (it.get("viewItemURL") or [""])[0] if isinstance(it.get("viewItemURL"), list) else (it.get("viewItemURL") or "")

            selling_status = it.get("sellingStatus", [{}])[0]
            current_price = selling_status.get("currentPrice", [{}])[0]
            value = current_price.get("__value__")
            currency = current_price.get("@currencyId") or ""
            if value is None:
                continue

            price = float(value)
            if not title or not view_url or not currency:
                continue

            out.append(EbaySoldComp(title=title, price=price, currency=currency, url=view_url))
        except Exception:
            continue

    return out

