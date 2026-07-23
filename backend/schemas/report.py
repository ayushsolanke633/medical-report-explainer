"""
schemas/report.py
------------------
Pydantic models for report upload, AI analysis results, and history
listing/detail endpoints.

These mirror the structured JSON we ask Gemini to return (see
utils/prompt.py) so the API responses are consistent and typed.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DetectedTest(BaseModel):
    test_name: str
    normal_range: str
    actual_value: str
    status: str = Field(..., description="Green | Yellow | Red")
    meaning: str
    possible_causes: List[str] = []
    lifestyle_suggestions: List[str] = []
    diet_suggestions: List[str] = []
    when_to_consult_doctor: str


class ReportAnalysis(BaseModel):
    patient_summary: str
    overall_health_summary: str
    key_findings: List[str] = []
    health_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="Low | Moderate | High")
    detected_tests: List[DetectedTest] = []
    diet_advice: List[str] = []
    exercise_advice: List[str] = []
    doctor_recommendation: str
    red_flags: List[str] = []
    emergency_signs: List[str] = []


class ReportUploadResponse(BaseModel):
    report_id: int
    report_name: str
    message: str = "File uploaded successfully. Analysis in progress."


class ReportDetail(BaseModel):
    id: int
    report_name: str
    hospital_name: Optional[str] = None
    summary: Optional[str] = None
    health_score: Optional[float] = None
    risk_level: Optional[str] = None
    language: str
    created_at: datetime
    analysis: Optional[ReportAnalysis] = None

    class Config:
        from_attributes = True


class ReportHistoryItem(BaseModel):
    id: int
    report_name: str
    hospital_name: Optional[str] = None
    health_score: Optional[float] = None
    risk_level: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TranslateRequest(BaseModel):
    report_id: int
    target_language: str = Field(..., description="'en' or 'mr'")
