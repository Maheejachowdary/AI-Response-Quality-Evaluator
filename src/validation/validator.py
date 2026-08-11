"""
Milestone 2 deliverable: validation script.
Runs the Relevance, Accuracy, and Hallucination agents across sampled
question/reference pairs from TruthfulQA to check scoring consistency
and reasoning quality, then writes a report to validation/reports/.
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure the 'src' directory (parent of this file's folder) is on sys.path
# so 'backend' and 'validation' packages are importable no matter where
# this script is run from.
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from backend.evaluator import ResponseEvaluator
from backend.llm import generate_response

from validation.dataset_loader import load_dataset
from validation.report import generate_report

DATASET = "truthfulqa.json"
SAMPLE_SIZE = 5
SAMPLING_STRATEGY = "all"  # "all" | "random" | "sequential"
def evaluate_sample(evaluator, sample):
    if "response" in sample:
        response = sample["response"]
    else:
        print("  Generating AI response with Gemini (no pre-set response in sample)...")
        response = generate_response(sample["question"])
        time.sleep(8)

    evaluation = evaluator.evaluate(
        sample["question"],
        response,
        sample["reference"],
    )

    return {
        "id": sample["id"],
        "dataset": sample.get("dataset"),
        "category": sample.get("category"),
        "question": sample["question"],
        "response": response,
        "reference": sample["reference"],
        "evaluation": evaluation,
    }


def main():
    evaluator = ResponseEvaluator()

    samples = load_dataset(
        filename=DATASET,
        sample_size=SAMPLE_SIZE,
        strategy=SAMPLING_STRATEGY,
    )

    results = []

    print("=" * 60)
    print("AI RESPONSE QUALITY EVALUATOR - Milestone 3 Validation")
    print("=" * 60)
    print(f"Dataset  : {DATASET}")
    print(f"Samples  : {len(samples)}")
    print(f"Strategy : {SAMPLING_STRATEGY}")
    print("=" * 60)

    failures = []

    for index, sample in enumerate(samples, start=1):
        print(f"\nEvaluating Sample {index}/{len(samples)} (ID: {sample['id']})")
        if sample.get("category"):
            print(f"Category : {sample['category']}")

        try:
            result = evaluate_sample(evaluator, sample)
        except Exception as e:
            print(f"FAILED  x  {type(e).__name__}: {e}")
            failures.append({"id": sample["id"], "error": f"{type(e).__name__}: {e}"})
            time.sleep(10)
            continue

        results.append(result)
        print("Completed OK")
        time.sleep(15)

    print("\n" + "=" * 60)
    print(f"Succeeded : {len(results)}/{len(samples)}")
    if failures:
        print(f"Failed    : {len(failures)}")
        for f in failures:
            print(f"  - {f['id']}: {f['error']}")
    print("=" * 60)

    if not results:
        print("No samples succeeded - no report written.")
        print("Fix the errors above and re-run before filling in your report.")
        return []

    report_path = generate_report(results)

    print("\nValidation Completed")
    print("Report saved to:", report_path)
    if failures:
        print(f"NOTE: report covers {len(results)} sample(s); "
              f"{len(failures)} excluded due to errors.")

    return results


if __name__ == "__main__":
    main()