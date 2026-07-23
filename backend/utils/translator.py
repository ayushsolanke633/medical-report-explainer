"""
utils/translator.py
---------------------
Handles translating a full structured report analysis (not just a
single string) between English and Marathi.

Rather than translating one giant JSON blob (which risks Gemini
breaking the JSON structure), we translate the human-readable text
fields individually and leave numeric/status fields untouched.
"""

import logging
from typing import Any

from utils.gemini import translate_text, GeminiError

logger = logging.getLogger("translator")

SUPPORTED_LANGUAGES = {"en", "mr"}

# Fields in a ReportAnalysis-shaped dict that contain human-readable
# text and should be translated. Everything else (health_score,
# status, ranges, values) is left as-is since translating numbers/
# codes would be meaningless or risky.
TRANSLATABLE_TOP_LEVEL_FIELDS = [
    "patient_summary",
    "overall_health_summary",
    "doctor_recommendation",
]

TRANSLATABLE_LIST_FIELDS = [
    "key_findings",
    "diet_advice",
    "exercise_advice",
    "red_flags",
    "emergency_signs",
]

TRANSLATABLE_TEST_FIELDS = [
    "meaning",
    "when_to_consult_doctor",
]

TRANSLATABLE_TEST_LIST_FIELDS = [
    "possible_causes",
    "lifestyle_suggestions",
    "diet_suggestions",
]


def _translate_list(items: list[str], target_language: str) -> list[str]:
    if not items:
        return items
    # Join with a delimiter unlikely to appear in medical text, translate
    # once (cheaper than one call per item), then split back apart.
    delimiter = "\n---ITEM---\n"
    joined = delimiter.join(items)
    translated = translate_text(joined, target_language)
    parts = [p.strip() for p in translated.split(delimiter)]
    # Safety net: if splitting produced a mismatched count, fall back
    # to per-item translation to avoid silently losing content.
    if len(parts) != len(items):
        return [translate_text(item, target_language) for item in items]
    return parts


def translate_analysis(analysis: dict[str, Any], target_language: str) -> dict[str, Any]:
    """
    Returns a new analysis dict with all human-readable text fields
    translated into target_language ("en" or "mr"). Numeric/status
    fields (health_score, risk_level, status, normal_range,
    actual_value, test_name) are preserved exactly.
    """
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {target_language}")

    if target_language == "en":
        return analysis  # analysis is generated in English by default

    translated = dict(analysis)

    try:
        for field in TRANSLATABLE_TOP_LEVEL_FIELDS:
            if translated.get(field):
                translated[field] = translate_text(translated[field], target_language)

        for field in TRANSLATABLE_LIST_FIELDS:
            if translated.get(field):
                translated[field] = _translate_list(translated[field], target_language)

        if translated.get("detected_tests"):
            new_tests = []
            for test in translated["detected_tests"]:
                test_copy = dict(test)
                for field in TRANSLATABLE_TEST_FIELDS:
                    if test_copy.get(field):
                        test_copy[field] = translate_text(test_copy[field], target_language)
                for field in TRANSLATABLE_TEST_LIST_FIELDS:
                    if test_copy.get(field):
                        test_copy[field] = _translate_list(test_copy[field], target_language)
                new_tests.append(test_copy)
            translated["detected_tests"] = new_tests

    except GeminiError as exc:
        logger.warning("Translation partially failed: %s", exc)
        # Return whatever was successfully translated rather than
        # failing the whole request.

    return translated
