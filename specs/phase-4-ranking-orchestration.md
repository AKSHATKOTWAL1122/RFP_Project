# Phase 4 — Ranking & Orchestration

Files: `ranking.py`, `orchestrator.py`

## Scope

Turn scored suppliers into a deterministically ranked list, then wire the entire 10-step pipeline together as the single function the UI will call — with a frozen per-run criterion snapshot and a defined failed-supplier policy.

## Deliverables

### `ranking.py`

- Single stable composite sort key applied in one pass — not multiple sequential sorts:
  ```python
  def _sort_key(s):
      return (-s.ppi, s.submission_date, -s.experience_rating, s.supplier_name.lower())
  ```
- `1) Higher PPI first -> 2) Earlier submission date -> 3) Higher experience rating -> 4) Supplier name ascending`
- **Suppliers with `ppi is None` (failed evaluation) are excluded from this sort entirely** — not included and sorted-in as if they scored worst. They never receive a `final_rank`.
- Sort the remaining (successfully-evaluated) suppliers with Python's stable `sorted()`, then assign `final_rank` sequentially (1, 2, 3, ...) — gapless, no ties in the final rank.

### `orchestrator.py` — mapped 1:1 to the brief's step names

1. `run_setup()` — **Setup**: load active criteria (`database.get_active_criteria`)
2. *(Input is UI-side, Phase 5)*
3. `run_batch(supplier_meta)` — **Batch**: generate `rfp_run_id` (uuid4), `database.create_run(..., status="in_progress")`, and — critically — **load active criteria exactly once here and freeze them as this run's criterion snapshot**. This snapshot, not a fresh reload, is what every subsequent step (Evaluate, Validate, Score, Benchmark, Rank, Persist) uses for every supplier in the batch. This guarantees all suppliers in one run are evaluated under the same configuration, even if someone edits criteria mid-run (which is additionally blocked by `is_run_in_progress()` locking the Criteria screen).
4. `evaluate_supplier(...)` — **Evaluate**: per supplier — `document_tool.extract_text_from_pdf` → `evaluation_agent`'s chain, called with the frozen snapshot
5. `validation_tool.validate_and_normalize(...)` — **Validate**
6. `scoring.compute_absolute_score(...)` — **Score**
7. `scoring.compute_benchmarks(...)` + per-supplier gap/relative % — **Benchmark**
8. `ranking.rank_suppliers(...)` (after `scoring.compute_ppi(...)` per supplier) — **Rank**
9. `persist_run(...)` — **Persist**: `database.persist_supplier_results(...)`, embedding the frozen snapshot in each row's `result_json`
10. *(Present is UI-side, Phase 5)*

- `execute_full_pipeline(supplier_meta, uploaded_pdfs)` is the single entry point the UI calls on "Evaluate" — chains steps 1, 3-9.
- **Failed-supplier policy**: per-supplier failures (PDF extraction error, unrecoverable LLM error after retries) are caught inside the batch loop and recorded as a warning. That supplier is persisted with `absolute_score = NULL`, `ppi = NULL`, `final_rank = NULL`, and is **excluded from ranking** — never silently defaulted to a 0 score. The rest of the batch proceeds normally.
- The whole pipeline is wrapped in try/except/**finally**: the `finally` block guarantees `rfp_runs.status` is always set to `"completed"` or `"failed"` — an unhandled exception must never leave a run stuck at `"in_progress"` (which would permanently lock the Criteria screen in Phase 5).

## Done-check

- Fixture suppliers deliberately tied at each level (Edge Case Checklist items 8-10) resolve in the documented order, with `final_rank` a gapless 1..N sequence over the successfully-evaluated suppliers only
- A fixture supplier with a forced PDF-extraction failure (item 11) is persisted with NULL score/ppi/rank and excluded from the ranked list — verify it does not appear with `final_rank` set to anything
- A full pipeline run with a stubbed LLM call produces persisted, ranked rows in `supplier_results`, each embedding the frozen criterion snapshot
- Forcing an exception mid-pipeline (e.g. a broken DB write) still leaves `rfp_runs.status` as `"failed"`, never stuck at `"in_progress"`
- Verify two suppliers evaluated in the same run see identical criterion weights/descriptions even if `evaluation_criteria` is edited between their individual evaluations (proves the freeze-once behavior)
