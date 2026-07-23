"""
schemas/user.py
----------------
Pydantic models (request/response shapes) for authentication and
user profile endpoints: /register, /login, /profile.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="Aditi Sharma")
    email: EmailStr = Field(..., example="aditi@example.com")
    password: str = Field(..., min_length=6, max_length=72, example="StrongPass123")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True  # allows creation directly from ORM objects


class UserPublic(BaseModel):
    """Minimal safe-to-return user info (no password fields, ever)."""
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True
