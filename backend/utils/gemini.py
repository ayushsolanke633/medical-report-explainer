"""
utils/gemini.py
-----------------
Thin wrapper around the google-generativeai SDK. Handles:
  - Configuring the Gemini client with the API key from .env
  - Sending the structured analysis prompt and parsing JSON safely
  - Sending translation prompts
  - Defensive error handling so a bad/empty AI response never crashes
    the API — callers always get a usable dict or a clear exception.
"""

import os
import json
import re
import logging

import google.generativeai as genai
from dotenv import load_dotenv

from utils.prompt import build_analysis_prompt, build_translation_prompt

load_dotenv()

logger = logging.getLogger("gemini")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not GEMINI_API_KEY:
    logger.warning(
        "GEMINI_API_KEY is not set. Add it to your .env file before "
        "calling any AI analysis endpoints."
    )
else:
    genai.configure(api_key=GEMINI_API_KEY)


class GeminiError(Exception):
    """Raised when the Gemini API call fails or returns unusable data."""
    pass


def _get_model():
    if not GEMINI_API_KEY:
        raise GeminiError(
            "Gemini API key is missing. Set GEMINI_API_KEY in your .env file."
        )
    return genai.GenerativeModel(GEMINI_MODEL_NAME)


def _extract_json(raw_text: str) -> dict:
    """
    Gemini sometimes wraps JSON in ```json ... ``` fences despite
    instructions not to. This strips any fencing/whitespace and
    safely parses the result.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Try to salvage the largest {...} block in the text as a fallback
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise GeminiError(f"Gemini did not return valid JSON: {exc}") from exc


def analyze_report(report_text: str, patient_context: str = "") -> dict:
    """
    Sends extracted report text to Gemini and returns the parsed
    structured analysis dict matching schemas.report.ReportAnalysis.

    Raises:
        GeminiError: if the API call fails or the response isn't
                     parseable JSON.
    """
    if not report_text or not report_text.strip():
        raise GeminiError("No text was extracted from the uploaded report.")

    model = _get_model()
    prompt = build_analysis_prompt(report_text, patient_context)

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,  # low temperature for consistent, factual output
                "max_output_tokens": 4096,
            },
        )
    except Exception as exc:  # network / SDK errors
        logger.exception("Gemini API call failed")
        raise GeminiError(f"Gemini API request failed: {exc}") from exc

    if not response or not getattr(response, "text", None):
        raise GeminiError("Gemini returned an empty response.")

    return _extract_json(response.text)


def translate_text(text: str, target_language: str) -> str:
    """
    Translates a block of explanation text into the target language
    ("mr" for Marathi). Returns plain translated text (not JSON).
    """
    if target_language == "en":
        return text  # no-op, already English

    model = _get_model()
    prompt = build_translation_prompt(text, target_language)

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 2048},
        )
    except Exception as exc:
        logger.exception("Gemini translation call failed")
        raise GeminiError(f"Gemini translation request failed: {exc}") from exc

    if not response or not getattr(response, "text", None):
        raise GeminiError("Gemini returned an empty translation response.")

    return response.text.strip()
