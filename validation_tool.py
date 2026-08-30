"""Step 5 — normalize the Evaluation Agent's parsed (possibly malformed) output.

Produces exactly one trustworthy `CriterionResult` per active criterion in the
run's frozen snapshot, plus a flat list of human-readable warnings. All business
rules for "what counts as missing / unknown / out-of-range" live here so the
scoring layer can assume clean input.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from models import Criterion, CriterionResult, LLMEvaluationOutput

_BLANK_PLACEHOLDER = "Not provided"

# Documented assumption (README): a fully unparseable / non-JSON LLM response is
# not a fatal error for the supplier — every active criterion is defaulted to 0
# and the supplier still appears (scored, not failed). "failed" is reserved for
# PDF-extraction / unrecoverable API errors, handled in the orchestrator.
MALFORMED_POLICY_WARNING = (
    "LLM response was unparseable; applied 'malformed response' policy — "
    "all active criteria defaulted to score 0"
)


def _default_all_to_zero(snapshot: List[Criterion]) -> List[CriterionResult]:
    return [
        CriterionResult(
            criterion_id=c.criterion_id,
            score=0.0,
            max_score=c.max_score,
            justification=_BLANK_PLACEHOLDER,
            evidence=_BLANK_PLACEHOLDER,
        )
        for c in snapshot
    ]


def normalize_llm_output(
    raw: Optional[LLMEvaluationOutput],
    snapshot: List[Criterion],
    *,
    malformed: bool = False,
) -> Tuple[List[CriterionResult], List[str]]:
    """Return (one result per active criterion, warnings).

    `malformed=True` (or `raw is None`) short-circuits to the malformed-response
    policy: all criteria defaulted to 0.
    """
    warnings: List[str] = []

    if malformed or raw is None:
        return _default_all_to_zero(snapshot), [MALFORMED_POLICY_WARNING]

    by_id: Dict[int, Criterion] = {c.criterion_id: c for c in snapshot}
    resolved: Dict[int, CriterionResult] = {}

    for entry in raw.criteria:
        # 1. Discard, don't guess — an entry with no criterion_id can't be
        #    attributed to any criterion.
        if entry.criterion_id is None:
            warnings.append(
                "LLM returned a criterion result with no criterion_id — discarded"
            )
            continue

        # 2. Unknown id — not in the frozen snapshot.
        crit = by_id.get(entry.criterion_id)
        if crit is None:
            warnings.append(
                f"unknown criterion_id {entry.criterion_id} in LLM response — ignored"
            )
            continue

        if entry.criterion_id in resolved:
            warnings.append(
                f"duplicate result for criterion_id {entry.criterion_id} — kept the first"
            )
            continue

        # 3. Clip to [0, max_score]; the snapshot's max_score always wins over
        #    whatever the LLM echoed back.
        score = float(entry.score)
        if score < 0 or score > crit.max_score:
            clipped = min(max(score, 0.0), crit.max_score)
            warnings.append(
                f"criterion '{crit.name}' score {score} out of range "
                f"[0, {crit.max_score}] — clipped to {clipped}"
            )
            score = clipped

        justification = (entry.justification or "").strip()
        evidence = (entry.evidence or "").strip()
        if not justification:
            warnings.append(f"criterion '{crit.name}' had no justification — set to '{_BLANK_PLACEHOLDER}'")
            justification = _BLANK_PLACEHOLDER
        if not evidence:
            warnings.append(f"criterion '{crit.name}' had no evidence — set to '{_BLANK_PLACEHOLDER}'")
            evidence = _BLANK_PLACEHOLDER

        resolved[entry.criterion_id] = CriterionResult(
            criterion_id=entry.criterion_id,
            score=score,
            max_score=crit.max_score,
            justification=justification,
            evidence=evidence,
        )

    # 4. Only now — after discarding bad entries — decide what's genuinely missing.
    for c in snapshot:
        if c.criterion_id not in resolved:
            warnings.append(
                f"criterion '{c.name}' missing from LLM response — defaulted to 0"
            )
            resolved[c.criterion_id] = CriterionResult(
                criterion_id=c.criterion_id,
                score=0.0,
                max_score=c.max_score,
                justification=_BLANK_PLACEHOLDER,
                evidence=_BLANK_PLACEHOLDER,
            )

    ordered = [resolved[c.criterion_id] for c in snapshot]
    return ordered, warnings
