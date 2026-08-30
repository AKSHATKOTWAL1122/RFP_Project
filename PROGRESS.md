# Progress Log

Short status only. Details live in `PLAN.md`, `specs/`, and the code.

| Phase | Status | Date | Notes |
|---|---|---|---|
| 1 — Foundations | Done | 2026-08-30 | database.py, models.py, .env.example, requirements.txt, .gitignore. Done-check passed. |
| 2 — Extraction & LLM | Code complete | 2026-08-30 | document_tool.py, evaluation_agent.py. Live done-check (real PDF + GEMINI_API_KEY) deferred — no sample PDFs / key present yet. |
| 3 — Validation & Scoring | Done | 2026-08-30 | validation_tool.py, scoring.py. Done-check passed: hand-computed fixture matches, Edge Cases 2–7 demonstrated. |
| 4 — Ranking & Orchestration | Done | 2026-08-30 | ranking.py, orchestrator.py. Done-check passed: edge cases 8–11, stubbed full pipeline persists gapless ranks + frozen snapshot, forced mid-pipeline exception resolves status to `failed`, freeze-once verified. |
| 5 — Streamlit UI | Code complete | 2026-08-30 | streamlit_app.py — all 5 screens (Criteria w/ no-delete + 100% weight guard + run lock, Supplier input w/ validation, Leaderboard w/ failed-supplier split + optional what-if re-rank, Detailed scorecard, Run details w/ JSON download). Boots clean headless (HTTP 200). End-to-end manual done-check deferred — needs real PDFs + GEMINI_API_KEY. |
| 6 — Polish & Submission | In progress | 2026-08-30 | README.md written (setup, architecture, formulas, Assumptions, deploy steps, screenshot placeholders). requirements.txt pinned to verified versions. git repo initialised and pushed to GitHub (AKSHATKOTWAL1122/RFP_Project, branch `main`). Collaboration notebook removed from the project. **Pending (needs user):** 4 supplier PDFs in data/sample_pdfs/ → live run → sample_data/sample_run_result.json + screenshots; GitHub push + Streamlit Cloud deploy + record URL. |

## Environment
- Local `.venv` (Python 3.14); deps installed ad hoc for verification, pinned in Phase 6.
