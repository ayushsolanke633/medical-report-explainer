"""
routes/upload.py
------------------
Handles secure upload of medical report PDFs.

Flow:
  1. Validate file type (.pdf only) and size (<= MAX_UPLOAD_MB).
  2. Save the file to backend/uploads/reports/ with a unique filename.
  3. Run OCR/text extraction immediately (pdfplumber -> pytesseract fallback).
  4. Create a Report row (without AI analysis yet — that happens via
     POST /analyze so the user can see "uploaded" state quickly and
     the AI call can be triggered/retried independently).
"""

import os
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.user import User
from models.report import Report
from routes.auth import get_current_user
from schemas.report import ReportUploadResponse
from utils.ocr import extract_text_from_pdf, OCRError

logger = logging.getLogger("upload")

router = APIRouter(tags=["Upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "reports")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_CONTENT_TYPE = "application/pdf"


@router.post("/upload", response_model=ReportUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    file: UploadFile = File(...),
    hospital_name: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accepts a PDF medical report, validates it, extracts its text, and
    stores it as a new Report belonging to the current user.
    """
    # --- Validate file type ---
    if file.content_type != ALLOWED_CONTENT_TYPE and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    # --- Read into memory once, validate size ---
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_UPLOAD_MB}MB size limit.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # --- Save with a unique, sanitized filename ---
    safe_original_name = os.path.basename(file.filename).replace(" ", "_")
    unique_filename = f"{uuid.uuid4().hex}_{safe_original_name}"
    saved_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # --- Extract text (digital or OCR fallback) ---
    try:
        extracted_text = extract_text_from_pdf(saved_path)
    except OCRError as exc:
        # Clean up the saved file since it's unusable
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected OCR failure")
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the uploaded file.",
        )

    # --- Persist Report row ---
    new_report = Report(
        user_id=current_user.id,
        report_name=safe_original_name,
        file_path=saved_path,
        original_text=extracted_text,
        hospital_name=hospital_name,
        language="en",
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return ReportUploadResponse(
        report_id=new_report.id,
        report_name=new_report.report_name,
        message="File uploaded and text extracted successfully. Call /analyze to generate the AI explanation.",
    )
