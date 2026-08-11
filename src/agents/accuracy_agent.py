from backend.llm import generate_response
from backend.utils import parse_json_response, clamp_score
from backend.retrieval import retrieve_context_text


class AccuracyJudge:
    """
    Milestone 2 - Agent 2.
    Checks factual correctness of the response against:
      1. an optional human-provided reference answer, and
      2. source chunks retrieved from the RAG knowledge base for the
         question (grounding evidence).
    """

    def evaluate(self, question: str, response: str, reference: str = "") -> dict:
        try:
            retrieved_context = retrieve_context_text(question, k=3)
        except FileNotFoundError:
            retrieved_context = ""

        prompt = f"""
You are an expert evaluator of AI responses.

Evaluate ONLY the factual accuracy of the AI response.

Question:
{question}

Reference Answer (may be empty):
{reference if reference else "(none provided)"}

Retrieved Source Evidence (from knowledge base, may be empty):
{retrieved_context if retrieved_context else "(no evidence retrieved)"}

AI Response:
{response}

Compare the AI response against the reference answer AND the retrieved
evidence. Base your judgment primarily on whichever source is available;
if both are available, they should agree with your ruling.

Return ONLY valid JSON in this exact format:
{{
    "score": number,
    "evidence": "brief explanation citing what supports or contradicts the response"
}}

Rules:
- Score between 1 and 10 (10 = fully accurate, 1 = completely wrong).
- Do not evaluate relevance or hallucinations here, only accuracy.
- Return ONLY the JSON object, no markdown.
"""
        raw = generate_response(prompt)
        result = parse_json_response(raw, "evidence")
        result["score"] = clamp_score(result.get("score", 0))
        result["retrieved_context"] = retrieved_context
        return result
