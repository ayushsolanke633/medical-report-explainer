"""
routes/analysis.py
--------------------
Handles AI analysis of an uploaded report, translation of that
analysis, fetching a single report's full detail, and exporting a
downloadable PDF summary.
"""

import os
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from models.database import get_db
from models.user import User
from models.report import Report
from routes.auth import get_current_user
from schemas.report import ReportAnalysis, ReportDetail, TranslateRequest
from utils.gemini import analyze_report, GeminiError
from utils.translator import translate_analysis

logger = logging.getLogger("analysis")

router = APIRouter(tags=["Analysis"])

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "reports", "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


def _get_owned_report(report_id: int, current_user: User, db: Session) -> Report:
    """Fetches a report and ensures it belongs to the current user."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this report.")
    return report


@router.post("/analyze/{report_id}", response_model=ReportAnalysis)
def analyze(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs Gemini analysis on a previously uploaded report's extracted
    text, then stores and returns the structured result.
    """
    report = _get_owned_report(report_id, current_user, db)

    if not report.original_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This report has no extracted text to analyze.",
        )

    try:
        analysis_dict = analyze_report(report.original_text)
        analysis = ReportAnalysis(**analysis_dict)
    except GeminiError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        logger.exception("Analysis parsing failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unexpected format. Please try again.",
        )

    # Persist results onto the report row
    report.summary = analysis.patient_summary
    report.raw_analysis_json = analysis.model_dump_json()
    report.health_score = analysis.health_score
    report.risk_level = analysis.risk_level
    db.commit()
    db.refresh(report)

    return analysis


@router.post("/translate", response_model=ReportAnalysis)
def translate(
    payload: TranslateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Translates an already-analyzed report's explanation into the
    requested language ("en" or "mr") and returns it. Does not
    overwrite the original English analysis in the database.
    """
    report = _get_owned_report(payload.report_id, current_user, db)

    if not report.raw_analysis_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This report has not been analyzed yet. Call /analyze first.",
        )

    original_analysis = json.loads(report.raw_analysis_json)

    try:
        translated_dict = translate_analysis(original_analysis, payload.target_language)
        translated = ReportAnalysis(**translated_dict)
    except GeminiError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return translated


@router.get("/report/{report_id}", response_model=ReportDetail)
def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns full detail (metadata + stored analysis) for one report."""
    report = _get_owned_report(report_id, current_user, db)

    analysis = None
    if report.raw_analysis_json:
        analysis = ReportAnalysis(**json.loads(report.raw_analysis_json))

    return ReportDetail(
        id=report.id,
        report_name=report.report_name,
        hospital_name=report.hospital_name,
        summary=report.summary,
        health_score=report.health_score,
        risk_level=report.risk_level,
        language=report.language,
        created_at=report.created_at,
        analysis=analysis,
    )


@router.get("/download/{report_id}")
def download_summary_pdf(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates (or regenerates) a clean, printable PDF summary of the
    report's AI analysis and returns it as a file download.
    """
    report = _get_owned_report(report_id, current_user, db)

    if not report.raw_analysis_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This report has not been analyzed yet. Call /analyze first.",
        )

    analysis = ReportAnalysis(**json.loads(report.raw_analysis_json))
    output_path = os.path.join(EXPORT_DIR, f"summary_{report.id}.pdf")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], textColor=colors.HexColor("#1a56db"))
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading2"], textColor=colors.HexColor("#1a56db"), spaceBefore=14)
    disclaimer_style = ParagraphStyle("Disclaimer", parent=styles["Normal"], textColor=colors.HexColor("#b91c1c"), fontSize=9, spaceBefore=10)

    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = []

    story.append(Paragraph(f"Medical Report Summary — {report.report_name}", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Health Score: {analysis.health_score}/100  |  Risk Level: {analysis.risk_level}", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Patient Summary", heading_style))
    story.append(Paragraph(analysis.patient_summary, styles["Normal"]))

    story.append(Paragraph("Overall Health Summary", heading_style))
    story.append(Paragraph(analysis.overall_health_summary, styles["Normal"]))

    if analysis.key_findings:
        story.append(Paragraph("Key Findings", heading_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(item, styles["Normal"])) for item in analysis.key_findings],
            bulletType="bullet",
        ))

    if analysis.detected_tests:
        story.append(Paragraph("Detected Tests", heading_style))
        for test in analysis.detected_tests:
            story.append(Paragraph(
                f"<b>{test.test_name}</b> — {test.actual_value} (Normal: {test.normal_range}) "
                f"— Status: {test.status}",
                styles["Normal"],
            ))
            story.append(Paragraph(test.meaning, styles["Normal"]))
            story.append(Spacer(1, 6))

    if analysis.diet_advice:
        story.append(Paragraph("Diet Advice", heading_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(item, styles["Normal"])) for item in analysis.diet_advice],
            bulletType="bullet",
        ))

    if analysis.exercise_advice:
        story.append(Paragraph("Exercise Advice", heading_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(item, styles["Normal"])) for item in analysis.exercise_advice],
            bulletType="bullet",
        ))

    story.append(Paragraph("Doctor Recommendation", heading_style))
    story.append(Paragraph(analysis.doctor_recommendation, styles["Normal"]))

    if analysis.red_flags:
        story.append(Paragraph("Red Flags", heading_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(item, styles["Normal"])) for item in analysis.red_flags],
            bulletType="bullet",
        ))

    if analysis.emergency_signs:
        story.append(Paragraph("Emergency Signs — Seek Immediate Care If Present", heading_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(item, styles["Normal"])) for item in analysis.emergency_signs],
            bulletType="bullet",
        ))

    story.append(Paragraph(
        "This explanation is generated by AI and is for educational purposes only. "
        "It is NOT medical advice. Please consult a qualified doctor.",
        disclaimer_style,
    ))

    doc.build(story)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"{report.report_name.rsplit('.', 1)[0]}_summary.pdf",
    )
