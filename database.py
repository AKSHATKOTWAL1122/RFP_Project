from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from models import Criterion

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rfp_eval.db")

SEED_CRITERIA = [
    ("Technical Capability", "Architecture, integrations, scalability, technical fit", 30, 10),
    ("Implementation Plan", "Timeline, milestones, staffing, risk plan", 20, 10),
    ("Commercial Value", "Pricing clarity, total cost, assumptions", 20, 10),
    ("Security & Compliance", "Controls, certifications, privacy, auditability", 20, 10),
    ("Support & Experience", "Support model, similar projects, references", 10, 10),
]


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS evaluation_criteria (
                criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                weight REAL NOT NULL,
                max_score REAL NOT NULL DEFAULT 10,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS rfp_runs (
                rfp_run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS supplier_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id),
                supplier_name TEXT NOT NULL,
                submission_date TEXT,
                experience_rating REAL,
                absolute_score REAL,
                ppi REAL,
                final_rank INTEGER,
                result_json TEXT NOT NULL
            );
            """
        )


def seed_criteria() -> None:
    with _connect() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
        if existing:
            return
        conn.executemany(
            "INSERT INTO evaluation_criteria (name, description, weight, max_score, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            SEED_CRITERIA,
        )


def _row_to_criterion(row: sqlite3.Row) -> Criterion:
    return Criterion(
        criterion_id=row["criterion_id"],
        name=row["name"],
        description=row["description"],
        weight=row["weight"],
        max_score=row["max_score"],
        is_active=bool(row["is_active"]),
    )


def get_active_criteria() -> List[Criterion]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM evaluation_criteria WHERE is_active = 1 ORDER BY criterion_id"
        ).fetchall()
    return [_row_to_criterion(r) for r in rows]


def get_all_criteria() -> List[Criterion]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM evaluation_criteria ORDER BY criterion_id"
        ).fetchall()
    return [_row_to_criterion(r) for r in rows]


def get_criterion(criterion_id: int) -> Optional[Criterion]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM evaluation_criteria WHERE criterion_id = ?", (criterion_id,)
        ).fetchone()
    return _row_to_criterion(row) if row else None


def add_criterion(name: str, description: str, weight: float, max_score: float = 10) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO evaluation_criteria (name, description, weight, max_score, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            (name, description, weight, max_score),
        )
        return cur.lastrowid


def update_criterion(
    criterion_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    weight: Optional[float] = None,
    max_score: Optional[float] = None,
) -> None:
    fields = {
        "name": name,
        "description": description,
        "weight": weight,
        "max_score": max_score,
    }
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        return
    clause = ", ".join(f"{k} = ?" for k in updates)
    with _connect() as conn:
        conn.execute(
            f"UPDATE evaluation_criteria SET {clause} WHERE criterion_id = ?",
            (*updates.values(), criterion_id),
        )


def set_active(criterion_id: int, is_active: bool) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE evaluation_criteria SET is_active = ? WHERE criterion_id = ?",
            (1 if is_active else 0, criterion_id),
        )


def active_weight_total() -> float:
    with _connect() as conn:
        total = conn.execute(
            "SELECT COALESCE(SUM(weight), 0) FROM evaluation_criteria WHERE is_active = 1"
        ).fetchone()[0]
    return float(total)


def is_run_in_progress() -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM rfp_runs WHERE status = 'in_progress' LIMIT 1"
        ).fetchone()
    return row is not None


def create_run(rfp_run_id: str, status: str = "in_progress") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO rfp_runs (rfp_run_id, created_at, status) VALUES (?, ?, ?)",
            (rfp_run_id, datetime.now(timezone.utc).isoformat(), status),
        )


def update_run_status(rfp_run_id: str, status: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE rfp_runs SET status = ? WHERE rfp_run_id = ?", (status, rfp_run_id)
        )


def get_run(rfp_run_id: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM rfp_runs WHERE rfp_run_id = ?", (rfp_run_id,)
        ).fetchone()
    return dict(row) if row else None


def list_runs() -> List[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM rfp_runs ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def insert_supplier_result(
    rfp_run_id: str,
    supplier_name: str,
    submission_date: Optional[str],
    experience_rating: Optional[float],
    absolute_score: Optional[float],
    ppi: Optional[float],
    final_rank: Optional[int],
    result_json: dict,
) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO supplier_results (rfp_run_id, supplier_name, submission_date, "
            "experience_rating, absolute_score, ppi, final_rank, result_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rfp_run_id,
                supplier_name,
                submission_date,
                experience_rating,
                absolute_score,
                ppi,
                final_rank,
                json.dumps(result_json),
            ),
        )


def get_supplier_results(rfp_run_id: str) -> List[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM supplier_results WHERE rfp_run_id = ? ORDER BY "
            "final_rank IS NULL, final_rank, supplier_name",
            (rfp_run_id,),
        ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["result_json"] = json.loads(d["result_json"])
        results.append(d)
    return results


def setup_database() -> None:
    init_schema()
    seed_criteria()


if __name__ == "__main__":
    setup_database()
    print(f"Database ready at {DB_PATH}")
    for c in get_active_criteria():
        print(f"  [{c.criterion_id}] {c.name} — weight {c.weight}, max {c.max_score}")
    print(f"Active weight total: {active_weight_total()}")
