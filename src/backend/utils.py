import json
import re


def parse_json_response(response_text: str, default_key: str) -> dict:
    """
    Safely parses JSON returned by the LLM.
    Handles markdown fences and prose wrapped around the JSON object.
    """
    text = (response_text or "").strip()

    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    result = {
        "score": 0,
        default_key: f"Could not parse evaluator output. Raw: {text[:300]}",
        "_error": response_text,
    }
    if default_key == "reason":
        result.setdefault("unsupported_claims", [])
    return result


def clamp_score(value, low=1, high=10):
    """Ensures a score always stays within the expected 1-10 range."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, value))