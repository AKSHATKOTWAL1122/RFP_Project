"""Steps 1 & 3-9 — the pipeline controller.

Plain Python, no agent framework. `execute_full_pipeline` is the single entry
point the Streamlit UI calls on "Evaluate". It maps 1:1 to the brief's step
names: Setup -> Batch -> Evaluate -> Validate -> Score -> Benchmark -> Rank ->
Persist.

Two invariants enforced here:
  * The run's criterion snapshot is loaded exactly once, at Batch time, and
    reused for every supplier and every downstream step. Criteria are never
    re-fetched mid-run.
  * The run's `status` is always resolved to "completed" or "failed" in a
    `finally` block — an unhandled exception must never leave it "in_progress",
    which would permanently lock the Criteria screen.
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

import database
import document_tool
import evaluation_agent
from models import (
    Criterion,
    LLMEvaluationOutput,
    RankedSupplier,
    SupplierScore,
)
from ranking import rank_suppliers
from scoring import compute_benchmarks, score_supplier
from validation_tool import normalize_llm_output


def run_setup() -> List[Criterion]:
    """Step 1 — Setup: the active criteria the UI shows before a run starts."""
    return database.get_active_criteria()


def run_batch() -> Tuple[str, List[Criterion]]:
    """Step 3 — Batch: open the run and freeze its criterion snapshot once."""
    rfp_run_id = str(uuid.uuid4())
    database.create_run(rfp_run_id, status="in_progress")
    snapshot = database.get_active_criteria()
    return rfp_run_id, snapshot


def _evaluate_one(
    supplier_name: str, pdf_path: str, snapshot: List[Criterion]
) -> Tuple[Optional[LLMEvaluationOutput], bool, List[str]]:
    """Step 4 — Evaluate one supplier: PDF -> text -> LLM chain.

    Returns (raw_output_or_None, failed, warnings). A PDF-extraction failure or an
    unrecoverable LLM error (after retries) marks the supplier failed — it is not
    scored as 0.
    """
    try:
        text = document_tool.extract_text(pdf_path, supplier_name)
    except document_tool.DocumentExtractionError as exc:
        return None, True, [f"PDF extraction failed: {exc.message}"]

    try:
        raw = evaluation_agent.evaluate_supplier(supplier_name, text, snapshot)
    except evaluation_agent.EvaluationError as exc:
        return None, True, [f"LLM evaluation failed: {exc.message}"]

    return raw, False, []


def _persist_run(
    rfp_run_id: str, ranked: List[RankedSupplier], snapshot: List[Criterion]
) -> None:
    """Step 9 — Persist: one row per supplier, each embedding the frozen snapshot.

    A past run's criteria are read back from this embedded snapshot, never
    re-derived by joining to the live `evaluation_criteria` table.
    """
    snapshot_json = [c.model_dump() for c in snapshot]
    for rs in ranked:
        ss = rs.supplier_score
        result_json = {
            "supplier_name": ss.supplier_name,
            "failed": ss.failed,
            "warnings": ss.warnings,
            "risks": ss.risks,
            "overall_summary": ss.overall_summary,
            "criteria_snapshot": snapshot_json,
            "scored_criteria": [sc.model_dump() for sc in ss.scored_criteria],
            "absolute_score": ss.absolute_score,
            "ppi": ss.ppi,
            "final_rank": rs.final_rank,
        }
        database.insert_supplier_result(
            rfp_run_id=rfp_run_id,
            supplier_name=ss.supplier_name,
            submission_date=ss.submission_date.isoformat() if ss.submission_date else None,
            experience_rating=ss.experience_rating,
            absolute_score=ss.absolute_score,
            ppi=ss.ppi,
            final_rank=rs.final_rank,
            result_json=result_json,
        )


def execute_full_pipeline(
    supplier_meta: List[dict], uploaded_pdfs: List[str]
) -> Tuple[str, List[RankedSupplier]]:
    """Chain Setup(1) + Batch(3) -> Persist(9). Present(10) is UI-side.

    `supplier_meta`: parallel list of dicts with keys
    `name`, `submission_date` (date), `experience_rating` (float).
    `uploaded_pdfs`: parallel list of local PDF paths.
    """
    rfp_run_id, snapshot = run_batch()
    status = "completed"
    try:
        evaluated = [
            (meta, *_evaluate_one(meta["name"], pdf, snapshot))
            for meta, pdf in zip(supplier_meta, uploaded_pdfs)
        ]

        # Step 5 — Validate: one clean result set per non-failed supplier.
        normalized: dict = {}
        warnings_by_name: dict = {}
        for meta, raw, failed, warns in evaluated:
            name = meta["name"]
            if failed:
                warnings_by_name[name] = warns
                continue
            results, nwarns = normalize_llm_output(
                raw, snapshot, malformed=(raw is None)
            )
            normalized[name] = results
            warnings_by_name[name] = warns + nwarns

        # Step 7 — Benchmark: computed once, across all successfully-evaluated
        # suppliers in this run.
        benchmarks, bench_warnings = compute_benchmarks(normalized, snapshot)

        supplier_scores: List[SupplierScore] = []
        for meta, raw, failed, _ in evaluated:
            name = meta["name"]
            ss = SupplierScore(
                supplier_name=name,
                submission_date=meta["submission_date"],
                experience_rating=meta["experience_rating"],
                criteria_snapshot=snapshot,
                warnings=warnings_by_name.get(name, []),
            )
            if failed:
                ss.failed = True
                supplier_scores.append(ss)
                continue

            # Step 6 — Score: absolute weighted score + per-criterion breakdown + PPI.
            scored, absolute, ppi = score_supplier(
                normalized[name], snapshot, benchmarks
            )
            ss.scored_criteria = scored
            ss.absolute_score = absolute
            ss.ppi = ppi
            if raw is not None:
                ss.risks = list(raw.risks)
                ss.overall_summary = raw.overall_summary
            ss.warnings = ss.warnings + bench_warnings
            supplier_scores.append(ss)

        # Step 8 — Rank.
        ranked = rank_suppliers(supplier_scores)

        _persist_run(rfp_run_id, ranked, snapshot)
        return rfp_run_id, ranked
    except Exception:
        status = "failed"
        raise
    finally:
        database.update_run_status(rfp_run_id, status)
