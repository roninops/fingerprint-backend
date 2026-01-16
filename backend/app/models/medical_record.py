from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.app.core.database import JournalBase


class MedicalRecord(JournalBase):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True)
    patient_external_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    age = Column(Integer, nullable=False)
    diagnosis = Column(Text, nullable=False)
    medication = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
