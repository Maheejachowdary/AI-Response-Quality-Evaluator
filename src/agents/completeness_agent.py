from backend.llm import generate_response
from backend.utils import parse_json_response, clamp_score
from backend.retrieval import retrieve_context_text


class CompletenessJudge:
    """
    Milestone 3 - Agent 4.
    Assesses whether the AI response addresses ALL aspects of the question.
    A question may contain several parts (e.g. "what is X and why does it
    matter?"); this judge checks coverage and lists specific omissions.

    Independent of relevance and accuracy: a response can be on-topic and
    factually correct yet still incomplete (answering only part of what was
    asked).
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
You are an expert evaluator assessing the COMPLETENESS of an AI response.

Completeness means: does the response address every distinct part of the
question that was asked? A question may ask for several things at once
(e.g. a definition AND a cause AND an example). Judge ONLY coverage here -
ignore factual accuracy and ignore relevance.

Question:
{question}

Optional Grounding Evidence (a guide to what a full answer may include;
it is NOT a checklist, and the response need not mention everything in it):
{grounding}

AI Response:
{response}

Steps:
1. Break the question into its distinct required aspects / sub-parts.
2. For each aspect, decide whether the response addresses it.
3. List the aspects that are MISSING or only superficially addressed.

Return ONLY valid JSON in this exact format:
{{
    "score": number,
    "missing_aspects": ["aspect 1", "aspect 2"],
    "reason": "short explanation of what was and was not covered"
}}

Rules:
- Score between 1 and 10 (10 = every part of the question fully addressed,
  1 = almost nothing that was asked for was covered).
- If the question asks only one thing and the response covers it, that is
  complete - return an empty list and a high score.
- Do NOT penalise a response for extra detail; only for omissions.
- Return ONLY the JSON object, no markdown.
"""
        raw = generate_response(prompt)
        result = parse_json_response(raw, "reason")
        result["score"] = clamp_score(result.get("score", 0))
        result.setdefault("missing_aspects", [])
        result.setdefault("reason", "")
        result["retrieved_context"] = retrieved_context
        return result