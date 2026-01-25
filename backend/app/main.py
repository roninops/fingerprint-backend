HEAD
from fastapi import FastAPI  # fastapi er en bibliotek, Fastapi er en klasse, En klasse er en skabelon til et objekt "tænk jeg vil bruge FastAPIs opskrift"
from fastapi import FastAPI  # fastapi er en bibliotek, Fastapi er en klasse, En klasse er en skabelon til et objekt "tænk at jeg vil bruge FastAPIs opskrift"
( add fingerprint backend, requirmenents and serial bridge)
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates  # importere FastAPIs template integration, og bygger ovenpå Ninja2
from fastapi import Form
from fastapi.responses import RedirectResponse
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from pydantic import BaseModel
from backend.app.core.database import FingerprintSessionLocal, JournalSessionLocal
from backend.app.core.database import (
    fingerprint_engine,
    journal_engine,
    FingerprintBase,
    JournalBase,
)
from fastapi import Body, Cookie
from sqlalchemy.orm import Session
from backend.app.models.patient import Patient
from backend.app.models.fingerprint import Fingerprint
from backend.app.models.medical_record import MedicalRecord
from backend.app.api import esp32
from backend.app.api.servo import unlock_servo
from typing import Optional
import requests
from datetime import datetime

app = FastAPI()  # opretter et objekt, app er backend-applikationen. ALT backend hænger på app [Her starter mit system]

# Register API routers
app.include_router(esp32.router)

# Admin credentials (simpel - til eksamen)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


def get_fingerprint_db():
    db = FingerprintSessionLocal()
    try:
        yield db
    finally:
        db.close()

class FingerprintVerifyRequest(BaseModel):
    patient_id: int

templates = Jinja2Templates(directory="backend/app/templates")  # Det er en stige fortæller Fastapt at her ligger HTML-filen


# tilføjer funktionalitet
@app.get("/")  # Root endpoint - velkomstside
def home():
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Fingerprint login side - SIMPEL med manuel input"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/health")  # @ = dekorator (ændre adfærd af en funktion)
def health():
    return {"status": "ok"}


def get_journal_db():
    db = JournalSessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/patients", response_class=HTMLResponse)
def patients(
    request: Request,  # Dette er en template, Alle templates skal have reguest # FastAPI bruger det internt #FastAPI regle
    db: Session = Depends(get_fingerprint_db),
):
    patients_list = db.query(Patient).all()
    
    # Hent fingerprints for hver patient
    for patient in patients_list:
        patient.fingerprint_count = db.query(Fingerprint).filter(
            Fingerprint.patient_id == patient.id
        ).count()

    return templates.TemplateResponse(  # Render html
        "patients.html",
        {
            "request": request,
            "patients": patients_list
        }
    )


@app.post("/patients")
def create_patient(
    name: str = Form(...),  # Fortæller FastAPI at data kommer fra html-formular
    db: Session = Depends(get_fingerprint_db),
):
    patient = Patient(
        name=name,
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Redirect til enrollment i stedet for tilbage til patients
    return RedirectResponse(
        url=f"/patient/{patient.id}/enroll",
        status_code=303
    )


@app.get("/patient/{patient_id}/journal", response_class=HTMLResponse)
def patient_journal(
    patient_id: int,
    request: Request,
    fp_db: Session = Depends(get_fingerprint_db),
    journal_db: Session = Depends(get_journal_db),
):
    # Hent patient fra fingerprint DB
    patient = fp_db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Hent journal fra journal DB
    records = journal_db.query(MedicalRecord).filter(
        MedicalRecord.patient_external_id == patient.external_id
    ).all()
    
    return templates.TemplateResponse(
        "journal.html",
        {
            "request": request,
            "patient": patient,
            "records": records
        }
    )


@app.post("/patient/{patient_id}/journal")
def create_journal_entry(
    patient_id: int,
    age: int = Form(...),
    diagnosis: str = Form(...),
    medication: str = Form(None),
    fp_db: Session = Depends(get_fingerprint_db),
    journal_db: Session = Depends(get_journal_db),
):
    # Hent patient
    patient = fp_db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Opret journal entry
    record = MedicalRecord(
        patient_external_id=patient.external_id,
        age=age,
        diagnosis=diagnosis,
        medication=medication or "Ingen"
    )
    
    journal_db.add(record)
    journal_db.commit()
    
    return RedirectResponse(
        url=f"/patient/{patient_id}/journal",
        status_code=303
    )


# Global variable til seneste scan (simpel cache)
latest_scan = {"slot": None, "timestamp": 0}
latest_enrollment = {"slot": None, "timestamp": 0}
voltage_history = []  # Liste af voltage målinger:
MAX_VOLTAGE_HISTORY = 100  # Max antal målinger i historik

@app.get("/api/latest-scan")
def get_latest_scan():
    """Return seneste scan fra ESP32"""
    import time
    # Hvis scan er ældre end 10 sekunder, ignorer
    if time.time() - latest_scan["timestamp"] > 10:
        return {"slot": None}
    return {"slot": latest_scan["slot"]}


@app.post("/api/report-scan")
def report_scan(slot: int):
    """ESP32 eller serial bridge rapporterer scan"""
    import time
    global latest_scan
    
    # Log scan
    print(f"[SCAN REPORT] Slot {slot} scannet kl. {time.strftime('%H:%M:%S')}")
    
    latest_scan = {"slot": slot, "timestamp": time.time()}
    return {"success": True}


@app.get("/api/latest-enrollment")
def get_latest_enrollment():
    """Return seneste enrollment fra ESP32"""
    import time
    if time.time() - latest_enrollment["timestamp"] > 30:
        return {"slot": None}
    return {"slot": latest_enrollment["slot"]}


@app.post("/api/report-enrollment")
def report_enrollment(data: dict = Body(...)):
    """ESP32 eller serial bridge rapporterer enrollment"""
    import time
    global latest_enrollment
    slot = data.get("slot")
    latest_enrollment = {"slot": slot, "timestamp": time.time()}
    return {"success": True, "slot": slot}


@app.post("/api/report-voltage")
def report_voltage(data: dict = Body(...)):
    """ESP32 eller serial bridge rapporterer voltage måling"""
    import time
    global voltage_history
    voltage = data.get("voltage")
    timestamp = time.time()
    
    # Tilføj til historik
    voltage_history.append({"voltage": voltage, "timestamp": timestamp})
    
    # Begræns historik til MAX_VOLTAGE_HISTORY
    if len(voltage_history) > MAX_VOLTAGE_HISTORY:
        voltage_history = voltage_history[-MAX_VOLTAGE_HISTORY:]
    
    return {"success": True, "voltage": voltage}


@app.get("/api/voltage-history")
def get_voltage_history():
    """Hent voltage historik til graf"""
    return {"history": voltage_history}


@app.get("/monitoring", response_class=HTMLResponse)
def monitoring_page(request: Request):
    """Voltage monitoring side med graf"""
    return templates.TemplateResponse("monitoring.html", {"request": request})


@app.get("/patient/{patient_id}/enroll", response_class=HTMLResponse)
def enroll_fingerprint_page(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_fingerprint_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Find næste ledige slot
    used_slots = db.query(Fingerprint.sensor_slot).filter(
        Fingerprint.patient_id == patient_id
    ).all()
    used_slot_numbers = [slot[0] for slot in used_slots]
    
    next_slot = 1
    while next_slot in used_slot_numbers:
        next_slot += 1
    
    return templates.TemplateResponse(
        "enroll.html",
        {
            "request": request,
            "patient": patient,
            "next_slot": next_slot
        }
    )


@app.post("/patient/{patient_id}/enroll")
def enroll_fingerprint_submit(
    patient_id: int,
    slot: int = Form(...),
    db: Session = Depends(get_fingerprint_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check om slot allerede bruges
    existing = db.query(Fingerprint).filter(
        Fingerprint.sensor_slot == slot
    ).first()
    
    if existing:
        old_patient = db.query(Patient).filter(Patient.id == existing.patient_id).first()
        old_name = old_patient.name if old_patient else "UNKNOWN"
        
        print(f"[ENROLL] ⚠️ Slot {slot} allerede brugt af {old_name} (ID: {old_patient.id if old_patient else '?'})")
        print(f"[ENROLL] Opdaterer til {patient.name} (ID: {patient_id})")
        
        # Opdater eksisterende fingerprint til denne patient
        existing.patient_id = patient_id
        db.commit()
    else:
        # Opret nyt fingerprint
        print(f"[ENROLL] ✅ Nyt fingeraftryk: Slot {slot} → {patient.name} (ID: {patient_id})")
        fingerprint = Fingerprint(
            patient_id=patient_id,
            sensor_slot=slot,
            template=b"enrolled_via_web"
        )
        db.add(fingerprint)
        db.commit()
    
    return RedirectResponse(
        url=f"/patient/{patient_id}/journal",
        status_code=303
    )


@app.post("/patient/{patient_id}/take-photo")
def take_patient_photo(
    patient_id: int,
    db: Session = Depends(get_fingerprint_db),
):
    """Tag billede via Raspberry Pi camera"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Send request til Raspberry Pi
    # TODO: 
    pi_ip = "192.168.1.100" 
    
    try:
        response = requests.post(
            f"http://{pi_ip}:5000/take-photo",
            json={"patient_id": patient_id},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                # Gem photo path i database
                patient.photo_path = data.get("photo_path")
                db.commit()
                
                return {
                    "success": True,
                    "photo_path": data.get("photo_path"),
                    "message": "Billede taget og gemt"
                }
        
        return {"success": False, "error": "Kunne ikke tage billede"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/patient/{patient_id}/unlock")
def unlock_patient_door(
    patient_id: int,
    duration: int = 2,
    db: Session = Depends(get_fingerprint_db),
):
    """Åbn lås via ESP32 servo"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Åbn lås via servo
    result = unlock_servo(duration)
    
    return result


@app.get("/db-test")
def db_test():
    with fingerprint_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    with journal_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {"status": "Begge databaser svarer"}


@app.on_event("startup")
def init_db():
    FingerprintBase.metadata.create_all(bind=fingerprint_engine)
    JournalBase.metadata.create_all(bind=journal_engine)


@app.post("/fingerprint/verify")
def verify_fingerprint(
    payload: FingerprintVerifyRequest,
    db: Session = Depends(get_fingerprint_db),
):
    """Verify fingerprint and return patient info or redirect based on match"""
    patient = db.query(Patient).filter(
        Patient.id == payload.patient_id
    ).first()

    if not patient:
        return {"match": False, "error": "Patient not found"}

<<<<<<< HEAD
    return RedirectResponse(
        url=f"/patients?matched={patient.id}",
        status_code=303
    )
=======
    return {
        "match": True,
        "patient_id": patient.id,
        "patient_external_id": str(patient.external_id),
        "patient_name": patient.name,
    }


# ADMIN ROUTES

@app.get("/admin", response_class=HTMLResponse)
def admin_login_page(request: Request, error: Optional[str] = None):
    """Admin login side"""
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": error})


@app.post("/admin/login")
def admin_login(
    username: str = Form(...),
    password: str = Form(...),
):
    """Admin login"""
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie("admin_session", "authenticated")
        return response
    else:
        return RedirectResponse(url="/admin?error=Forkert brugernavn eller adgangskode", status_code=303)


@app.get("/admin/logout")
def admin_logout():
    """Admin logout"""
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    admin_session: Optional[str] = Cookie(None),
    fp_db: Session = Depends(get_fingerprint_db),
    journal_db: Session = Depends(get_journal_db),
):
    """Admin dashboard"""
    # Check authentication
    if admin_session != "authenticated":
        return RedirectResponse(url="/admin")
    
    # Get all patients med fingerprint count
    patients = fp_db.query(Patient).all()
    for patient in patients:
        patient.fingerprint_count = fp_db.query(Fingerprint).filter(
            Fingerprint.patient_id == patient.id
        ).count()
    
    # Get total fingerprints
    total_fingerprints = fp_db.query(Fingerprint).count()
    
    # Get total journal records
    total_records = journal_db.query(MedicalRecord).count()
    
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "patients": patients,
            "total_fingerprints": total_fingerprints,
            "total_records": total_records
        }
    )


@app.post("/admin/patient/{patient_id}/edit")
def admin_edit_patient(
    patient_id: int,
    name: str = Body(..., embed=True),
    admin_session: Optional[str] = Cookie(None),
    db: Session = Depends(get_fingerprint_db),
):
    """Edit patient navn"""
    if admin_session != "authenticated":
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient.name = name
    db.commit()
    
    return {"success": True}


@app.delete("/admin/patient/{patient_id}/delete")
def admin_delete_patient(
    patient_id: int,
    admin_session: Optional[str] = Cookie(None),
    fp_db: Session = Depends(get_fingerprint_db),
    journal_db: Session = Depends(get_journal_db),
):
    """Delete patient and all data"""
    if admin_session != "authenticated":
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    patient = fp_db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Slet fingerprints
    fp_db.query(Fingerprint).filter(Fingerprint.patient_id == patient_id).delete()
    
    # Slet journal entries
    journal_db.query(MedicalRecord).filter(
        MedicalRecord.patient_external_id == patient.external_id
    ).delete()
    journal_db.commit()
    
    # Slet patient
    fp_db.delete(patient)
    fp_db.commit()
    
    return {"success": True}
>>>>>>> 1c5697b ( add fingerprint backend, requirmenents and serial bridge)
