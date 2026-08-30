# Phase 5 — Streamlit UI

File: `streamlit_app.py`

## Scope

Wire the pipeline built in Phases 1-4 into the 5 required screens. Get the required workflow fully correct first; the what-if re-ranking enhancement is optional and comes last, only if time remains.

## Deliverables

### 1. Criteria (display + management)

- Table of existing criteria: name, description, weight, max_score, active toggle
- Inline edit + an "Add criterion" form, backed by `database.add_criterion` / `update_criterion`
- **Deactivate only** — a toggle calling `database.set_active`. **No delete button anywhere in this screen.**
- Running weight-total shown live; **Save disabled + error shown until active weights sum to exactly 100**
- Entire screen (add/edit/toggle/save) disabled with an explanatory message whenever `database.is_run_in_progress()` is true
- Changes only affect runs evaluated after the save — never retroactive (guaranteed by the frozen snapshot each run stores)

### 2. Supplier input

- `st.file_uploader(accept_multiple_files=True)` for supplier PDFs
- Per-supplier metadata form: name, `st.date_input` submission date, `st.number_input` experience rating bounded to the documented `EXPERIENCE_RATING_MIN/MAX` constant
- Validation with inline `st.error`: supplier name required and non-empty, no duplicate names within the same batch, submission date required, experience rating within the documented range
- "Evaluate" button disabled until validation passes; on click, calls `orchestrator.execute_full_pipeline(...)` with a spinner

### 3. Leaderboard

- Rank, supplier, absolute score, PPI, submission date, experience rating — as a plain list-of-dicts table, gapless 1..N rank
- Any supplier excluded from ranking (failed PDF/LLM evaluation) is shown **separately**, below or beside the ranked table, with an "Evaluation failed" badge and the recorded warning — never merged into the ranked table with a fabricated rank or score
- **(Optional, build last)** What-if re-ranking: a slider per criterion, seeded from that run's own stored criterion snapshot, auto-normalized live to 100. Moving a slider recomputes `scoring`/`ranking` in memory only, against that run's stored per-criterion scores — no LLM call, no DB write. "Reset to official weights" restores the persisted ranking. Clearly labeled as hypothetical, visually distinct from the official result.

### 4. Detailed scorecard

- Supplier selector (`st.selectbox`) — include both ranked and failed suppliers, with failed ones clearly marked
- Per criterion: score, benchmark, gap, relative %, weight, evidence, justification (evidence/justification in an `st.expander` per row)

### 5. Run details

- `rfp_run_id`, run status
- Aggregated warnings list (validation warnings + any per-supplier failures)
- Tie-break explanation: each ranked supplier's sort-key tuple `(ppi, submission_date, experience_rating, name)`
- `st.download_button` serving the full run as JSON (ranked suppliers + excluded suppliers + criterion snapshot + warnings)

## Done-check

- End-to-end manual run with verified PDFs: upload ≥4, fill metadata, Evaluate → leaderboard shows a gapless 1..N rank order obeying tie-break rules
- Scorecard shows evidence/gap/relative% correctly for each supplier/criterion
- Run Details JSON download matches what's persisted in the DB
- Criteria Save is blocked when weights don't sum to 100, and when a run is in progress
- No delete control exists anywhere on the Criteria screen
- A forced supplier failure appears as excluded/failed, not zero-ranked
- (If built) what-if sliders re-rank instantly with no DB writes
