"""
Scoring consistency validation (Milestone 4).

Runs the SAME dataset through the real evaluator multiple times and
reports the variation in each dimension's score across runs. Low
variation => stable, consistent scoring.

This uses the LIVE Gemini API, so it consumes quota and takes several
minutes (rate-limited). Run from the project root:

    python tests/consistency_test.py
"""

import os
import sys
import json
import time
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from backend.evaluator import ResponseEvaluator

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS = 3
BETWEEN_CALLS = 6      # seconds between evaluations (rate-limit safety)

# Load the same validation dataset used in earlier milestones.
DATASET_PATH = os.path.join(SRC, "validation", "datasets", "truthfulqa.json")
with open(DATASET_PATH, encoding="utf-8") as f:
    dataset = json.load(f)

evaluator = ResponseEvaluator()

DIMS = ["relevance", "accuracy", "completeness", "hallucination"]

print("=" * 70)
print(f"SCORING CONSISTENCY VALIDATION — {len(dataset)} samples x {RUNS} runs")
print("=" * 70)

# results[sample_id][dimension] = [run1_score, run2_score, run3_score]
results = {s["id"]: {d: [] for d in DIMS + ["overall_score"]} for s in dataset}
verdicts = {s["id"]: [] for s in dataset}

for run in range(1, RUNS + 1):
    print(f"\n--- Run {run}/{RUNS} ---")
    for s in dataset:
        # Use a pre-set response if present, else generate one.
        response = s.get("response")
        if not response:
            from backend.llm import generate_response
            response = generate_response(s["question"])
            time.sleep(BETWEEN_CALLS)

        try:
            r = evaluator.evaluate(s["question"], response, s.get("reference", ""))
            for d in DIMS:
                results[s["id"]][d].append(r[d]["score"])
            results[s["id"]]["overall_score"].append(r["overall_score"])
            verdicts[s["id"]].append(r["verdict"])
            print(f"  {s['id']}: overall {r['overall_score']}  ({r['verdict']})")
        except Exception as e:
            print(f"  {s['id']}: ERROR {type(e).__name__}: {e}")
        time.sleep(BETWEEN_CALLS)

# ---- Analysis ----
print("\n" + "=" * 70)
print("CONSISTENCY ANALYSIS (std-dev across runs; 0.00 = perfectly stable)")
print("=" * 70)

overall_stdevs = []
for s in dataset:
    sid = s["id"]
    print(f"\n{sid} ({s.get('category','')})")
    for d in DIMS + ["overall_score"]:
        vals = results[sid][d]
        if len(vals) >= 2:
            sd = statistics.pstdev(vals)
            mean = statistics.mean(vals)
            print(f"  {d:14} mean {mean:5.2f}   values {vals}   std {sd:.2f}")
            if d == "overall_score":
                overall_stdevs.append(sd)
    vset = set(verdicts[sid])
    stable = "STABLE" if len(vset) == 1 else "VARIED"
    print(f"  verdict        {verdicts[sid]}  -> {stable}")

print("\n" + "=" * 70)
if overall_stdevs:
    avg_sd = statistics.mean(overall_stdevs)
    print(f"Average overall-score std-dev across all samples: {avg_sd:.3f}")
    if avg_sd < 0.5:
        print("=> Highly consistent (overall scores vary by less than 0.5 on average).")
    elif avg_sd < 1.5:
        print("=> Moderately consistent.")
    else:
        print("=> Notable variation; scoring is sensitive to run-to-run LLM randomness.")
print("=" * 70)