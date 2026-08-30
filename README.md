# Agentic RFP Evaluation & Supplier Ranking

A Streamlit application that reads supplier RFP proposal PDFs, scores each one against
configurable weighted criteria using an LLM, then applies **deterministic Python
arithmetic** to benchmark, rank, and present an explainable supplier leaderboard.

The LLM judges proposal *content* only. Every number that decides the outcome —
absolute score, peer benchmark, gap, relative %, PPI, tie-breaks, and final rank — is
computed in plain Python (`scoring.py`, `ranking.py`) and never by the model.

---

## 1. Setup

Requires Python 3.11+ (developed and verified on 3.14) and a Google Gemini API key.

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd Industry_project

# 2. Create a virtual environment and install pinned dependencies
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Provide the API key (never commit this file)
cp .env.example .env
#   then edit .env and set:
#   GEMINI_API_KEY=your-key-here

# 4. Create and seed the SQLite database (schema + 5 default criteria)
python database.py

# 5. Run the app
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`. On Streamlit Community Cloud the key is
supplied through **Secrets** instead of `.env` (see §7).

### Sample data

Place at least four fictional supplier PDFs in `data/sample_pdfs/` before running an
evaluation. The four expected supplier profiles (from the brief) are:

| Supplier | Profile |
|---|---|
| Apex Systems | Strong technical design and security; higher price; moderate delivery schedule |
| BrightPath Tech | Lowest price and fastest timeline; weak compliance detail; limited experience |
| NexaWorks | Balanced; strongest implementation plan and support model |
| Orbit Digital | Strong experience/references; vague integration plan; medium pricing |

Each proposal should contain: executive summary, proposed solution / implementation
approach, timeline / team / milestones, price table with assumptions,
security / compliance / risk controls, and support model + relevant experience +
references.

---

## 2. Architecture

### The 10-step data flow

| Step | Name | Owner file | What happens |
|---|---|---|---|
| 1 | Setup | `database.py` → `orchestrator.run_setup` | Load active criteria from SQLite |
| 2 | Input | `streamlit_app.py` | Upload supplier PDFs; enter name, submission date, experience rating |
| 3 | Batch | `orchestrator.run_batch` | Create the run, generate `rfp_run_id`, **freeze the criterion snapshot once** |
| 4 | Evaluate | `document_tool.py` + `evaluation_agent.py` | PDF → text (PyMuPDF); LangChain prompt → Gemini → parsed JSON |
| 5 | Validate | `validation_tool.py` | Normalize missing / unknown / out-of-range criterion results |
| 6 | Score | `scoring.py` | Absolute weighted score + per-criterion breakdown |
| 7 | Benchmark | `scoring.py` | Best score per criterion; gap; relative % |
| 8 | Rank | `ranking.py` | PPI + fixed tie-break → sequential ranks |
| 9 | Persist | `database.py` | One row per supplier; frozen snapshot embedded in `result_json` |
| 10 | Present | `streamlit_app.py` | Leaderboard, detailed scorecards, run details, JSON download |

### File map

| File | Responsibility |
|---|---|
| `streamlit_app.py` | All UI: 5 screens (Criteria, Supplier input, Leaderboard, Detailed scorecard, Run details) |
| `orchestrator.py` | Pipeline controller; `execute_full_pipeline()`; freezes the criterion snapshot at Batch time |
| `database.py` | Schema DDL, seed data, criteria CRUD (`add` / `update` / `set_active` — **no delete**), run & result persistence, run-lock check; also the standalone `python database.py` seed script |
| `document_tool.py` | PDF text extraction (PyMuPDF only) |
| `evaluation_agent.py` | LangChain `ChatPromptTemplate` + `PydanticOutputParser` + `ChatGoogleGenerativeAI` (Gemini 2.5 Flash), with retry |
| `validation_tool.py` | Normalization of the LLM's parsed output |
| `scoring.py` | Absolute score, benchmark, gap, relative %, PPI |
| `ranking.py` | Tie-break sort + sequential rank assignment |
| `models.py` | Shared Pydantic models; the experience-rating scale constant |

### Tech stack

- **UI**: Streamlit — tables are plain lists/dicts into `st.dataframe` / `st.table` (no pandas)
- **DB**: SQLite via stdlib `sqlite3` (no ORM)
- **LLM**: Gemini 2.5 Flash through LangChain (`langchain-google-genai`), structured output via `PydanticOutputParser`
- **PDF**: PyMuPDF only
- **Validation**: Pydantic

---

## 3. Formulas

All formulas operate on the run's frozen criterion snapshot. Active criteria weights
always sum to exactly 100.

| Quantity | Definition |
|---|---|
| **Absolute weighted score** | `Σ over criteria of (criterion_score / max_score) × weight`. With weights summing to 100 and each ratio in `[0, 1]`, the result is on a 0–100 scale. |
| **Criterion benchmark** | Highest valid score observed for that criterion across all successfully-evaluated suppliers in the run. |
| **Criterion gap** | `supplier_score − benchmark` (0 for the benchmark leader on that criterion, otherwise negative). |
| **Relative performance %** | `(supplier_score / benchmark) × 100`. If the benchmark is 0, defined as **100%** for every supplier on that criterion (see Assumptions). |
| **Peer Performance Index (PPI)** | Weighted average of each criterion's relative-performance %, weighted by that criterion's snapshot weight: `Σ(relative_pct × weight/100) / Σ(weight/100)`. |

### Mandatory tie-break order

Applied as a single stable composite sort key:

```
(-ppi, submission_date, -experience_rating, name.lower())
```

1. Higher PPI first
2. then earlier submission date
3. then higher historical experience rating
4. then supplier name ascending (case-insensitive)

Ranks 1, 2, 3, … are assigned sequentially **after** this sort. Failed suppliers are
excluded from the sort entirely (see Assumptions).

---

## 4. Assumptions

Everything below is a decision made *beyond* the brief's stated minimums. Each is
implemented as a named constant or a commented policy, not a silent guess.

1. **Malformed / unparseable LLM response → all active criteria defaulted to score 0**,
   with a warning. The supplier is still scored and ranked (not marked failed).
   `"failed"` is reserved for PDF-extraction failures and unrecoverable API errors.
   (`validation_tool.MALFORMED_POLICY_WARNING`)

2. **Zero benchmark on a criterion** (every supplier scored 0) → relative performance
   is defined as **100%** for all suppliers on that criterion, with a run-level
   warning. This avoids divide-by-zero and a misleading 0%. (`scoring._gap_and_relative`)

3. **Experience-rating scale is 0–5 inclusive** (float). The brief states a historical
   experience rating exists but not its range; we fix it as an explicit documented
   constant. (`models.EXPERIENCE_RATING_MIN` / `EXPERIENCE_RATING_MAX`)

4. **Per-run criterion snapshot** — the run freezes the active criteria exactly once,
   at Batch time, and every supplier in the run is scored against that same frozen
   set. Each persisted run stores its own snapshot inside `result_json`. This is a
   **design decision for historical reproducibility** (a later weight change must not
   retroactively alter how an old run reads) — *not* a brief requirement. Criteria
   editing is locked in the UI for the duration of a run to make this safe.

5. **Failed-supplier policy** — a supplier whose PDF cannot be extracted, or whose LLM
   call fails after retries, is persisted with `absolute_score = NULL`, `ppi = NULL`,
   `final_rank = NULL` and a warning, and is **excluded from ranking** — never
   silently scored as 0. The UI shows these separately under "Excluded from ranking".

6. **Unknown / missing `criterion_id` in the LLM response** — an entry whose
   `criterion_id` is unknown or absent is discarded with a warning (never guessed or
   reattributed). Active criteria with no valid entry after processing are then
   defaulted to 0 with their own warning.

7. **Out-of-range scores are clipped** to `[0, max_score]` (the snapshot's `max_score`
   always wins over whatever the LLM echoed back), with a warning.

8. **Criteria are never hard-deleted** — only `add`, `update`, and `set_active`
   (activate / deactivate) exist. Deactivation preserves history.

9. **Benchmark is computed once per run**, across all successfully-evaluated
   suppliers, before any per-supplier scoring.

---

## 5. Screens

| Screen | Contents |
|---|---|
| **Criteria** | Display active criteria + weights; add / edit / activate / deactivate. Save is blocked unless active weights sum to exactly 100%. Locked while a run is in progress. |
| **Supplier input** | Upload multiple PDFs; enter name, submission date, experience rating (0–5) per supplier; input validation; triggers `execute_full_pipeline`. |
| **Leaderboard** | Rank, supplier, absolute score, PPI, submission date, experience rating. Failed suppliers split into "Excluded from ranking". Optional what-if re-ranking. |
| **Detailed scorecard** | Per criterion: score, benchmark, gap, relative %, weight, evidence, justification. |
| **Run details** | `rfp_run_id`, status, all warnings grouped by supplier, tie-break key explanation, full-run JSON download. |

### Screenshots

_Add one screenshot per screen here after running locally:_

| Screen | Screenshot |
|---|---|
| Criteria | `docs/screenshots/criteria.png` |
| Supplier input | `docs/screenshots/supplier-input.png` |
| Leaderboard | `docs/screenshots/leaderboard.png` |
| Detailed scorecard | `docs/screenshots/scorecard.png` |
| Run details | `docs/screenshots/run-details.png` |

---

## 6. Demonstration

- **`notebooks/collaboration.ipynb`** runs the full pipeline top-to-bottom against the
  real project modules (setup → criteria → extraction → LLM → validation → scoring →
  benchmark → PPI → ranking → persistence) and demonstrates all 11 items of the Edge
  Case Checklist (`PLAN.md`), including a deliberately corrupted PDF that surfaces a
  warning while the rest of the batch completes.
- **`sample_data/sample_run_result.json`** — a real completed run exported via the Run
  Details download button.

---

## 7. Deploy to Streamlit Community Cloud

1. Push this repository to GitHub (public or private with Streamlit access granted).
   `.env`, `data/rfp_eval.db`, `.venv/` and `__pycache__/` are git-ignored.
2. At [share.streamlit.io](https://share.streamlit.io) → **New app** → select the repo,
   branch, and `streamlit_app.py` as the entry point.
3. In **Advanced settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
   (`evaluation_agent.py` reads `GEMINI_API_KEY` from the environment; Streamlit
   injects secrets as env vars.)
4. Deploy. On first boot the app calls `database.setup_database()` to create and seed
   `data/rfp_eval.db` in the container.
5. Record the public URL here:

   **Live app:** _<paste the Streamlit Community Cloud URL here>_

> Note: Streamlit Community Cloud storage is ephemeral — the SQLite DB resets when the
> container restarts. This is acceptable for a demo; a production deployment would use
> a managed database.

---

## 8. Development process

Spec-driven, 6 phases under `specs/`, done in order. See `PLAN.md` for full rationale,
the Data Preparation Checklist, the Edge Case Checklist, and every correction applied
after the brief-compliance review. `PROGRESS.md` tracks phase status.
