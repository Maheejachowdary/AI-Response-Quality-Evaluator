"""
End-to-end test for the AI Response Quality Evaluator (Milestone 4).

Runs OFFLINE: the Gemini LLM and FAISS retrieval are mocked, so this
exercises the full pipeline — agents, verdict, orchestrator, database,
dashboard stats, PDF report, Flask routes, error handling, and invalid
input — in seconds with no API calls or quota use.

Run from the project root:
    python tests/e2e_test.py
"""

import sys
import os
import io
import json
import types
import tempfile

# --- make src importable ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

# ---------------------------------------------------------------------------
# 1. Mock google.generativeai BEFORE backend.llm imports it.
# ---------------------------------------------------------------------------
SCENARIO = {"name": "good"}

def _route(prompt):
    s = SCENARIO["name"]
    if "summarising an AI response quality evaluation" in prompt:
        return json.dumps({"summary": f"[{s}] consolidated verdict summary."})
    if "detecting hallucinations" in prompt:
        if s == "bad":
            return json.dumps({"score": 1, "unsupported_claims": ["a fabricated claim"],
                               "reason": "off-topic, unsupported"})
        return json.dumps({"score": 10, "unsupported_claims": [], "reason": "grounded"})
    if "COMPLETENESS" in prompt:
        if s == "bad":
            return json.dumps({"score": 1, "missing_aspects": ["the actual question"],
                               "reason": "did not address question"})
        return json.dumps({"score": 10, "missing_aspects": [], "reason": "fully covered"})
    if "ONLY the factual accuracy" in prompt:
        return json.dumps({"score": 1 if s == "bad" else 10, "evidence": f"[{s}] accuracy"})
    if "ONLY the relevance" in prompt:
        return json.dumps({"score": 1 if s == "bad" else 10, "reason": f"[{s}] relevance"})
    return json.dumps({"score": 5, "reason": "fallback"})

fake_genai = types.ModuleType("google.generativeai")
class _FM:
    def __init__(self, n): pass
    def generate_content(self, p): return types.SimpleNamespace(text=_route(p))
fake_genai.configure = lambda **k: None
fake_genai.GenerativeModel = _FM
fake_google = types.ModuleType("google")
fake_google.generativeai = fake_genai
sys.modules["google"] = fake_google
sys.modules["google.generativeai"] = fake_genai
os.environ.setdefault("GEMINI_API_KEY", "test-key")

# ---------------------------------------------------------------------------
# 2. Mock retrieval so no FAISS index / network is needed.
# ---------------------------------------------------------------------------
fake_retrieval = types.ModuleType("backend.retrieval")
fake_retrieval.retrieve_context_text = lambda q, k=3: "Mock grounding evidence."
fake_retrieval.retrieve = lambda q, k=3: [{"text": "Mock", "similarity": 0.9}]
sys.modules["backend.retrieval"] = fake_retrieval

# ---------------------------------------------------------------------------
# 3. Point the database at a temporary file so we don't touch real data.
# ---------------------------------------------------------------------------
import backend.database as database
_tmp_db = os.path.join(tempfile.gettempdir(), "e2e_test_evaluations.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
database.DB_PATH = _tmp_db

# no real sleeping during batch
import time as _time
_time.sleep = lambda *a, **k: None

# ---------------------------------------------------------------------------
# Now import the app (after all mocks are in place).
# ---------------------------------------------------------------------------
import app as appmod
client = appmod.app.test_client()

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
problems = []

def check(cond, label):
    print(f"  [{PASS if cond else FAIL}] {label}")
    if not cond:
        problems.append(label)

print("=" * 70)
print("END-TO-END TEST — Milestone 4")
print("=" * 70)

# --- 1. Agent scoring + verdict (good) ---
print("\n[1] Agent scoring & verdict — good response")
from backend.evaluator import ResponseEvaluator
ev = ResponseEvaluator()
SCENARIO["name"] = "good"
r = ev.evaluate("What is photosynthesis?", "Plants convert light to energy.")
check(r["overall_score"] == 10.0, f"weighted overall == 10.0 (got {r['overall_score']})")
check(r["verdict"] == "Pass", f"verdict == Pass (got {r['verdict']})")
check(all(k in r for k in ("relevance","accuracy","completeness","hallucination")),
      "all four dimensions present")

# --- 2. Agent scoring + verdict (bad) ---
print("\n[2] Agent scoring & verdict — bad response")
SCENARIO["name"] = "bad"
r = ev.evaluate("Why is the sky blue?", "The Great Wall is long.")
check(r["overall_score"] == 1.0, f"weighted overall == 1.0 (got {r['overall_score']})")
check(r["verdict"] == "Fail", f"verdict == Fail (got {r['verdict']})")
check(len(r["hallucination"]["unsupported_claims"]) > 0, "hallucination flagged on bad response")
check(len(r["completeness"]["missing_aspects"]) > 0, "missing aspect flagged on bad response")

# --- 3. Invalid input handling ---
print("\n[3] Invalid / empty input handling")
r = ev.evaluate("", "some response")
check(r["overall_score"] == 0 and r["verdict"] == "Fail", "empty question -> Fail / 0")
r = ev.evaluate("a question", "")
check(r["overall_score"] == 0 and r["verdict"] == "Fail", "empty response -> Fail / 0")

# --- 4. Database persistence ---
print("\n[4] Database persistence")
database.init_db()
before = len(database.fetch_all())
SCENARIO["name"] = "good"
res = ev.evaluate("Q for DB", "A for DB")
database.save_evaluation(res, "Q for DB", "A for DB", "", model_name="TestModel",
                         dataset="unit", mode="single")
after = len(database.fetch_all())
check(after == before + 1, f"row inserted (before {before}, after {after})")
check(database.fetch_all()[0]["model_name"] == "TestModel", "model_name stored correctly")

# --- 5. Dashboard stats ---
print("\n[5] Dashboard statistics")
stats = database.dashboard_stats()
check(stats["total"] >= 1, "dashboard total >= 1")
check("avg_accuracy" in stats and "hallucination_freq" in stats, "stat keys present")
check("TestModel" in stats["models"], "model appears in filter list")

# --- 6. Flask routes ---
print("\n[6] Flask routes")
check(client.get("/").status_code == 200, "GET / -> 200")
check(client.get("/batch").status_code == 200, "GET /batch -> 200")
check(client.get("/dashboard").status_code == 200, "GET /dashboard -> 200")

SCENARIO["name"] = "good"
resp = client.post("/evaluate", data={"question": "Q?", "response": "A.", "model_name": "RouteTest"})
check(resp.status_code == 200, "POST /evaluate -> 200")
check(b"Pass" in resp.data, "single-eval page shows verdict")

# --- 7. Batch workflow (valid + invalid CSV) ---
print("\n[7] Batch workflow")
good_csv = "question,response,reference\nWhat is X?,X is a thing.,X is a concept.\n"
resp = client.post("/batch",
    data={"csvfile": (io.BytesIO(good_csv.encode()), "t.csv"), "model_name": "BatchTest"},
    content_type="multipart/form-data")
check(resp.status_code == 200 and b"rows evaluated" in resp.data, "valid CSV processed")

bad_csv = "foo,bar\n1,2\n"
resp = client.post("/batch",
    data={"csvfile": (io.BytesIO(bad_csv.encode()), "bad.csv")},
    content_type="multipart/form-data")
check(b"must contain" in resp.data, "invalid CSV (missing columns) handled")

resp = client.post("/batch", data={}, content_type="multipart/form-data")
check(b"No file selected" in resp.data, "missing file handled")

# --- 8. PDF report generation ---
print("\n[8] PDF report generation")
from backend.report_pdf import build_report
pdf = build_report()
check(pdf[:4] == b"%PDF", "report bytes start with %PDF header")
check(len(pdf) > 1000, f"report has content ({len(pdf)} bytes)")

resp = client.get("/report")
check(resp.status_code == 200, "GET /report -> 200")
check(resp.data[:4] == b"%PDF", "downloaded report is a PDF")

# --- 9. Report respects filters ---
print("\n[9] Filtered report")
resp = client.get("/report?model_name=TestModel")
check(resp.status_code == 200 and resp.data[:4] == b"%PDF", "filtered report generates")

# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
if problems:
    print(f"{len(problems)} CHECK(S) FAILED:")
    for p in problems:
        print("  -", p)
else:
    print("ALL CHECKS PASSED")
print("=" * 70)

# cleanup
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)