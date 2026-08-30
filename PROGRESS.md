# Progress Log

Short status only. Details live in `PLAN.md`, `specs/`, and the code.

| Phase | Status | Date | Notes |
|---|---|---|---|
| 1 — Foundations | Done | 2026-08-30 | database.py, models.py, .env.example, requirements.txt, .gitignore. Done-check passed. |
| 2 — Extraction & LLM | Done | 2026-08-30 | document_tool.py, evaluation_agent.py. Live done-check passed in Phase 6: the 4 sample PDFs extract and evaluate through Gemini 2.5 Flash end to end. |
| 3 — Validation & Scoring | Done | 2026-08-30 | validation_tool.py, scoring.py. Done-check passed: hand-computed fixture matches, Edge Cases 2–7 demonstrated. |
| 4 — Ranking & Orchestration | Done | 2026-08-30 | ranking.py, orchestrator.py. Done-check passed: edge cases 8–11, stubbed full pipeline persists gapless ranks + frozen snapshot, forced mid-pipeline exception resolves status to `failed`, freeze-once verified. |
| 5 — Streamlit UI | Code complete | 2026-08-30 | streamlit_app.py — all 5 screens (Criteria w/ no-delete + 100% weight guard + run lock, Supplier input w/ validation, Leaderboard w/ failed-supplier split + optional what-if re-rank, Detailed scorecard, Run details w/ JSON download). Boots clean headless (HTTP 200). End-to-end done-check passed in Phase 6 (live run + broken-input case, screenshots captured). |
| 6 — Polish & Submission | In progress | 2026-08-30 | README.md written (setup, architecture, formulas, Assumptions, deploy steps, embedded screenshots). requirements.txt pinned to verified versions. git repo initialised and pushed to GitHub (AKSHATKOTWAL1122/RFP_Project, branch `main`). Collaboration notebook removed. `.devcontainer/` + `.streamlit/secrets.toml.example` added. Live run completed against 4 sample PDFs — `sample_data/sample_run_result.json` exported (clean 4-supplier run), 5 screen screenshots in `docs/screenshots/` (captured from the broken-input demo run), corrupt-PDF case demonstrated with the supplier excluded from ranking and the warning surfaced in Run Details. **Pending (needs user):** Streamlit Community Cloud deploy + record public URL. |

## Environment
- Local `.venv` (Python 3.14); deps installed ad hoc for verification, pinned in Phase 6.
- `.devcontainer/` (Codespaces) pins Python 3.11. `requirements.txt` pins were verified on 3.14 only — when deploying to Streamlit Community Cloud, select a Python version its runtime offers (3.13 recommended) and confirm the first build resolves.
