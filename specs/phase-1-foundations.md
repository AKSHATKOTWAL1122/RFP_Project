# Phase 1 — Foundations

Files: `database.py`, `models.py`, `.env.example`, `requirements.txt`, `.gitignore`

## Scope

Establish the persistence layer and shared data models everything else builds on. No UI, no LLM calls in this phase.

## Deliverables

- `.env.example` with `GEMINI_API_KEY=`
- `requirements.txt`: `streamlit`, `pymupdf`, `langchain`, `langchain-google-genai`, `pydantic`, `python-dotenv` — **unpinned for now**; pin to verified versions in Phase 6
- `.gitignore`: `.env`, `data/rfp_eval.db`, `__pycache__`
- SQLite schema in `database.py`, exactly:
  - `evaluation_criteria(criterion_id, name, description, weight, max_score, is_active)`
  - `rfp_runs(rfp_run_id, created_at, status)`
  - `supplier_results(rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json)` — `absolute_score`, `ppi`, `final_rank` must be **nullable**, to support the failed-supplier policy (Phase 4)
- Seed data: 5 criteria — Technical Capability 30, Implementation Plan 20, Commercial Value 20, Security & Compliance 20, Support & Experience 10 (sums to 100), all `is_active=1`. Use the brief's **exact inspection-guidance wording** as each criterion's `description`:
  - Technical Capability → "Architecture, integrations, scalability, technical fit"
  - Implementation Plan → "Timeline, milestones, staffing, risk plan"
  - Commercial Value → "Pricing clarity, total cost, assumptions"
  - Security & Compliance → "Controls, certifications, privacy, auditability"
  - Support & Experience → "Support model, similar projects, references"
- `init_schema()` and `seed_criteria()` in `database.py`, called idempotently both from Streamlit startup and from a `if __name__ == "__main__":` block, so `python database.py` runs standalone as the required DB creation/seed script
- Criteria CRUD in `database.py` — **only these three**:
  - `add_criterion`, `update_criterion`
  - `set_active` (activate/deactivate)
  - **No `delete_criterion`.** Criteria are never hard-deleted, per the brief's own language (activate/deactivate/change weights, not delete).
- `is_run_in_progress()` — checks `rfp_runs` for any row with `status="in_progress"`, used later to lock criteria editing during an active evaluation
- A named constant for the experience-rating scale (e.g. `EXPERIENCE_RATING_MIN = 0`, `EXPERIENCE_RATING_MAX = 5`) in `database.py` or `models.py` — documented as an explicit assumption (the brief specifies the field exists, not its range), to be called out in the README's Assumptions section later
- Pydantic models in `models.py`: `Criterion`, `CriterionResult`, `LLMEvaluationOutput`, `SupplierScore`, `RankedSupplier`
  - `SupplierScore` and `RankedSupplier` must embed the full frozen `Criterion` snapshot used for that supplier's run (id, name, description, weight, max_score) — not just criterion IDs, so past runs stay self-contained even if criteria are later edited or deactivated
  - `SupplierScore.absolute_score` / `RankedSupplier.ppi` / `RankedSupplier.final_rank` must be `Optional`, to represent a failed/excluded supplier

## Done-check

- `python database.py` run standalone creates and seeds the database from scratch
- `get_active_criteria()` returns 5 rows whose weights sum to 100, and whose `description` fields match the brief's exact inspection-guidance wording
- No `delete_criterion` function exists anywhere in `database.py`
