from backend.llm import generate_response
from backend.utils import parse_json_response


class VerdictAgent:
    """
    Milestone 3 - Verdict Agent.
    Aggregates the four dimension scores (Relevance, Accuracy, Completeness,
    Hallucination) into a single weighted overall score, maps it to a
    Pass / Needs Improvement / Fail verdict, and produces a consolidated
    reasoning summary.

    The weighted score is computed deterministically in Python (not by the
    LLM), so the number is always reproducible. The LLM is used only to
    write a short human-readable summary of the per-dimension findings, with
    a deterministic fallback if the LLM call fails.
    """

    # Weights must sum to 1.0
    WEIGHTS = {
        "accuracy": 0.35,
        "hallucination": 0.30,
        "completeness": 0.20,
        "relevance": 0.15,
    }

    PASS_THRESHOLD = 8.0
    NEEDS_IMPROVEMENT_THRESHOLD = 5.0

    def _weighted_score(self, scores: dict) -> float:
        total = 0.0
        for dim, weight in self.WEIGHTS.items():
            total += float(scores.get(dim, 0)) * weight
        return round(total, 2)

    def _verdict_label(self, overall: float) -> str:
        if overall >= self.PASS_THRESHOLD:
            return "Pass"
        if overall >= self.NEEDS_IMPROVEMENT_THRESHOLD:
            return "Needs Improvement"
        return "Fail"

    def evaluate(self, question, response, dimension_results: dict) -> dict:
        scores = {
            "relevance": dimension_results["relevance"]["score"],
            "accuracy": dimension_results["accuracy"]["score"],
            "completeness": dimension_results["completeness"]["score"],
            "hallucination": dimension_results["hallucination"]["score"],
        }

        overall = self._weighted_score(scores)
        verdict = self._verdict_label(overall)

        missing = dimension_results["completeness"].get("missing_aspects", [])
        unsupported = dimension_results["hallucination"].get("unsupported_claims", [])

        findings = f"""
Relevance score: {scores['relevance']}/10 - {dimension_results['relevance'].get('reason', '')}
Accuracy score: {scores['accuracy']}/10 - {dimension_results['accuracy'].get('evidence', '')}
Completeness score: {scores['completeness']}/10 - {dimension_results['completeness'].get('reason', '')}
Missing aspects: {missing if missing else 'none'}
Hallucination score: {scores['hallucination']}/10 - {dimension_results['hallucination'].get('reason', '')}
Unsupported claims: {unsupported if unsupported else 'none'}
Computed overall (weighted): {overall}/10
Verdict: {verdict}
"""

        prompt = f"""
You are summarising an AI response quality evaluation for a reviewer.

Question:
{question}

Per-dimension findings (already computed - do NOT change any scores):
{findings}

Write a single consolidated reasoning paragraph (3-5 sentences) that
explains the overall verdict of "{verdict}" based on the findings above.
Mention the strongest and weakest dimensions and any missing aspects or
unsupported claims. Do not invent new scores.

Return ONLY valid JSON in this exact format:
{{
    "summary": "consolidated reasoning paragraph"
}}

Return ONLY the JSON object, no markdown.
"""
        try:
            raw = generate_response(prompt)
            parsed = parse_json_response(raw, "summary")
            summary = parsed.get("summary", "").strip()
            if not summary or summary.startswith("Could not parse"):
                raise ValueError("empty summary")
        except Exception:
            # Deterministic fallback so the verdict never depends on the LLM.
            weakest = min(scores, key=scores.get)
            strongest = max(scores, key=scores.get)
            summary = (
                f"Overall weighted score {overall}/10 -> {verdict}. "
                f"Strongest dimension: {strongest} ({scores[strongest]}/10). "
                f"Weakest dimension: {weakest} ({scores[weakest]}/10)."
            )
            if missing:
                summary += f" Missing aspects: {', '.join(missing)}."
            if unsupported:
                summary += f" Unsupported claims flagged: {len(unsupported)}."

        return {
            "overall_score": overall,
            "verdict": verdict,
            "weights": self.WEIGHTS,
            "summary": summary,
        }