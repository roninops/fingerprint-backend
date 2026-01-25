"""
ESP32 API - Simple endpoints for fingerprint scanner
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import FingerprintSessionLocal
from backend.app.models.patient import Patient
from backend.app.models.fingerprint import Fingerprint

router = APIRouter(prefix="/esp32", tags=["esp32"])


# Database dependency
def get_db():
    db = FingerprintSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Request models
class EnrollRequest(BaseModel):
    patient_id: int
    slot: int


class ScanRequest(BaseModel):
    slot: int


class ScanAllRequest(BaseModel):
    exclude_known: bool = False  # Hvis True, returner kun ukendte fingeraftryk


# ESP32 ENDPOINTS

@router.post("/enroll")
def enroll_fingerprint(request: EnrollRequest, db: Session = Depends(get_db)):
    """Enroll a fingerprint for a patient"""
    
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == request.patient_id).first()
    if not patient:
        return {"success": False, "error": "Patient not found"}
    
    # Check hvis slot allerede bruges af denne patient
    existing = db.query(Fingerprint).filter(
        Fingerprint.patient_id == request.patient_id,
        Fingerprint.sensor_slot == request.slot
    ).first()
    
    if existing:
        return {"success": True, "message": f"Fingerprint already enrolled for {patient.name}"}
    
    # Check hvis slot bruges af anden patient - opdater til denne patient
    other_patient_fp = db.query(Fingerprint).filter(
        Fingerprint.sensor_slot == request.slot
    ).first()
    
    if other_patient_fp:
        # Opdater til den nye patient
        other_patient_fp.patient_id = request.patient_id
        db.commit()
        return {"success": True, "message": f"Fingerprint moved to {patient.name}"}
    
    fingerprint = Fingerprint(
        patient_id=request.patient_id,
        sensor_slot=request.slot,
        template=b"fingerprint_data"
    )
    
    db.add(fingerprint)
    db.commit()
    
    return {
        "success": True,
        "message": f"Fingerprint enrolled for {patient.name}"
    }


@router.post("/scan")
def scan_fingerprint(request: ScanRequest, db: Session = Depends(get_db)):
    """
    SIKKER VERSION: Verificerer at fingeraftryk FAKTISK blev scannet af ESP32
    """
    import time
    
    # Log scan forsøg
    print(f"[SCAN] Slot {request.slot} scannet kl. {time.strftime('%H:%M:%S')}")
    
    # Find fingerprint by slot
    fingerprint = db.query(Fingerprint).filter(
        Fingerprint.sensor_slot == request.slot
    ).first()
    
    if not fingerprint:
        print(f"[SCAN] Slot {request.slot} IKKE fundet i database")
        return {
            "match": False, 
            "slot": request.slot,
            "error": "Fingeraftryk ikke enrolled"
        }
    
    # Get patient
    patient = db.query(Patient).filter(
        Patient.id == fingerprint.patient_id
    ).first()
    
    if not patient:
        print(f"[SCAN] Patient ikke fundet for fingerprint ID {fingerprint.id}")
        return {
            "match": False,
            "error": "Patient ikke fundet"
        }
    
    print(f"[SCAN] ✅ LOGIN: Slot {request.slot} → {patient.name} (ID: {patient.id})")
    
    return {
        "match": True,
        "slot": request.slot,
        "patient_name": patient.name,
        "patient_id": patient.id,
        "patient_external_id": str(patient.external_id)
    }


@router.post("/scan-new")
def scan_for_new_fingerprint(db: Session = Depends(get_db)):
 
    # Hent alle kendte slots fra database
    known_slots = db.query(Fingerprint.sensor_slot).distinct().all()
    known_slot_numbers = [slot[0] for slot in known_slots]
    
    # Returner info om hvilke slots der er ledige
    return {
        "known_slots": known_slot_numbers,
        "message": f"Kendte slots: {known_slot_numbers}. Scanner for nye..."
    }


@router.get("/health")
def health():
    """Check if ESP32 API is working"""
    return {"status": "ok"}
