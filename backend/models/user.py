"""
user.py
--------
SQLAlchemy ORM model representing an application user.

Passwords are NEVER stored in plaintext — see utils handled in
routes/auth.py, which hashes passwords with passlib (bcrypt) before
saving them here.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One user can have many uploaded/analyzed reports
    reports = relationship(
        "Report",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
