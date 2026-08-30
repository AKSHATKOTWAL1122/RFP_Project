# Plan: Agentic RFP Evaluation and Supplier Ranking

*Revised after a full review against the six-page assignment brief. See "Corrections Applied" below for what changed and why.*

## Context

This is a classroom mini-project (brief fully captured in `Agentic_RFP_Evaluation_Mini_Project.md`) requiring an AI-assisted Streamlit app that scores supplier RFP PDFs against configurable criteria, benchmarks suppliers against peers, and produces an explainable, deterministic leaderboard. The repo is currently empty (just the brief and an empty notebook) — this is a from-scratch build.

User constraints locked in for this build:
- **LLM**: Gemini 2.5 Flash, called through **LangChain** (`langchain-google-genai`), not the raw SDK. API key from env var, never hardcoded.
- **Orchestration**: plain Python functions, no agent framework — LangChain is scoped only to the single Evaluate/LLM-call step.
- **Sample PDFs**: user supplies their own 4+ supplier PDFs — must be verified against the brief's required profiles/sections before use (see Data Preparation Checklist).
- **Deployment**: build and verify locally first; actually deploy to Streamlit Community Cloud as the final step (mandatory per the brief's submission requirements, not optional).
- **Code shape**: one clear component per file, mirroring the brief's own named components (Document Tool, Evaluation Agent, Validation Tool, Scoring, Ranking, Database, Orchestrator). Comments allowed and encouraged where a rule isn't self-evident (e.g. the zero-benchmark policy) — kept minimal elsewhere.
- **Process**: spec-driven development, work divided into phases; a `CLAUDE.md` at the project root gives every future session the same context automatically; `notebooks/collaboration.ipynb` is an **active** development/demo artifact, updated as each phase lands.

**Tech stack decisions:**
- Validation: **Pydantic** models for the LLM output schema and normalized results.
- Tables in Streamlit: **plain lists/dicts** passed straight to `st.dataframe`/`st.table` — no pandas dependency.
- PDF extraction: **PyMuPDF only** — no pypdf fallback, one dependency.
- Testing: no pytest framework, but a **defined set of edge-case fixtures** (see Edge Case Checklist) must be demonstrated, ideally in the collaboration notebook.
- **LLM call uses LangChain**, scoped to just the Evaluate step (`evaluation_agent.py`):
  - `langchain-google-genai` (`ChatGoogleGenerativeAI`) as the Gemini 2.5 Flash chat model.
  - `ChatPromptTemplate` builds the evaluation prompt, injecting each active criterion's **exact inspection guidance from the brief** (not just its name) — e.g. Technical Capability → "architecture, integrations, scalability, technical fit" — verbatim as the `description` field, sourced from the DB.
  - `PydanticOutputParser` bound to `LLMEvaluationOutput` generates format instructions injected into the prompt, and parses the model's raw text response.
  - Everything **outside** this one LLM-call step stays plain Python — LangChain is not used for orchestration.

## Corrections Applied (from assignment-brief review)

1. **10-step architecture made explicit in the file map** — each file is now named after, and scoped to, one of the brief's named components (Document Tool, Evaluation Agent, Validation Tool, Scoring, Ranking, Database, Orchestrator), not folded together.
2. **Criteria snapshot taken once per batch, not per supplier.** Orchestrator loads active criteria exactly once at Batch time and freezes them as the run's criterion snapshot; every supplier in that run is evaluated/scored against that same frozen snapshot. Criteria editing is locked for the run's duration (already planned via `is_run_in_progress`), which is what makes this safe.
3. **Criterion snapshot reframed as a design decision, not an assignment requirement.** It exists for historical reproducibility (so a later weight change doesn't retroactively alter how an old run reads), documented as such in the README.
4. **`delete_criterion()` removed entirely.** The brief asks only for activate/deactivate/weight changes. Criteria are never hard-deleted — only `add_criterion`, `update_criterion`, `set_active`.
5. **Missing-`criterion_id` handling fixed.** A criterion-result entry with no `criterion_id` cannot be safely attributed to any criterion — it's discarded with a warning, not defaulted to score 0 under an invented ID. Separately, after processing all entries, whichever *active* criteria have no corresponding valid entry are defaulted to 0 with their own warning.
6. **Normalization policies explicitly labeled as assumptions**, to be documented in the README's Assumptions section rather than presented as brief requirements: (a) fully unparseable JSON → all active criteria defaulted to 0, and (b) zero-benchmark → 100% relative performance for all suppliers on that criterion.
7. **Failed-supplier ranking policy defined.** A supplier whose PDF can't be extracted or whose LLM call fails after retries is persisted with `absolute_score = NULL`, `ppi = NULL`, `final_rank = NULL`, and a warning in `result_json` — excluded from the official ranking rather than silently scored as 0. The UI shows them separately with an "Evaluation failed" badge.
8. **Experience-rating scale is a documented, named constant**, not a silent assumption — defined once, called out in README's Assumptions, and easy to change.
9. **Component separation clarified** — `document_tool.py`, `evaluation_agent.py`, `validation_tool.py` are distinct files, not folded into one `evaluation.py`; `scoring.py` (absolute score + peer metrics + PPI) and `ranking.py` (tie-break + rank assignment) are separate files with clearly separated functions.
10. **Collaboration notebook is an active artifact.** It's updated phase-by-phase to progressively call into the real modules and demonstrate the workflow and edge cases — not left as a static outline.
11. **Edge Case Checklist added** (10 cases) as an explicit, demonstrable list rather than an implicit "handle errors" note.
12. **Data Preparation Checklist added** — the user's supplied PDFs must be explicitly verified against the brief's 4 required supplier profiles and required proposal sections before being treated as satisfying that deliverable.
13. **What-if re-ranking marked explicitly optional**, built only after the required workflow is fully working — not on the critical path.
14. **"No code comments" rule removed.** Comments are allowed and encouraged around non-obvious rules (zero-benchmark policy, normalization policy, tie-break order, snapshot rationale) — kept minimal elsewhere.
15. **Dependency pinning deferred.** Build and verify locally first; record the actually-working versions in `requirements.txt` afterward, rather than guessing pins upfront.
16. Formulas, tie-break order, and the LLM/deterministic-arithmetic separation were already correct — unchanged.

## Data Preparation Checklist (must pass before Phase 2's smoke test)

The brief requires ≥4 fictional supplier PDFs with **specific profiles** and **specific required sections** — arbitrary user-supplied PDFs don't automatically satisfy this. Before using any supplied PDF set, verify:

**Profiles** (each PDF must clearly reflect its assigned profile):
| Supplier | Required profile |
|---|---|
| Apex Systems | Strong technical design and security; higher price; moderate delivery schedule |
| BrightPath Tech | Lowest price and fastest timeline; weak compliance detail; limited experience |
| NexaWorks | Balanced; strongest implementation plan and support model |
| Orbit Digital | Strong experience/references; vague integration plan; medium pricing |

**Required sections in every proposal**: executive summary, proposed solution/implementation approach, timeline/team/milestones, price table with assumptions, security/compliance/risk controls, support model + relevant experience + references.

If the user's PDFs don't clearly satisfy this, flag it before proceeding — don't silently treat any 4 PDFs as sufficient.

## Edge Case Checklist (must be demonstrable, ideally in the notebook)

1. Valid evaluation (happy path)
2. LLM response missing an active criterion → defaulted to 0, warned
3. Out-of-range score → clipped, warned
4. Fully malformed/unparseable JSON → all active criteria defaulted to 0, warned
5. Unknown `criterion_id` in response → discarded, warned
6. Criterion-result entry with no `criterion_id` at all → discarded, warned (not misattributed)
7. Zero benchmark on a criterion (all suppliers scored 0) → 100% relative performance, warned
8. Tie on PPI → resolved by earlier submission date
9. Tie on PPI + submission date → resolved by higher experience rating
10. Full tie on PPI + date + rating → resolved by supplier name ascending
11. Supplier PDF extraction fails → excluded from ranking, shown as failed, rest of batch unaffected

## File Structure

```
Industry_project/
├── CLAUDE.md                     # persistent session context
├── streamlit_app.py              # UI: Input (2) + Present (10), Criteria screen, what-if re-ranking (optional)
├── orchestrator.py               # controls steps 1, 3-9; freezes the run's criterion snapshot once per batch
├── database.py                   # steps 1 (load) + 9 (persist); criteria CRUD (add/update/set_active — no delete)
├── document_tool.py              # step 4: PDF text extraction (PyMuPDF)
├── evaluation_agent.py           # step 4: LangChain prompt/chain/LLM call
├── validation_tool.py            # step 5: normalization of the LLM's parsed output
├── scoring.py                    # step 6 (absolute score) + step 7 (benchmark/gap/relative %) + PPI
├── ranking.py                    # step 8: tie-break sort + sequential rank assignment
├── models.py                     # shared Pydantic models
├── requirements.txt
├── .env.example                  # GEMINI_API_KEY=
├── .gitignore                    # .env, data/rfp_eval.db, __pycache__
├── README.md                     # setup, architecture, formulas, assumptions, screenshots (Phase 6)
├── specs/
│   ├── phase-1-foundations.md
│   ├── phase-2-extraction-llm.md
│   ├── phase-3-validation-scoring.md
│   ├── phase-4-ranking-orchestration.md
│   ├── phase-5-streamlit-ui.md
│   └── phase-6-polish-submission.md
├── data/
│   ├── rfp_eval.db               # created at runtime (gitignored)
│   └── sample_pdfs/              # user's supplier PDFs — verified against the Data Preparation Checklist
├── sample_data/
│   └── sample_run_result.json    # exported example of one completed run (Phase 6)
├── Agentic_RFP_Evaluation_Mini_Project.{pdf,md}   # existing brief
└── notebooks/collaboration.ipynb # ACTIVE dev/demo notebook, updated phase-by-phase
```

Each file maps to exactly one of the brief's named components or steps — `document_tool.py` (step 4 extraction), `evaluation_agent.py` (step 4 LLM call), `validation_tool.py` (step 5), `scoring.py` (steps 6-7 + PPI), `ranking.py` (step 8), `database.py` (steps 1 + 9), `orchestrator.py` (controls 1, 3-9), `streamlit_app.py` (steps 2 + 10).

## CLAUDE.md Contents

- Project summary, pointing to the brief and this plan.
- Tech stack: Streamlit, SQLite (stdlib `sqlite3`), Gemini 2.5 Flash via LangChain, Pydantic, PyMuPDF.
- File map with one line per file (as above).
- Hard constraints: LLM never does arithmetic/ranking; tie-break order is fixed; API keys only via env/`st.secrets`; criteria are **never hard-deleted**, only deactivated; the run's criterion snapshot is taken once at Batch time and reused for every supplier in that run — never re-loaded per supplier; failed suppliers are excluded from ranking (NULL score/ppi/rank), never silently scored 0; comments are welcome around non-obvious rules, not banned.
- Note that `notebooks/collaboration.ipynb` is updated alongside each phase to demonstrate the real workflow and the Edge Case Checklist — not a static artifact.
- Phase pointer table.

## Spec Phases

**Phase 1 — Foundations** (`database.py`, `models.py`)
- `.env.example`, `requirements.txt` (unpinned for now — pin after local verification), `.gitignore`.
- SQLite schema exactly: `evaluation_criteria(criterion_id, name, description, weight, max_score, is_active)`, `rfp_runs(rfp_run_id, created_at, status)`, `supplier_results(rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json)` — `absolute_score`/`ppi`/`final_rank` nullable, to support the failed-supplier policy.
- Seed the 5 criteria from the brief **with their exact inspection-guidance text** as `description` (Technical Capability → "Architecture, integrations, scalability, technical fit", etc.), weights 30/20/20/20/10, `is_active=1`.
- `init_schema()` + `seed_criteria()`, idempotent, callable both from Streamlit startup and a `if __name__ == "__main__":` block (`python database.py` = the required DB creation/seed script).
- Criteria CRUD: `add_criterion`, `update_criterion`, `set_active` only — **no `delete_criterion`**.
- `is_run_in_progress()` — checks `rfp_runs` for any `status="in_progress"` row, used to lock criteria editing during an active run.
- A named, documented constant for the experience-rating scale (e.g. `EXPERIENCE_RATING_MIN/MAX`), flagged as an assumption.
- Pydantic models in `models.py`: `Criterion`, `CriterionResult`, `LLMEvaluationOutput`, `SupplierScore`, `RankedSupplier`. `SupplierScore`/`RankedSupplier` embed the frozen criterion snapshot for that run.
- Done-check: `python database.py` creates+seeds the DB standalone; `get_active_criteria()` returns 5 rows summing to 100; each criterion's `description` matches the brief's exact inspection guidance.

**Phase 2 — Document & LLM** (`document_tool.py`, `evaluation_agent.py`)
- Before smoke-testing: verify the user's supplied PDFs against the **Data Preparation Checklist** above.
- `document_tool.py`: PyMuPDF-only text extraction, raising a typed error per-supplier on failure — nothing else in this file.
- `evaluation_agent.py`: `ChatPromptTemplate` (supplier name, document text, the **frozen run criterion snapshot** — id/name/description/max_score) + `PydanticOutputParser(pydantic_object=LLMEvaluationOutput)`; chain = `prompt | ChatGoogleGenerativeAI(model="gemini-2.5-flash") | parser`; bounded retry on transient errors.
- Prompt instructs: use only evidence in the document, return exactly one result per active criterion, stay within score range, JSON only. Criteria descriptions injected verbatim from the DB (not paraphrased) — this is graded under "PDF extraction & prompting."
- Done-check: feed one verified sample PDF through both files in sequence; confirm a parsed `LLMEvaluationOutput` matching the expected shape.

**Phase 3 — Validation & Scoring** (`validation_tool.py`, `scoring.py`)
- `validation_tool.py` normalization, in order:
  1. Drop any criterion-result entry with a missing/null `criterion_id` — warn, do not attribute it to any criterion.
  2. Drop any entry whose `criterion_id` isn't in the run's active snapshot — warn.
  3. For remaining valid entries: clip out-of-range scores to `[0, max_score]` (warn if clipped); always use the DB's `max_score`, never the LLM's echoed value.
  4. After steps 1-3, compare covered `criterion_id`s against the full active snapshot; any active criterion still missing a result → default to `score=0` + warn.
  5. Fully unparseable JSON → skip straight to defaulting all active criteria to 0, single warning noting this is the "malformed response" policy (an assumption, documented in README).
- `scoring.py`:
  - Absolute weighted score = Σ `(criterion_score / max_score) * weight`
  - Benchmark = max valid score per criterion across the run
  - Gap = supplier − benchmark (0 for leader, negative otherwise)
  - Relative % = `(supplier / benchmark) * 100`; **zero-benchmark → 100% for all suppliers on that criterion** (documented assumption, avoids div-by-zero)
  - PPI = weighted average of relative %, weights from the run's frozen snapshot (never live criteria)
- Done-check: hand-computed fixture values match exactly, including edge cases 2-7 from the Edge Case Checklist.

**Phase 4 — Ranking & Orchestration** (`ranking.py`, `orchestrator.py`)
- `ranking.py`: single stable composite sort key `(-ppi, submission_date, -experience_rating, name.lower())`; suppliers with `ppi is None` (failed evaluation) are excluded from this sort entirely, not sorted-in-as-worst.
- `orchestrator.py`, mapped 1:1 to the brief's step names:
  1. `run_setup()` — Setup
  3. `run_batch(supplier_meta)` — Batch: generates `rfp_run_id`, `database.create_run(..., status="in_progress")`, **loads active criteria exactly once and freezes them as this run's snapshot** — this snapshot, not a fresh reload, is what every subsequent step uses
  4. `evaluate_supplier(...)` — Evaluate: `document_tool` → `evaluation_agent`, called per supplier, using the frozen snapshot
  5. `validation_tool.validate_and_normalize(...)` — Validate
  6-7. `scoring.py` calls — Score, Benchmark
  8. `ranking.rank_suppliers(...)` — Rank
  9. `persist_run(...)` — Persist: writes rows to `supplier_results`, embedding the frozen snapshot in `result_json`
  - `execute_full_pipeline(...)` is the single entry point the UI calls; per-supplier PDF/LLM failures are caught, recorded as a warning, and that supplier is persisted with `absolute_score/ppi/final_rank = NULL` and excluded from ranking rather than defaulted to 0 — the rest of the batch continues
  - The whole pipeline runs inside try/except/**finally**, guaranteeing `rfp_runs.status` always resolves to `"completed"` or `"failed"` — never stuck at `"in_progress"`
- Done-check: all 11 Edge Case Checklist items reproduced and verified, including a forced failed-supplier case showing exclusion (not zero-scoring) and a forced mid-pipeline exception still resolving `status` to `"failed"`.

**Phase 5 — Streamlit UI** (`streamlit_app.py`)
- 5 required screens: Criteria (display + management), Supplier input, Leaderboard, Detailed scorecard, Run details.
- Tables as plain lists of dicts — no pandas.
- Supplier input validation: non-empty unique-within-batch supplier name, required submission date, experience rating within the documented constant range — inline `st.error`.
- Criteria screen: add/edit/`set_active` (activate/deactivate) — **no delete button**. Running weight-total shown; Save blocked until active weights sum to exactly 100. Whole screen locked while `is_run_in_progress()`.
- Leaderboard: ranked suppliers in a gapless 1..N order; any excluded/failed suppliers shown separately with an "Evaluation failed" badge, not folded into the ranked table.
- **What-if re-ranking is optional** — build it only after the required screens and the official ranking are fully verified working. It reuses the run's frozen criterion snapshot, recomputes in memory only, never writes to the DB.
- Done-check: full run with ≥4 verified PDFs produces a correct leaderboard; criteria Save is blocked on bad weight totals and during an in-progress run; a forced supplier failure shows correctly as excluded, not zero-ranked.

**Phase 6 — Polish & Submission**
- `README.md`: setup, architecture (the 8-file/10-step map), formulas, **Assumptions section** listing every documented assumption (malformed-JSON policy, zero-benchmark policy, experience-rating scale, criterion-snapshot rationale), screenshots, Streamlit Cloud deployment steps.
- Update `notebooks/collaboration.ipynb` to progressively demonstrate: setup → criteria → extraction → LLM → validation → scoring → benchmark → PPI → ranking → persistence, plus the Edge Case Checklist.
- Export one real completed run to `sample_data/sample_run_result.json`.
- Demonstrate one successful run plus at least one deliberate error case.
- **Deploy to Streamlit Community Cloud**, record the public URL, and pin `requirements.txt` to the versions actually verified working locally.

## requirements.txt

```
streamlit
pymupdf
langchain
langchain-google-genai
pydantic
python-dotenv
```
Unpinned for now — build and verify locally first, then pin to the exact versions confirmed working before deployment (Phase 6), rather than guessing compatible ranges upfront.

## Verification (end-to-end, Phase 5/6)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY
python database.py     # create + seed the database standalone
streamlit run streamlit_app.py
```
Confirm: Criteria screen shows 5 seeded criteria (exact brief descriptions) summing to 100%; uploading verified supplier PDFs + metadata and clicking Evaluate produces a correctly deterministic leaderboard; a supplier with a broken PDF is excluded from ranking (not zero-scored) and flagged; scorecards show benchmark/gap/relative%/evidence; Run Details JSON matches persisted data; editing/deactivating a criterion after a run exists leaves that run's scorecard unchanged; all 11 Edge Case Checklist items are reproducible.
