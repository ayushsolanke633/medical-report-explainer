"""
utils/prompt.py
-----------------
Builds the structured prompt sent to Gemini so it always returns a
predictable JSON object matching schemas.report.ReportAnalysis.

Keeping the prompt in one place makes it easy to tune wording without
touching the API-calling code in utils/gemini.py.
"""

# JSON schema description embedded directly in the prompt so Gemini
# knows exactly which keys/types to return.
RESPONSE_JSON_SPEC = """
Return ONLY a valid JSON object (no markdown, no code fences, no extra
commentary) with EXACTLY this structure:

{
  "patient_summary": "string - a warm, plain-language 3-5 sentence summary written directly to the patient",
  "overall_health_summary": "string - 2-3 sentence overview of general health status based on this report",
  "key_findings": ["string", "..."],
  "health_score": number between 0 and 100,
  "risk_level": "Low" | "Moderate" | "High",
  "detected_tests": [
    {
      "test_name": "string, e.g. Hemoglobin",
      "normal_range": "string, e.g. 13.0 - 17.0 g/dL",
      "actual_value": "string, e.g. 10.2 g/dL",
      "status": "Green" | "Yellow" | "Red",
      "meaning": "string - what this test measures and what this result means, in simple language",
      "possible_causes": ["string", "..."],
      "lifestyle_suggestions": ["string", "..."],
      "diet_suggestions": ["string", "..."],
      "when_to_consult_doctor": "string - clear guidance on when this specific result warrants a doctor visit"
    }
  ],
  "diet_advice": ["string", "..."],
  "exercise_advice": ["string", "..."],
  "doctor_recommendation": "string - overall recommendation on whether/when to see a doctor",
  "red_flags": ["string", "..."],
  "emergency_signs": ["string - symptoms that would require IMMEDIATE emergency care, if any apply"]
}
"""

SYSTEM_INSTRUCTIONS = """
You are a medical report explainer AI assistant. Your ONLY job is to
translate clinical lab report data into simple, compassionate,
easy-to-understand language for a non-medical person.

Rules you MUST follow:
1. NEVER provide a diagnosis. Only explain what the report data shows.
2. ALWAYS recommend consulting a qualified doctor for interpretation
   and treatment decisions.
3. Use simple, non-alarming, everyday language. Avoid jargon; when a
   medical term is unavoidable, briefly explain it in parentheses.
4. Classify each test result as Green (normal), Yellow (borderline /
   slightly outside range), or Red (significantly outside range).
5. If any values suggest a potential medical emergency (e.g.
   dangerously low hemoglobin, very high blood glucose, critical
   potassium levels), list them clearly under "emergency_signs" and
   advise seeking immediate care.
6. Be encouraging and supportive in tone — never cause unnecessary
   alarm, but be honest about risk levels.
7. Base your entire response strictly on the report text provided.
   Do not invent values that are not present in the text.
8. Output MUST be valid JSON only, matching the schema exactly.
"""


def build_analysis_prompt(report_text: str, patient_context: str = "") -> str:
    """
    Assembles the final prompt string sent to Gemini for full report
    analysis.

    Args:
        report_text: Raw text extracted via OCR/pdfplumber/PyMuPDF from
                      the uploaded medical report.
        patient_context: Optional extra context (age, gender, known
                          conditions) if provided by the user later.

    Returns:
        Complete prompt string ready to send to the Gemini API.
    """
    context_block = f"\nAdditional patient context: {patient_context}\n" if patient_context else ""

    prompt = f"""{SYSTEM_INSTRUCTIONS}

Below is the extracted text of a patient's medical report:

--- REPORT TEXT START ---
{report_text}
--- REPORT TEXT END ---
{context_block}
{RESPONSE_JSON_SPEC}
"""
    return prompt.strip()


def build_translation_prompt(text: str, target_language: str) -> str:
    """
    Builds a simple prompt to translate already-generated explanation
    text into the target language while preserving medical meaning.

    Args:
        text: The English explanation text to translate.
        target_language: "mr" for Marathi (currently supported target).

    Returns:
        Prompt string for the translation call.
    """
    language_name = "Marathi" if target_language == "mr" else "English"

    return f"""Translate the following medical explanation into {language_name}.
Keep the tone warm and simple. Preserve all numbers, test names, and
medical values exactly as given. Return ONLY the translated text, with
no extra commentary or markdown.

--- TEXT START ---
{text}
--- TEXT END ---
"""
