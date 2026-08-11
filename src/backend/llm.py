"""
Thin wrapper around the Google Gemini API.
Every judge agent calls generate_response() to get raw model output.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Copy .env.example to .env and add your key."
    )

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.5-flash-lite")


def generate_response(prompt: str) -> str:
    """
    Sends a prompt to Gemini and returns cleaned text.
    Raises on API failure so callers can distinguish an error
    from a genuine model response.
    """
    response = model.generate_content(prompt)
    text = response.text.strip()

    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
    if text.endswith("```"):
        text = text[:-3]

    return text.strip()