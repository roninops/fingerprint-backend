from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from backend.app.core.config import (
    FINGERPRINT_DB_URL,
    JOURNAL_DB_URL,
)

# ---------- FINGERPRINT / AUTH DB ----------

fingerprint_engine = create_engine(
    FINGERPRINT_DB_URL,
    pool_pre_ping=True,
    future=True,
)

FingerprintSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=fingerprint_engine,
    future=True,
)


class FingerprintBase(DeclarativeBase): # En Base samler alle metadata for models. # fortæller sqlAl and disse tabler høre sammen # bruger aembic til migrationer
    pass


# ---------- JOURNAL DB ----------

journal_engine = create_engine(
    JOURNAL_DB_URL,
    pool_pre_ping=True,
    future=True,
)

JournalSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=journal_engine,
    future=True,
)


class JournalBase(DeclarativeBase):
    pass
