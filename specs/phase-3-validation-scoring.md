# Phase 3 — Validation & Scoring

Files: `validation_tool.py`, `scoring.py`

## Scope

Turn a raw (possibly malformed) LLM output into a normalized, trustworthy set of per-criterion results, then compute the deterministic scoring formulas on top of it. No ranking yet (that's Phase 4).

## Deliverables

### `validation_tool.py` — normalization, in this exact order

1. **Discard, don't guess.** Any criterion-result entry with a missing or null `criterion_id` cannot be safely attributed to any criterion — discard it with a warning. Never invent an ID or default it to some criterion's score.
2. Any entry whose `criterion_id` isn't in the run's active criterion snapshot → discard + warning ("unknown criterion_id ignored").
3. For the remaining valid entries: clip out-of-range scores to `[0, max_score]` (warn if clipped). The DB's `max_score` (from the frozen snapshot) always overrides whatever the LLM echoed back.
4. **After** steps 1-3, compare the covered `criterion_id`s against the full active snapshot. Any active criterion still missing a result at this point → default to `score=0` + warning ("criterion X missing from LLM response, defaulted to 0"). This is the correct way to detect "missing" — never conflate a malformed/unattributable entry with a genuinely missing criterion.
5. Fully unparseable/non-JSON response → skip straight to defaulting **all** active criteria to 0, with a single warning explicitly noting this is the documented "malformed response" policy (an assumption — flagged for the README, not presented as a brief requirement).
6. Blank `justification`/`evidence` → defaulted to `"Not provided"` + warning.
7. All warnings accumulate into a `list[str]` attached to that supplier's result.

### `scoring.py` — formulas

- **Absolute weighted score** = Σ over criteria of `(criterion_score / max_score) * weight`
- **Criterion benchmark** = highest valid score observed for that criterion across all suppliers in the run
- **Criterion gap** = `supplier_score - benchmark_score` (zero for the benchmark leader, negative otherwise)
- **Relative performance %** = `(supplier_score / benchmark_score) * 100`
  - **Zero-benchmark policy (documented assumption)**: if every supplier scored 0 on a criterion (`benchmark_score == 0`), relative % is defined as **100 for all suppliers** on that criterion — avoids division by zero, avoids a misleading artificial 0%. Emit a run-level warning explaining this.
- **Peer Performance Index (PPI)** = weighted average of each criterion's relative-performance %, weighted by that criterion's weight from the run's frozen snapshot (weights normalized by dividing by 100 internally)
- All of the above operate on the criterion snapshot embedded in each `SupplierScore` — never re-fetch live criteria from `database.py` for this.

## Done-check

Hand-computed fixture values (fixed sample criteria + scores worked out on paper) match the function output exactly, covering Edge Case Checklist items 2 (missing criterion), 3 (out-of-range), 4 (malformed JSON), 5 (unknown criterion_id), 6 (entry with no criterion_id), and 7 (zero benchmark).
