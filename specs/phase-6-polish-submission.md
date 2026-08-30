# Phase 6 — Polish & Submission

Files: `README.md`, `sample_data/sample_run_result.json`, deployment

## Scope

Close out every submission requirement from the brief that isn't already satisfied by Phases 1-5.

## Deliverables

- `README.md` covering:
  - Setup steps (`pip install -r requirements.txt`, `.env` setup, `python database.py`, `streamlit run streamlit_app.py`)
  - Architecture overview (the file map, the 10-step flow, which file owns which step)
  - Formulas, written out explicitly
  - **A dedicated Assumptions section**, listing every documented assumption made beyond the brief's minimums:
    - Malformed/unparseable LLM JSON → all active criteria defaulted to 0 (Phase 3)
    - Zero-benchmark → 100% relative performance for all suppliers on that criterion (Phase 3)
    - Experience-rating numeric scale and its exact bounds (Phase 1)
    - Criterion snapshot per run — why it exists (historical reproducibility), explicitly framed as a design decision, not a brief requirement
    - Failed-supplier policy — excluded from ranking with NULL score/ppi/rank, rather than scored 0
  - Screenshots of each of the 5 screens
  - Streamlit Community Cloud deployment steps
- Export one real completed run to `sample_data/sample_run_result.json` (via the Run Details download, using verified real supplier PDFs)
- Demonstration: one successful full run, plus at least one deliberately triggered validation/error case (e.g. a corrupted PDF, or a temporarily invalid API key) showing a warning surfaced in Run Details while the rest of the batch still completes
- Pin `requirements.txt` to the exact versions verified working locally (replacing the unpinned Phase 1 list)
- **Deploy to Streamlit Community Cloud** and record the public app URL — the brief's submission requirements mandate this; it is not optional

## Done-check

- README is complete enough that a stranger could clone the repo and run the app from scratch, and its Assumptions section covers every item listed above
- `sample_data/sample_run_result.json` exists and matches the shape produced by the Run Details download button
- The demo covers both a clean successful run and a deliberately broken input, with the resulting warning visible in the UI
- `requirements.txt` is pinned to verified versions
- The public Streamlit Cloud URL is live and loads the app
