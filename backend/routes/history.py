"""
routes/history.py
-------------------
Handles listing a user's report history (with optional search) and
deleting reports (including their stored PDF file on disk).
"""

import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.database import get_db
from models.user import User
from models.report import Report
from routes.auth import get_current_user
from schemas.report import ReportHistoryItem

logger = logging.getLogger("history")

router = APIRouter(tags=["History"])


@router.get("/history", response_model=list[ReportHistoryItem])
def get_history(
    search: str | None = Query(default=None, description="Search by report name or hospital name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the current user's report history, newest first, with
    optional search across report_name and hospital_name.
    """
    query = db.query(Report).filter(Report.user_id == current_user.id)

    if search:
        like_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Report.report_name.ilike(like_pattern),
                Report.hospital_name.ilike(like_pattern),
            )
        )

    reports = query.order_by(Report.created_at.desc()).all()
    return reports


@router.delete("/delete/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a report row and its associated uploaded PDF file."""
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this report.")

    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except OSError as exc:
            logger.warning("Could not delete file %s: %s", report.file_path, exc)

    db.delete(report)
    db.commit()

    return {"message": "Report deleted successfully.", "report_id": report_id}
