"""Steps 6 & 7 — deterministic scoring arithmetic.

Everything here is plain Python on the run's frozen criterion snapshot. The LLM
never touches these numbers. Operates only on the snapshot passed in — never
re-fetches live criteria from `database.py`.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from models import Criterion, CriterionResult, ScoredCriterion


def absolute_weighted_score(
    results: List[CriterionResult], snapshot: List[Criterion]
) -> float:
    """Σ over criteria of (criterion_score / max_score) * weight.

    With active weights summing to 100 and each ratio in [0, 1], the result is
    on a 0–100 scale.
    """
    by_id = {r.criterion_id: r for r in results}
    total = 0.0
    for c in snapshot:
        r = by_id.get(c.criterion_id)
        if r is None or c.max_score == 0:
            continue
        total += (r.score / c.max_score) * c.weight
    return total


def compute_benchmarks(
    per_supplier: Dict[str, List[CriterionResult]], snapshot: List[Criterion]
) -> Tuple[Dict[int, float], List[str]]:
    """Benchmark = highest score observed for each criterion across the run.

    Returns (benchmark_by_criterion_id, run_level_warnings). A criterion where
    every supplier scored 0 gets benchmark 0 and a warning explaining the
    zero-benchmark relative-% policy applied downstream.
    """
    benchmarks: Dict[int, float] = {}
    warnings: List[str] = []
    for c in snapshot:
        best = 0.0
        seen = False
        for results in per_supplier.values():
            for r in results:
                if r.criterion_id == c.criterion_id:
                    best = max(best, r.score)
                    seen = True
        benchmarks[c.criterion_id] = best
        if seen and best == 0:
            warnings.append(
                f"criterion '{c.name}': every supplier scored 0 — benchmark is 0, "
                "relative performance defined as 100% for all suppliers on this criterion"
            )
    return benchmarks, warnings


def _gap_and_relative(score: float, benchmark: float) -> Tuple[float, float]:
    # Zero-benchmark policy (documented assumption): avoid div-by-zero and a
    # misleading 0% — treat everyone as 100% of the (zero) benchmark.
    if benchmark == 0:
        return 0.0, 100.0
    return score - benchmark, (score / benchmark) * 100.0


def score_supplier(
    results: List[CriterionResult],
    snapshot: List[Criterion],
    benchmarks: Dict[int, float],
) -> Tuple[List[ScoredCriterion], float, float]:
    """Return (per-criterion scored breakdown, absolute_score, ppi).

    PPI = weighted average of each criterion's relative-performance %, weighted
    by that criterion's snapshot weight (normalized by /100).
    """
    by_id = {r.criterion_id: r for r in results}
    scored: List[ScoredCriterion] = []
    ppi_acc = 0.0
    weight_acc = 0.0

    for c in snapshot:
        r = by_id.get(c.criterion_id)
        score = r.score if r else 0.0
        benchmark = benchmarks.get(c.criterion_id, 0.0)
        gap, relative = _gap_and_relative(score, benchmark)
        scored.append(
            ScoredCriterion(
                criterion=c,
                score=score,
                benchmark=benchmark,
                gap=gap,
                relative_pct=relative,
                justification=r.justification if r else "Not provided",
                evidence=r.evidence if r else "Not provided",
            )
        )
        ppi_acc += relative * (c.weight / 100.0)
        weight_acc += c.weight / 100.0

    ppi = ppi_acc / weight_acc if weight_acc else 0.0
    absolute = absolute_weighted_score(results, snapshot)
    return scored, absolute, ppi
