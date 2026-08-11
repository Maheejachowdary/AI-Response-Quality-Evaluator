import os
from datetime import datetime


def generate_report(results):
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    dataset_name = results[0].get("dataset") or "benchmark"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(reports_dir, f"{dataset_name.lower()}_{timestamp}.txt")

    def scores(dim):
        return [r["evaluation"][dim]["score"] for r in results]

    relevance_scores = scores("relevance")
    accuracy_scores = scores("accuracy")
    completeness_scores = scores("completeness")
    hallucination_scores = scores("hallucination")
    overall_scores = [r["evaluation"]["overall_score"] for r in results]

    def avg(xs):
        return sum(xs) / len(xs)

    verdict_counts = {"Pass": 0, "Needs Improvement": 0, "Fail": 0}
    for r in results:
        v = r["evaluation"].get("verdict", "Fail")
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    with open(report_path, "w", encoding="utf-8") as report:
        report.write("=" * 70 + "\n")
        report.write("AI RESPONSE QUALITY EVALUATION - MILESTONE 3 VALIDATION REPORT\n")
        report.write("=" * 70 + "\n\n")
        report.write(f"Generated On : {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n")
        report.write(f"Dataset      : {dataset_name}\n")
        report.write(f"Samples      : {len(results)}\n\n")

        report.write("=" * 70 + "\nSUMMARY\n" + "=" * 70 + "\n\n")
        report.write(f"Average Relevance Score      : {avg(relevance_scores):.2f}/10\n")
        report.write(f"Average Accuracy Score       : {avg(accuracy_scores):.2f}/10\n")
        report.write(f"Average Completeness Score   : {avg(completeness_scores):.2f}/10\n")
        report.write(f"Average Hallucination Score  : {avg(hallucination_scores):.2f}/10\n")
        report.write(f"Average Overall (weighted)   : {avg(overall_scores):.2f}/10\n\n")
        report.write(f"Highest Overall Score        : {max(overall_scores):.2f}\n")
        report.write(f"Lowest Overall Score         : {min(overall_scores):.2f}\n\n")

        report.write("Verdict Distribution:\n")
        report.write(f"  Pass              : {verdict_counts.get('Pass', 0)}\n")
        report.write(f"  Needs Improvement : {verdict_counts.get('Needs Improvement', 0)}\n")
        report.write(f"  Fail              : {verdict_counts.get('Fail', 0)}\n\n")

        for result in results:
            report.write("=" * 70 + "\n")
            report.write(f"Sample ID : {result['id']}\n")
            if result.get("category"):
                report.write(f"Category  : {result['category']}\n")
            report.write("=" * 70 + "\n\n")

            report.write(f"Question:\n{result['question']}\n\n")
            report.write(f"Generated Response:\n{result['response']}\n\n")
            report.write(f"Reference Answer:\n{result['reference']}\n\n")

            ev = result["evaluation"]

            report.write("-" * 50 + "\nRELEVANCE\n" + "-" * 50 + "\n")
            report.write(f"Score : {ev['relevance']['score']}/10\n\n")
            report.write(f"Reason:\n{ev['relevance'].get('reason', '')}\n\n")

            report.write("-" * 50 + "\nACCURACY\n" + "-" * 50 + "\n")
            report.write(f"Score : {ev['accuracy']['score']}/10\n\n")
            report.write(f"Evidence:\n{ev['accuracy'].get('evidence', '')}\n\n")

            report.write("-" * 50 + "\nCOMPLETENESS\n" + "-" * 50 + "\n")
            report.write(f"Score : {ev['completeness']['score']}/10\n\n")
            report.write(f"Reason:\n{ev['completeness'].get('reason', '')}\n\n")

            report.write("Missing Aspects:\n")
            missing = ev["completeness"].get("missing_aspects", [])
            if missing:
                for aspect in missing:
                    report.write(f"  - {aspect}\n")
            else:
                report.write("  (none - fully covered)\n")
            report.write("\n")

            report.write("-" * 50 + "\nHALLUCINATION\n" + "-" * 50 + "\n")
            report.write(f"Score : {ev['hallucination']['score']}/10\n\n")
            report.write(f"Reason:\n{ev['hallucination'].get('reason', '')}\n\n")

            report.write("Unsupported Claims:\n")
            unsupported = ev["hallucination"].get("unsupported_claims", [])
            if unsupported:
                for claim in unsupported:
                    report.write(f"  - {claim}\n")
            else:
                report.write("  (none detected)\n")
            report.write("\n")

            report.write("-" * 50 + "\nVERDICT\n" + "-" * 50 + "\n")
            report.write(f"Overall (weighted)     : {ev['overall_score']:.2f}/10\n")
            report.write(f"Verdict                : {ev.get('verdict', 'N/A')}\n\n")
            report.write(f"Consolidated Reasoning:\n{ev.get('summary', '')}\n\n")

    return report_path