"""
Generates a downloadable PDF report of stored evaluations using fpdf2
(pure Python, no compiled dependencies).

The report contains: project details, summary statistics, per-evaluation
results with dimension scores, flagged hallucinations, verdicts, and
automatic improvement recommendations.
"""

import io
from datetime import datetime
from fpdf import FPDF

from backend.database import fetch_all, dashboard_stats


# fpdf2's core fonts are latin-1 only; strip characters it can't encode.
def _safe(text):
    if text is None:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")


class _ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "AI Response Quality Evaluation Report", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, _safe(f"Generated {datetime.now().strftime('%d %b %Y, %I:%M %p')}"),
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _section(pdf, title):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(240, 240, 245)
    pdf.cell(0, 8, _safe(title), new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(1)


def _recommendations(row):
    """Derive simple improvement recommendations from the scores."""
    recs = []
    if (row.get("relevance") or 10) < 6:
        recs.append("Improve relevance: ensure the response directly addresses the question asked.")
    if (row.get("accuracy") or 10) < 6:
        recs.append("Improve accuracy: verify factual claims against reliable sources.")
    if (row.get("completeness") or 10) < 6:
        recs.append("Improve completeness: cover all parts of the question, not just some.")
    if (row.get("hallucination") or 10) < 6 or (row.get("hallucination_count") or 0) > 0:
        recs.append("Reduce hallucination: remove claims not supported by evidence.")
    if not recs:
        recs.append("No major issues detected; response meets quality thresholds.")
    return recs


def build_report(filters=None):
    """Build the PDF and return it as bytes."""
    rows = fetch_all(filters)
    stats = dashboard_stats(filters)

    pdf = _ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    epw = pdf.epw  # effective page width (usable width between margins)

    # --- Project details ---
    _section(pdf, "Project Details")
    details = [
        ("Project", "AI Response Quality Evaluator"),
        ("Evaluation dimensions", "Relevance, Accuracy, Completeness, Hallucination"),
        ("Scoring model", "Weighted: Accuracy 35%, Hallucination 30%, Completeness 20%, Relevance 15%"),
        ("Verdict bands", "Pass >= 8.0, Needs Improvement 5.0-7.9, Fail < 5.0"),
    ]
    if filters:
        applied = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
        if applied:
            details.append(("Filters applied", applied))
    for label, value in details:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(epw, 6, _safe(label + ":"))
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(epw, 6, _safe(value))
        pdf.ln(1)
    pdf.ln(2)

    # --- Summary ---
    _section(pdf, "Summary")
    pdf.set_font("Helvetica", "", 10)
    summary_lines = [
        f"Total evaluations: {stats['total']}",
        f"Pass: {stats['pass_count']}   Needs Improvement: {stats['needs_count']}   Fail: {stats['fail_count']}",
        f"Average Relevance: {stats['avg_relevance']}/10",
        f"Average Accuracy: {stats['avg_accuracy']}/10",
        f"Average Completeness: {stats['avg_completeness']}/10",
        f"Average Hallucination: {stats['avg_hallucination']}/10",
        f"Average Overall (weighted): {stats['avg_overall']}/10",
        f"Hallucination frequency: {stats['hallucination_freq']}% ({stats['hallucinated_count']} of {stats['total']})",
    ]
    for line in summary_lines:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 6, _safe(line))
    pdf.ln(3)

    # --- Individual evaluations ---
    _section(pdf, "Individual Evaluation Results")
    for i, row in enumerate(rows, start=1):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        verdict = row.get("verdict") or "N/A"
        pdf.multi_cell(epw, 6, _safe(f"{i}. [{verdict}]  {row.get('question', '')}"))

        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(90, 90, 90)
        meta = f"Model: {row.get('model_name') or 'n/a'}   Mode: {row.get('mode') or 'n/a'}   Date: {row.get('created_at') or 'n/a'}"
        pdf.multi_cell(epw, 5, _safe(meta))
        pdf.set_text_color(0, 0, 0)

        pdf.set_x(pdf.l_margin)
        scores = (f"Relevance {row.get('relevance')}/10   "
                  f"Accuracy {row.get('accuracy')}/10   "
                  f"Completeness {row.get('completeness')}/10   "
                  f"Hallucination {row.get('hallucination')}/10   "
                  f"Overall {row.get('overall_score')}/10")
        pdf.multi_cell(epw, 5, _safe(scores))

        if (row.get("hallucination_count") or 0) > 0:
            pdf.set_x(pdf.l_margin)
            pdf.set_text_color(180, 30, 30)
            pdf.multi_cell(epw, 5, _safe(f"Flagged hallucinations: {row.get('hallucination_count')} claim(s)"))
            pdf.set_text_color(0, 0, 0)

        recs = _recommendations(row)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(epw, 5, _safe("Recommendation: " + recs[0]))
        pdf.set_font("Helvetica", "", 9)
        pdf.ln(2)

    out = pdf.output()
    return bytes(out)