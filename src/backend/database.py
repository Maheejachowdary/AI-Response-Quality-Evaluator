"""
SQLite persistence layer for evaluation results.
Every single and batch evaluation is stored here so the dashboard can
show totals, trends, and filtered views, and the PDF report can be built
from stored data.

Uses Python's built-in sqlite3 — no external dependency, no server.
"""

import os
import sqlite3
from datetime import datetime

# The database file lives alongside this module, in src/backend/.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluations.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def init_db():
    """Create the evaluations table if it doesn't exist. Safe to call repeatedly."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at    TEXT NOT NULL,
            model_name    TEXT,
            dataset       TEXT,
            mode          TEXT,
            question      TEXT,
            response      TEXT,
            reference     TEXT,
            relevance     REAL,
            accuracy      REAL,
            completeness  REAL,
            hallucination REAL,
            overall_score REAL,
            verdict       TEXT,
            hallucination_count INTEGER,
            summary       TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_evaluation(result, question, response, reference="",
                    model_name="", dataset="", mode="single"):
    """
    Persist one evaluation. `result` is the dict returned by
    ResponseEvaluator.evaluate(). Returns the new row id.
    Never raises into the caller — a storage failure must not break
    the evaluation the user already got.
    """
    try:
        hall_claims = result.get("hallucination", {}).get("unsupported_claims", []) or []
        conn = get_connection()
        cur = conn.execute("""
            INSERT INTO evaluations (
                created_at, model_name, dataset, mode,
                question, response, reference,
                relevance, accuracy, completeness, hallucination,
                overall_score, verdict, hallucination_count, summary
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            model_name, dataset, mode,
            question, response, reference,
            result.get("relevance", {}).get("score"),
            result.get("accuracy", {}).get("score"),
            result.get("completeness", {}).get("score"),
            result.get("hallucination", {}).get("score"),
            result.get("overall_score"),
            result.get("verdict"),
            len(hall_claims),
            result.get("summary", ""),
        ))
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        return row_id
    except Exception as e:
        print("DB save error:", e)
        return None


def fetch_all(filters=None):
    """Return all evaluations (optionally filtered), newest first."""
    filters = filters or {}
    clauses, params = [], []
    for field in ("model_name", "dataset", "mode", "verdict"):
        if filters.get(field):
            clauses.append(f"{field} = ?")
            params.append(filters[field])
    if filters.get("date_from"):
        clauses.append("created_at >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("created_at <= ?")
        params.append(filters["date_to"])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = get_connection()
    rows = conn.execute(
        f"SELECT * FROM evaluations {where} ORDER BY id DESC", params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
def dashboard_stats(filters=None):
    """
    Compute aggregate statistics for the dashboard from stored evaluations.
    Returns a dict of totals, averages, verdict counts, model list, and
    time-series data for the trend chart.
    """
    rows = fetch_all(filters)

    total = len(rows)
    scored = [r for r in rows if r.get("overall_score") is not None]

    def avg(field):
        vals = [r[field] for r in scored if r.get(field) is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0

    verdicts = {"Pass": 0, "Needs Improvement": 0, "Fail": 0}
    for r in rows:
        v = r.get("verdict")
        if v in verdicts:
            verdicts[v] += 1

    hallucinated = sum(1 for r in rows if (r.get("hallucination_count") or 0) > 0)
    hall_freq = round(100 * hallucinated / total, 1) if total else 0

    # Trend: overall score per evaluation in chronological order (oldest first)
    chrono = sorted(scored, key=lambda r: r.get("created_at") or "")
    trend_labels = [r["created_at"][5:16].replace("T", " ") for r in chrono]
    trend_scores = [r["overall_score"] for r in chrono]

    # Distinct models and datasets for the filter dropdowns
    models = sorted({r["model_name"] for r in fetch_all() if r.get("model_name")})
    datasets = sorted({r["dataset"] for r in fetch_all() if r.get("dataset")})

    return {
        "total": total,
        "pass_count": verdicts["Pass"],
        "needs_count": verdicts["Needs Improvement"],
        "fail_count": verdicts["Fail"],
        "avg_relevance": avg("relevance"),
        "avg_accuracy": avg("accuracy"),
        "avg_completeness": avg("completeness"),
        "avg_hallucination": avg("hallucination"),
        "avg_overall": avg("overall_score"),
        "hallucination_freq": hall_freq,
        "hallucinated_count": hallucinated,
        "trend_labels": trend_labels,
        "trend_scores": trend_scores,
        "models": models,
        "datasets": datasets,
    }