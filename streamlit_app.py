"""Steps 2 (Input) & 10 (Present) — the Streamlit UI.

Five screens: Criteria (display + management), Supplier input, Leaderboard,
Detailed scorecard, Run details. Tables are plain lists of dicts handed to
`st.dataframe`/`st.table` — no pandas.

The UI never does evaluation arithmetic. It calls `orchestrator.execute_full_pipeline`
for a run, then reads everything back from the persisted rows in `database.py`.
A run's criteria are always read from the snapshot embedded in `result_json`,
never re-derived from the live `evaluation_criteria` table.
"""
from __future__ import annotations

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

import database
from models import EXPERIENCE_RATING_MAX, EXPERIENCE_RATING_MIN

# Load .env from next to this file, overriding any empty/stale shell var of the
# same name (a bare `GEMINI_API_KEY=` exported in the shell would otherwise win).
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# On Streamlit Community Cloud there is no .env — the key is supplied via
# `.streamlit/secrets.toml` (Secrets in the app settings). Bridge it into the
# environment so `evaluation_agent` (plain `os.getenv`) picks it up unchanged.
for _k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
    try:
        if _k in st.secrets and not os.getenv(_k):
            os.environ[_k] = str(st.secrets[_k])
    except Exception:
        pass

st.set_page_config(page_title="RFP Evaluation & Supplier Ranking", layout="wide")

database.setup_database()

WEIGHT_TOLERANCE = 0.01


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _run_selector(key: str) -> str | None:
    runs = database.list_runs()
    if not runs:
        st.info("No runs yet. Start one from the **Supplier input** screen.")
        return None
    labels = {
        f"{r['rfp_run_id'][:8]}…  ·  {r['created_at'][:19]}  ·  {r['status']}": r["rfp_run_id"]
        for r in runs
    }
    picked = st.selectbox("Run", list(labels), key=key)
    return labels[picked]


def _load_run(rfp_run_id: str):
    run = database.get_run(rfp_run_id)
    rows = database.get_supplier_results(rfp_run_id)
    ranked = [r for r in rows if r["final_rank"] is not None]
    failed = [r for r in rows if r["final_rank"] is None]
    ranked.sort(key=lambda r: r["final_rank"])
    return run, ranked, failed


def _snapshot_of(rows) -> list[dict]:
    for r in rows:
        snap = r["result_json"].get("criteria_snapshot")
        if snap:
            return snap
    return []


# --------------------------------------------------------------------------- #
# Screen 1 — Criteria (display + management)
# --------------------------------------------------------------------------- #
def screen_criteria() -> None:
    st.header("Criteria")
    locked = database.is_run_in_progress()
    if locked:
        st.warning(
            "A run is in progress — criteria are locked so every supplier in that "
            "run is scored under one frozen configuration. Editing re-opens when it finishes."
        )

    criteria = database.get_all_criteria()
    st.caption(
        "Changes apply only to runs started *after* you save — past runs keep the "
        "criterion snapshot they were evaluated under."
    )

    st.table(
        [
            {
                "ID": c.criterion_id,
                "Name": c.name,
                "Description": c.description,
                "Weight": c.weight,
                "Max score": c.max_score,
                "Active": "✓" if c.is_active else "—",
            }
            for c in criteria
        ]
    )

    active_total = database.active_weight_total()
    ok = abs(active_total - 100.0) <= WEIGHT_TOLERANCE
    (st.success if ok else st.error)(
        f"Active weights sum to {active_total:g}%. "
        + ("" if ok else "Must equal exactly 100% before any change can be saved.")
    )

    if locked:
        return

    st.subheader("Edit a criterion")
    by_id = {c.criterion_id: c for c in criteria}
    edit_id = st.selectbox(
        "Criterion", list(by_id), format_func=lambda i: f"[{i}] {by_id[i].name}"
    )
    target = by_id[edit_id]
    with st.form("edit_criterion"):
        name = st.text_input("Name", target.name)
        description = st.text_area("Description", target.description)
        weight = st.number_input("Weight (%)", 0.0, 100.0, float(target.weight), step=1.0)
        max_score = st.number_input("Max score", 1.0, 100.0, float(target.max_score), step=1.0)
        is_active = st.checkbox("Active", target.is_active)
        submitted = st.form_submit_button("Save changes")
    if submitted:
        projected = active_total
        if target.is_active:
            projected -= target.weight
        if is_active:
            projected += weight
        if abs(projected - 100.0) > WEIGHT_TOLERANCE:
            st.error(
                f"Save blocked — active weights would sum to {projected:g}%, not 100%."
            )
        else:
            database.update_criterion(
                edit_id, name=name, description=description, weight=weight, max_score=max_score
            )
            database.set_active(edit_id, is_active)
            st.success("Saved.")
            st.rerun()

    st.subheader("Add a criterion")
    st.caption("New criteria are added active — adjust other weights so the active total stays 100%.")
    with st.form("add_criterion"):
        n = st.text_input("Name", key="add_name")
        d = st.text_area("Description", key="add_desc")
        w = st.number_input("Weight (%)", 0.0, 100.0, 0.0, step=1.0, key="add_weight")
        m = st.number_input("Max score", 1.0, 100.0, 10.0, step=1.0, key="add_max")
        add = st.form_submit_button("Add criterion")
    if add:
        if not n.strip():
            st.error("Name is required.")
        elif abs((active_total + w) - 100.0) > WEIGHT_TOLERANCE:
            st.error(
                f"Save blocked — active weights would sum to {active_total + w:g}%, not 100%."
            )
        else:
            database.add_criterion(n.strip(), d.strip(), w, m)
            st.success("Added.")
            st.rerun()


# --------------------------------------------------------------------------- #
# Screen 2 — Supplier input
# --------------------------------------------------------------------------- #
def screen_supplier_input() -> None:
    st.header("Supplier input")

    if database.is_run_in_progress():
        st.warning("A run is already in progress. Wait for it to finish.")
        return

    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        st.error("No GEMINI_API_KEY / GOOGLE_API_KEY found in the environment or .env.")

    active = database.get_active_criteria()
    if abs(database.active_weight_total() - 100.0) > WEIGHT_TOLERANCE:
        st.error("Active criteria weights don't sum to 100%. Fix them on the Criteria screen first.")
        return
    st.caption(f"This run will use {len(active)} active criteria (snapshot frozen when you click Evaluate).")

    files = st.file_uploader(
        "Supplier RFP PDFs", type=["pdf"], accept_multiple_files=True
    )
    if not files:
        st.info("Upload at least one supplier PDF to continue. The brief expects ≥4.")
        return

    st.subheader("Metadata")
    meta = []
    names_seen = []
    errors = []
    for i, f in enumerate(files):
        st.markdown(f"**{f.name}**")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Supplier name", value=os.path.splitext(f.name)[0], key=f"name_{i}")
        sub_date = c2.date_input("Submission date", key=f"date_{i}")
        rating = c3.number_input(
            f"Experience rating ({EXPERIENCE_RATING_MIN}–{EXPERIENCE_RATING_MAX})",
            float(EXPERIENCE_RATING_MIN),
            float(EXPERIENCE_RATING_MAX),
            float(EXPERIENCE_RATING_MIN),
            step=0.5,
            key=f"rating_{i}",
        )
        clean = name.strip()
        if not clean:
            errors.append(f"{f.name}: supplier name is required.")
        elif clean.lower() in [n.lower() for n in names_seen]:
            errors.append(f"{f.name}: duplicate supplier name '{clean}' within this batch.")
        else:
            names_seen.append(clean)
        if not (EXPERIENCE_RATING_MIN <= rating <= EXPERIENCE_RATING_MAX):
            errors.append(f"{f.name}: experience rating out of range.")
        meta.append({"name": clean, "submission_date": sub_date, "experience_rating": float(rating), "file": f})

    for e in errors:
        st.error(e)

    if st.button("Evaluate", type="primary", disabled=bool(errors)):
        tmpdir = tempfile.mkdtemp(prefix="rfp_")
        pdf_paths = []
        for m in meta:
            path = os.path.join(tmpdir, f"{m['name']}.pdf")
            with open(path, "wb") as out:
                out.write(m["file"].getbuffer())
            pdf_paths.append(path)
        supplier_meta = [
            {k: m[k] for k in ("name", "submission_date", "experience_rating")} for m in meta
        ]
        from orchestrator import execute_full_pipeline

        with st.spinner("Running the evaluation pipeline…"):
            rfp_run_id, _ = execute_full_pipeline(supplier_meta, pdf_paths)
        st.session_state["last_run_id"] = rfp_run_id
        st.success(f"Run complete: {rfp_run_id}. See the Leaderboard screen.")


# --------------------------------------------------------------------------- #
# Screen 3 — Leaderboard
# --------------------------------------------------------------------------- #
def screen_leaderboard() -> None:
    st.header("Leaderboard")
    rfp_run_id = _run_selector("lb_run")
    if not rfp_run_id:
        return
    run, ranked, failed = _load_run(rfp_run_id)
    st.caption(f"Run {rfp_run_id} · status: {run['status']}")

    if ranked:
        st.table(
            [
                {
                    "Rank": r["final_rank"],
                    "Supplier": r["supplier_name"],
                    "Absolute score": round(r["absolute_score"], 2) if r["absolute_score"] is not None else None,
                    "PPI": round(r["ppi"], 2) if r["ppi"] is not None else None,
                    "Submission date": r["submission_date"],
                    "Experience": r["experience_rating"],
                }
                for r in ranked
            ]
        )
    else:
        st.info("No ranked suppliers in this run.")

    if failed:
        st.subheader("Excluded from ranking")
        for r in failed:
            warns = r["result_json"].get("warnings", [])
            st.error(f"🚫 **{r['supplier_name']}** — Evaluation failed. " + " ".join(warns))

    _whatif(rfp_run_id, ranked)


def _whatif(rfp_run_id: str, ranked: list) -> None:
    if not ranked:
        return
    with st.expander("What-if re-ranking (hypothetical — not saved)"):
        snapshot = _snapshot_of(ranked)
        if not snapshot:
            st.info("No criterion snapshot available for this run.")
            return
        st.caption(
            "Sliders start from this run's frozen weights and are normalised to 100%. "
            "Scores are the ones already produced for this run — no new LLM call, no DB write."
        )
        raw_weights = {}
        cols = st.columns(len(snapshot))
        for col, c in zip(cols, snapshot):
            raw_weights[c["criterion_id"]] = col.slider(
                c["name"], 0.0, 100.0, float(c["weight"]), step=1.0, key=f"wi_{rfp_run_id}_{c['criterion_id']}"
            )
        total = sum(raw_weights.values()) or 1.0
        norm = {k: v / total * 100.0 for k, v in raw_weights.items()}

        recomputed = []
        for r in ranked:
            rj = r["result_json"]
            num = den = 0.0
            for sc in rj.get("scored_criteria", []):
                cid = sc["criterion"]["criterion_id"]
                w = norm.get(cid, 0.0)
                num += (sc.get("relative_pct") or 0.0) * (w / 100.0)
                den += w / 100.0
            ppi = num / den if den else 0.0
            recomputed.append(
                {
                    "supplier": r["supplier_name"],
                    "ppi": ppi,
                    "submission_date": r["submission_date"],
                    "experience_rating": r["experience_rating"] or 0.0,
                }
            )
        recomputed.sort(
            key=lambda x: (-x["ppi"], x["submission_date"] or "", -x["experience_rating"], x["supplier"].lower())
        )
        st.table(
            [
                {"Hypothetical rank": i, "Supplier": x["supplier"], "PPI": round(x["ppi"], 2)}
                for i, x in enumerate(recomputed, start=1)
            ]
        )


# --------------------------------------------------------------------------- #
# Screen 4 — Detailed scorecard
# --------------------------------------------------------------------------- #
def screen_scorecard() -> None:
    st.header("Detailed scorecard")
    rfp_run_id = _run_selector("sc_run")
    if not rfp_run_id:
        return
    _, ranked, failed = _load_run(rfp_run_id)
    rows = ranked + failed
    if not rows:
        return

    def label(r):
        if r["final_rank"] is None:
            return f"{r['supplier_name']}  (evaluation failed)"
        return f"#{r['final_rank']}  {r['supplier_name']}"

    picked = st.selectbox("Supplier", rows, format_func=label)
    rj = picked["result_json"]

    if picked["final_rank"] is None:
        st.error("This supplier's evaluation failed and it is excluded from ranking.")
        for w in rj.get("warnings", []):
            st.write(f"- {w}")
        return

    c1, c2 = st.columns(2)
    c1.metric("Absolute score", round(picked["absolute_score"], 2))
    c2.metric("PPI", round(picked["ppi"], 2))
    if rj.get("overall_summary"):
        st.write(rj["overall_summary"])
    if rj.get("risks"):
        st.markdown("**Risks:** " + "; ".join(rj["risks"]))

    for sc in rj.get("scored_criteria", []):
        crit = sc["criterion"]
        st.markdown(f"### {crit['name']}  ·  weight {crit['weight']}%")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Score", f"{sc['score']:g}/{crit['max_score']:g}")
        m2.metric("Benchmark", f"{sc['benchmark']:g}")
        m3.metric("Gap", f"{sc['gap']:+g}")
        m4.metric("Relative %", f"{sc['relative_pct']:.0f}%")
        with st.expander("Evidence & justification"):
            st.markdown(f"**Justification:** {sc.get('justification', '')}")
            st.markdown(f"**Evidence:** {sc.get('evidence', '')}")


# --------------------------------------------------------------------------- #
# Screen 5 — Run details
# --------------------------------------------------------------------------- #
def screen_run_details() -> None:
    st.header("Run details")
    rfp_run_id = _run_selector("rd_run")
    if not rfp_run_id:
        return
    run, ranked, failed = _load_run(rfp_run_id)

    c1, c2 = st.columns(2)
    c1.metric("Run ID", rfp_run_id[:8] + "…")
    c2.metric("Status", run["status"])

    st.subheader("Warnings")
    any_warn = False
    for r in ranked + failed:
        warns = r["result_json"].get("warnings", [])
        if warns:
            any_warn = True
            st.markdown(f"**{r['supplier_name']}**")
            for w in warns:
                st.write(f"- {w}")
    if not any_warn:
        st.write("None.")

    st.subheader("Tie-break keys")
    st.caption("Sort key applied in order: (−PPI, submission_date, −experience_rating, name).")
    st.table(
        [
            {
                "Rank": r["final_rank"],
                "Supplier": r["supplier_name"],
                "PPI": round(r["ppi"], 2) if r["ppi"] is not None else None,
                "Submission date": r["submission_date"],
                "Experience rating": r["experience_rating"],
            }
            for r in ranked
        ]
    )

    export = {
        "rfp_run_id": rfp_run_id,
        "status": run["status"],
        "created_at": run["created_at"],
        "criterion_snapshot": _snapshot_of(ranked + failed),
        "ranked_suppliers": [r["result_json"] for r in ranked],
        "excluded_suppliers": [r["result_json"] for r in failed],
    }
    import json

    st.download_button(
        "Download full run as JSON",
        data=json.dumps(export, indent=2, default=str),
        file_name=f"rfp_run_{rfp_run_id[:8]}.json",
        mime="application/json",
    )


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
SCREENS = {
    "Criteria": screen_criteria,
    "Supplier input": screen_supplier_input,
    "Leaderboard": screen_leaderboard,
    "Detailed scorecard": screen_scorecard,
    "Run details": screen_run_details,
}

st.sidebar.title("RFP Evaluation")
choice = st.sidebar.radio("Screen", list(SCREENS))
SCREENS[choice]()
