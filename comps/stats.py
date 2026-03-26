from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class PriceStats:
    count: int
    median: Optional[float]
    p25: Optional[float]
    p75: Optional[float]


def _percentile(sorted_values: List[float], p: float) -> Optional[float]:
    if not sorted_values:
        return None
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]

    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def compute_price_stats(values: Iterable[float]) -> PriceStats:
    v = sorted([x for x in values if x is not None])
    if not v:
        return PriceStats(count=0, median=None, p25=None, p75=None)
    return PriceStats(
        count=len(v),
        median=_percentile(v, 50),
        p25=_percentile(v, 25),
        p75=_percentile(v, 75),
    )

