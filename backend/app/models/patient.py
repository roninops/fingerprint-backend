import uuid
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.app.core.database import FingerprintBase

class Patient(FingerprintBase):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    external_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
