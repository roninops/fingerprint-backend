from sqlalchemy import create_engine
from backend.app.core.config import (
    FINGERPRINT_DB_URL,
    JOURNAL_DB_URL,
)

fingerprint_engine = create_engine(
    FINGERPRINT_DB_URL,
    pool_pre_ping=True,
    future=True,
)

journal_engine = create_engine(
    JOURNAL_DB_URL,
    pool_pre_ping=True,
    future=True,
)
