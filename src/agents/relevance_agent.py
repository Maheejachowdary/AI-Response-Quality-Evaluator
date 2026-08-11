from backend.llm import generate_response
from backend.utils import parse_json_response, clamp_score


class RelevanceJudge:
    """
    Milestone 2 - Agent 1.
    Scores how directly the AI response addresses the question asked,
    independent of factual correctness (accuracy is scored separately).
    """

    def evaluate(self, question: str, response: str) -> dict:
        prompt = f"""
You are an expert evaluator of AI responses.

Evaluate ONLY the relevance of the response to the question.
Relevance means: does the response actually address what was asked,
regardless of whether the answer is factually correct?

Question:
{question}

AI Response:
{response}

Return ONLY valid JSON in this exact format:
{{
    "score": number,
    "reason": "short explanation"
}}

Rules:
- Score between 1 and 10 (10 = fully addresses the question, 1 = off-topic).
- Do NOT evaluate factual accuracy here.
- Do NOT use markdown or ```json fences.
- Return ONLY the JSON object.
"""
        raw = generate_response(prompt)
        result = parse_json_response(raw, "reason")
        result["score"] = clamp_score(result.get("score", 0))
        return result
