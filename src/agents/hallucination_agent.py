from backend.llm import generate_response
from backend.utils import parse_json_response, clamp_score
from backend.retrieval import retrieve_context_text


class HallucinationJudge:
    """
    Milestone 2 - Agent 3.
    Identifies unsupported claims in the AI response by cross-referencing
    every factual statement against RAG-retrieved source content (and the
    reference answer, if one was supplied).
    """

    def evaluate(self, question: str, response: str, reference: str = "") -> dict:
        try:
            retrieved_context = retrieve_context_text(question, k=3)
        except FileNotFoundError:
            retrieved_context = ""

        grounding = "\n\n".join(
            part for part in [
                f"Reference Answer:\n{reference}" if reference else "",
                f"Retrieved Source Content:\n{retrieved_context}" if retrieved_context else "",
            ] if part
        ) or "(no grounding evidence available)"

        prompt = f"""
You are an expert evaluator detecting hallucinations in AI-generated responses.

Question:
{question}

Grounding Evidence:
{grounding}

AI Response:
{response}

Go through every substantive factual claim in the AI response.
A claim is a verifiable factual assertion. Ignore rhetorical framing,
transitions, summaries, and section headings ("Here is a breakdown...",
"The short answer is...") - these are not claims.

For each claim, decide whether it is a hallucination. A claim is
UNSUPPORTED only if it is fabricated, unverifiable, or CONTRADICTED by
the grounding evidence.

A claim is NOT a hallucination merely because it adds detail beyond the
grounding evidence. The reference answer is a brief summary, not an
exhaustive source. Well-established general knowledge that is consistent
with the evidence is acceptable. Only flag claims that conflict with the
evidence or that assert specific facts (names, dates, figures, studies)
that appear fabricated.

Return ONLY valid JSON in this exact format:
{{
    "score": number,
    "unsupported_claims": ["claim 1", "claim 2"],
    "reason": "short explanation of your overall judgment"
}}

Rules:
- Score between 1 and 10 (10 = fully grounded, no hallucinations, 1 = mostly fabricated).
- If every statement is supported, return an empty list for unsupported_claims.
- If there is no grounding evidence at all, say so in "reason" and score conservatively.
- Return ONLY the JSON object, no markdown.
"""
        raw = generate_response(prompt)
        result = parse_json_response(raw, "reason")
        result["score"] = clamp_score(result.get("score", 0))
        result.setdefault("unsupported_claims", [])
        result.setdefault("reason", "")
        result["retrieved_context"] = retrieved_context
        return result
