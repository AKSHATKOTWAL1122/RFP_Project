"""Step 8 — deterministic tie-break ranking.

The LLM never influences rank. Ordering is a single stable composite sort key,
applied in one pass:

    1) higher PPI first
    2) then earlier submission date
    3) then higher experience rating
    4) then supplier name ascending (case-insensitive)

Suppliers whose evaluation failed (`ppi is None`) are excluded from the sort
entirely — they are never sorted in as if they scored worst, and never receive a
`final_rank`.
"""
from __future__ import annotations

from typing import List

from models import RankedSupplier, SupplierScore


def _sort_key(s: SupplierScore):
    return (-s.ppi, s.submission_date, -s.experience_rating, s.supplier_name.lower())


def rank_suppliers(suppliers: List[SupplierScore]) -> List[RankedSupplier]:
    ranked_ok = sorted(
        (s for s in suppliers if s.ppi is not None and not s.failed),
        key=_sort_key,
    )
    excluded = [s for s in suppliers if s.ppi is None or s.failed]

    out: List[RankedSupplier] = []
    for i, s in enumerate(ranked_ok, start=1):
        out.append(RankedSupplier(supplier_score=s, ppi=s.ppi, final_rank=i))
    for s in excluded:
        out.append(RankedSupplier(supplier_score=s, ppi=None, final_rank=None))
    return out
