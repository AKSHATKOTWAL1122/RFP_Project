# CLAUDE.md

## Project

Agentic RFP Evaluation and Supplier Ranking — a Streamlit app that reads supplier RFP PDFs, scores them against configurable weighted criteria using an LLM, then applies deterministic Python arithmetic to benchmark, rank, and present an explainable supplier leaderboard. Full assignment brief: `Agentic_RFP_Evaluation_Mini_Project.md`. Full implementation plan (with rationale and corrections applied after a brief-compliance review): `PLAN.md`.

## Tech Stack

- **UI**: Streamlit
- **DB**: SQLite via stdlib `sqlite3` (no ORM)
- **LLM**: Gemini 2.5 Flash, called through **LangChain** (`langchain-google-genai`'s `ChatGoogleGenerativeAI`) — never the raw `google-genai` SDK
- **Structured output**: `ChatPromptTemplate` + `PydanticOutputParser`
- **Validation/schema**: Pydantic
- **PDF extraction**: PyMuPDF only (no pypdf fallback)
- **Tables in UI**: plain lists/dicts into `st.dataframe`/`st.table` — no pandas
- **Dependency pinning**: deferred until after local verification (Phase 6) — don't guess versions upfront

## File Map

Each file maps to exactly one of the brief's named components/steps.

| File | Brief step(s) | Responsibility |
|---|---|---|
| `streamlit_app.py` | 2 (Input), 10 (Present) | All UI: Criteria (display+management), Supplier input, Leaderboard, Detailed scorecard, Run details |
| `orchestrator.py` | 1, 3-9 | Controls the pipeline; `execute_full_pipeline()`; freezes the run's criterion snapshot once at Batch time |
| `database.py` | 1 (load), 9 (persist) | Schema DDL, seed data, criteria CRUD (add/update/set_active — **no delete**), run/result persistence, run-lock check. Also the standalone DB creation/seed script (`python database.py`) |
| `document_tool.py` | 4 | PDF text extraction only |
| `evaluation_agent.py` | 4 | LangChain prompt/chain/LLM call only |
| `validation_tool.py` | 5 | Normalization of the LLM's parsed output |
| `scoring.py` | 6, 7 | Absolute score, benchmark, gap, relative %, PPI |
| `ranking.py` | 8 | Tie-break sort + sequential rank assignment |
| `models.py` | — | Shared Pydantic models |

## Hard Constraints

- The LLM may judge proposal content, but must never decide final arithmetic, benchmarks, tie-breaks, or rank — that's all deterministic Python in `scoring.py`/`ranking.py`.
- Tie-break order is fixed, implemented as a single stable composite sort key: `(-ppi, submission_date, -experience_rating, name.lower())`.
- API keys only via env var / `st.secrets` — never hardcoded, never committed.
- **Criteria are never hard-deleted** — only `add_criterion`, `update_criterion`, `set_active` (activate/deactivate) exist. There is no `delete_criterion`.
- **The run's criterion snapshot is taken exactly once, at Batch time**, and reused for every supplier evaluated in that run. Never reload/re-fetch criteria per supplier mid-run — that would let suppliers in the same run be scored under different configurations. Criteria editing is locked (`is_run_in_progress()`) for the run's duration to make this safe.
- Each persisted run stores its own frozen criterion snapshot inside `result_json` — a design decision for historical reproducibility, not a brief requirement. Never re-derive a past run's criteria by joining to the live `evaluation_criteria` table.
- **Failed suppliers** (PDF extraction failure, unrecoverable LLM error) are persisted with `absolute_score/ppi/final_rank = NULL` and a warning, and are **excluded from ranking** — never silently scored as 0.
- A criterion-result entry with a missing/unknown `criterion_id` is discarded with a warning — never guessed or reattributed.
- The experience-rating scale is a named, documented constant (not a silent assumption) — flag it in README's Assumptions.
- Active criteria weights must sum to exactly 100% before any save is allowed in the Criteria screen.
- Comments are welcome where a rule isn't self-evident (zero-benchmark policy, normalization policy, tie-break order, snapshot rationale) — kept minimal elsewhere. Not banned.

## Development Process

Spec-driven, 6 phases under `specs/`, done in order (1 → 6) since each depends on the previous. Read (and update if needed) a phase's spec file before writing its code.

The Edge Case Checklist (see `PLAN.md`) must be demonstrated as it lands each phase — via the module tests / done-checks in each phase spec.

| Phase | Spec file | Delivers |
|---|---|---|
| 1 | `specs/phase-1-foundations.md` | SQLite schema, seed data, criteria CRUD (no delete), Pydantic models |
| 2 | `specs/phase-2-extraction-llm.md` | PDF extraction, LangChain evaluation chain |
| 3 | `specs/phase-3-validation-scoring.md` | Response normalization (with corrected missing-ID handling), scoring formulas |
| 4 | `specs/phase-4-ranking-orchestration.md` | Tie-break ranking, frozen-snapshot orchestration, failed-supplier exclusion |
| 5 | `specs/phase-5-streamlit-ui.md` | All 5 UI screens, criteria management (no delete), optional what-if re-ranking |
| 6 | `specs/phase-6-polish-submission.md` | README with Assumptions section, sample JSON, deployment |

See `PLAN.md` for full rationale, the Data Preparation Checklist (verifying user-supplied PDFs against the brief's required profiles/sections), the Edge Case Checklist, and every correction applied after the brief-compliance review.
