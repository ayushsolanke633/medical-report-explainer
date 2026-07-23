"""
schemas/token.py
-----------------
Pydantic models for JWT access tokens returned by /login and /register,
and the decoded payload used internally to identify the current user.
"""

from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None  # subject = user email
    exp: Optional[int] = None
