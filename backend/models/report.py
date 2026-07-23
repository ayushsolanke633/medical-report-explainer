"""
report.py
----------
SQLAlchemy ORM model representing a single uploaded medical report
and its AI-generated analysis.

`raw_analysis_json` stores the full structured Gemini response so the
frontend can re-render detailed test-by-test breakdowns without
re-calling the AI every time the report is viewed.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from models.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    report_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)  # stored PDF location on disk

    original_text = Column(Text, nullable=True)      # raw OCR/extracted text
    summary = Column(Text, nullable=True)             # human-readable patient summary
    raw_analysis_json = Column(Text, nullable=True)   # full structured Gemini JSON

    health_score = Column(Float, nullable=True)       # 0-100
    risk_level = Column(String(20), nullable=True)    # Low / Moderate / High

    hospital_name = Column(String(255), nullable=True)
    language = Column(String(10), default="en")        # "en" or "mr"

    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="reports")

    def __repr__(self):
        return f"<Report id={self.id} name={self.report_name} user_id={self.user_id}>"
