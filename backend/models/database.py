"""
database.py
------------
Sets up the SQLAlchemy engine, session factory, and declarative Base
used across all ORM models (User, Report).

Uses SQLite for simplicity — swap DATABASE_URL in .env to switch to
Postgres/MySQL later without changing any model code.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medical_reports.db")

# SQLite requires this extra arg when used with FastAPI's threaded requests
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a database session and
    guarantees it is closed after the request finishes.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all tables defined by models that inherit from Base.
    Called once on application startup (see main.py).
    """
    # Import models here (not at top) to avoid circular imports
    from models import user, report  # noqa: F401
    Base.metadata.create_all(bind=engine)
