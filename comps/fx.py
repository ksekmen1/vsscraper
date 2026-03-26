from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import requests


@dataclass(frozen=True)
class FxQuote:
    rate: float
    from_ccy: str
    to_ccy: str


_CACHE: Dict[Tuple[str, str], FxQuote] = {}


def get_fx_rate(from_ccy: str, to_ccy: str) -> Optional[FxQuote]:
    f = from_ccy.upper().strip()
    t = to_ccy.upper().strip()
    if not f or not t:
        return None
    if f == t:
        return FxQuote(rate=1.0, from_ccy=f, to_ccy=t)

    key = (f, t)
    if key in _CACHE:
        return _CACHE[key]

    # Frankfurter is a free, no-key FX API (ECB-based).
    resp = requests.get(
        "https://api.frankfurter.app/latest",
        params={"from": f, "to": t},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    rate = float(data["rates"][t])
    quote = FxQuote(rate=rate, from_ccy=f, to_ccy=t)
    _CACHE[key] = quote
    return quote


def convert(amount: float, from_ccy: str, to_ccy: str) -> Optional[float]:
    quote = get_fx_rate(from_ccy, to_ccy)
    if not quote:
        return None
    return amount * quote.rate

