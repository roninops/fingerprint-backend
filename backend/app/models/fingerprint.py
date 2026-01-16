from sqlalchemy import Column, Integer, LargeBinary, ForeignKey, DateTime
from sqlalchemy.sql import func

from backend.app.core.database import FingerprintBase


class Fingerprint(FingerprintBase):
    __tablename__ = "fingerprints"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    template = Column(LargeBinary, nullable=False)
    sensor_slot = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
