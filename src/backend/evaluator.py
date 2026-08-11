"""
Orchestration layer: runs all four judge agents against a single
(question, response, reference) submission, then aggregates their scores
via the Verdict Agent into one weighted overall score and verdict.
"""

from agents.relevance_agent import RelevanceJudge
from agents.accuracy_agent import AccuracyJudge
from agents.completeness_agent import CompletenessJudge
from agents.hallucination_agent import HallucinationJudge
from agents.verdict_agent import VerdictAgent


class ResponseEvaluator:

    def __init__(self):
        self.relevance_agent = RelevanceJudge()
        self.accuracy_agent = AccuracyJudge()
        self.completeness_agent = CompletenessJudge()
        self.hallucination_agent = HallucinationJudge()
        self.verdict_agent = VerdictAgent()

    def _empty_result(self, message):
        dims = {
            "relevance": {"score": 0, "reason": message},
            "accuracy": {"score": 0, "evidence": message},
            "completeness": {"score": 0, "reason": message, "missing_aspects": []},
            "hallucination": {"score": 0, "reason": message, "unsupported_claims": []},
        }
        return {
            **dims,
            "overall_score": 0,
            "verdict": "Fail",
            "summary": message,
        }

    def evaluate(self, question: str, response: str, reference: str = ""):
        question = (question or "").strip()
        response = (response or "").strip()
        reference = (reference or "").strip()

        if not question or not response:
            missing = "Question" if not question else "AI response"
            return self._empty_result(f"{missing} cannot be empty.")

        # --- Relevance ---
        try:
            relevance_result = self.relevance_agent.evaluate(question, response)
        except Exception as e:
            print("Relevance Agent Error:", e)
            relevance_result = {"score": 0, "reason": "Unable to evaluate relevance."}

        # --- Accuracy ---
        try:
            accuracy_result = self.accuracy_agent.evaluate(question, response, reference)
        except Exception as e:
            print("Accuracy Agent Error:", e)
            accuracy_result = {"score": 0, "evidence": "Unable to evaluate accuracy."}

        # --- Completeness ---
        try:
            completeness_result = self.completeness_agent.evaluate(question, response, reference)
        except Exception as e:
            print("Completeness Agent Error:", e)
            completeness_result = {
                "score": 0,
                "reason": "Unable to evaluate completeness.",
                "missing_aspects": [],
            }

        # --- Hallucination ---
        try:
            hallucination_result = self.hallucination_agent.evaluate(question, response, reference)
        except Exception as e:
            print("Hallucination Agent Error:", e)
            hallucination_result = {
                "score": 0,
                "reason": "Unable to evaluate hallucinations.",
                "unsupported_claims": [],
            }

        dimension_results = {
            "relevance": relevance_result,
            "accuracy": accuracy_result,
            "completeness": completeness_result,
            "hallucination": hallucination_result,
        }

        # --- Verdict (weighted aggregation + consolidated reasoning) ---
        try:
            verdict_result = self.verdict_agent.evaluate(question, response, dimension_results)
        except Exception as e:
            print("Verdict Agent Error:", e)
            # Fallback: simple average so a verdict is always produced.
            avg = round(
                (
                    relevance_result["score"]
                    + accuracy_result["score"]
                    + completeness_result["score"]
                    + hallucination_result["score"]
                ) / 4,
                2,
            )
            verdict_result = {
                "overall_score": avg,
                "verdict": "Pass" if avg >= 8 else ("Needs Improvement" if avg >= 5 else "Fail"),
                "summary": "Verdict agent unavailable; used simple average of the four dimensions.",
            }

        return {
            **dimension_results,
            "overall_score": verdict_result["overall_score"],
            "verdict": verdict_result["verdict"],
            "summary": verdict_result["summary"],
        }