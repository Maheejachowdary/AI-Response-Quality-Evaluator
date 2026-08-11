import os
import sys
import csv
import io
import time

# Ensure 'src' is importable regardless of launch directory.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from flask import Flask, render_template, request, send_file

from backend.evaluator import ResponseEvaluator
from backend.database import init_db, save_evaluation, dashboard_stats
from backend.report_pdf import build_report

app = Flask(__name__)
evaluator = ResponseEvaluator()
init_db()

# Delay between rows in batch mode to stay within API rate limits.
BATCH_ROW_DELAY = 4
# Safety cap so a huge upload can't exhaust the daily quota in one go.
MAX_BATCH_ROWS = 50


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/evaluate", methods=["POST"])
def evaluate():
    question = request.form.get("question", "")
    response = request.form.get("response", "")
    reference = request.form.get("reference", "")

    results = evaluator.evaluate(question, response, reference)

    save_evaluation(results, question, response, reference,
                    model_name=request.form.get("model_name", ""),
                    dataset="manual", mode="single")

    return render_template(
        "index.html",
        question=question,
        response=response,
        reference=reference,
        results=results,
    )


@app.route("/batch", methods=["GET", "POST"])
def batch():
    if request.method == "GET":
        return render_template("batch.html")

    file = request.files.get("csvfile")
    if not file or file.filename == "":
        return render_template("batch.html", error="No file selected.")

    try:
        raw = file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return render_template(
            "batch.html",
            error="Could not read file. Please upload a UTF-8 encoded CSV.",
        )

    reader = csv.DictReader(io.StringIO(raw))
    fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

    if "question" not in fieldnames or "response" not in fieldnames:
        return render_template(
            "batch.html",
            error="CSV must contain at least 'question' and 'response' columns.",
        )

    def _clean(value):
        # DictReader puts overflow values into a list under None; join them.
        if isinstance(value, list):
            value = " ".join(str(v) for v in value if v)
        return (value or "").strip()

    rows = []
    for raw_row in reader:
        row = {}
        for k, v in raw_row.items():
            if k is None:
                continue  # ignore overflow columns from malformed rows
            row[k.strip().lower()] = _clean(v)
        q = row.get("question", "")
        r = row.get("response", "")
        ref = row.get("reference", "")
        if not q and not r:
            continue
        rows.append({"question": q, "response": r, "reference": ref})
        if len(rows) >= MAX_BATCH_ROWS:
            break

    if not rows:
        return render_template("batch.html", error="No data rows found in CSV.")

    display_rows = []
    passed = needs = failed = errored = 0
    sum_rel = sum_acc = sum_comp = sum_hall = sum_overall = 0.0
    scored = 0

    model_name = request.form.get("model_name", "")

    for i, row in enumerate(rows):
        try:
            res = evaluator.evaluate(row["question"], row["response"], row["reference"])
            display_rows.append({
                "question": row["question"],
                "relevance": res["relevance"]["score"],
                "accuracy": res["accuracy"]["score"],
                "completeness": res["completeness"]["score"],
                "hallucination": res["hallucination"]["score"],
                "overall": res["overall_score"],
                "verdict": res["verdict"],
            })
            save_evaluation(res, row["question"], row["response"], row["reference"],
                            model_name=model_name,
                            dataset="batch_csv", mode="batch")
            sum_rel += res["relevance"]["score"]
            sum_acc += res["accuracy"]["score"]
            sum_comp += res["completeness"]["score"]
            sum_hall += res["hallucination"]["score"]
            sum_overall += res["overall_score"]
            scored += 1
            if res["verdict"] == "Pass":
                passed += 1
            elif res["verdict"] == "Needs Improvement":
                needs += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Batch row {i+1} error:", e)
            errored += 1
            display_rows.append({
                "question": row["question"],
                "error": f"{type(e).__name__}: {e}",
                "verdict": "Error",
            })

        if i < len(rows) - 1:
            time.sleep(BATCH_ROW_DELAY)

    n = scored if scored else 1
    summary = {
        "total": len(rows),
        "pass_count": passed,
        "needs_count": needs,
        "fail_count": failed,
        "errors": errored,
        "avg_relevance": sum_rel / n,
        "avg_accuracy": sum_acc / n,
        "avg_completeness": sum_comp / n,
        "avg_hallucination": sum_hall / n,
        "avg_overall": sum_overall / n,
    }

    return render_template("batch.html", summary=summary, rows=display_rows)
@app.route("/dashboard")
def dashboard():
    filters = {
        "model_name": request.args.get("model_name", "").strip(),
        "dataset": request.args.get("dataset", "").strip(),
        "mode": request.args.get("mode", "").strip(),
        "verdict": request.args.get("verdict", "").strip(),
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
    }
    active = {k: v for k, v in filters.items() if v}
    stats = dashboard_stats(active)
    return render_template("dashboard.html", stats=stats, filters=filters)
@app.route("/report")
def report():
    filters = {
        "model_name": request.args.get("model_name", "").strip(),
        "dataset": request.args.get("dataset", "").strip(),
        "mode": request.args.get("mode", "").strip(),
        "verdict": request.args.get("verdict", "").strip(),
    }
    active = {k: v for k, v in filters.items() if v}
    pdf_bytes = build_report(active)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="evaluation_report.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)