# importere bibliotekker

from fastapi import FastAPI  # fastapi er en bibliotek, Fastapi er en klasse, En klasse er en skabelon til et objekt "tænk jeg vil bruge FastAPIs opskrift"
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
from backend.app.core.database import FingerprintSessionLocal
from backend.app.core.database import (
    fingerprint_engine,
    journal_engine,
    FingerprintBase,
    JournalBase,
)
from fastapi import Body
from sqlalchemy.orm import Session
from backend.app.models.patient import Patient

app = FastAPI()  # opretter et objekt, app er backend-applikationen. ALT backend hænger på app [Her starter mit system]


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
@app.get("/health")  # @ = dekorator (ændre adfærd af en funktion)
def root():
    return {"status": "ok"}


@app.get("/patients", response_class=HTMLResponse)
def patients(
    request: Request,  # Dette er en template, Alle templates skal have reguest # FastAPI bruger det internt #FastAPI regle
    db: Session = Depends(get_fingerprint_db),
):
    patients = db.query(Patient).all()

    return templates.TemplateResponse(  # Render html
        "patients.html",
        {
            "request": request,
            "patients": patients
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

    return RedirectResponse(
        url="/patients",
        status_code=303
    )

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


app.post("/fingerprint/verify")
def verify_fingerprint(
    fingerprint_id: int = Body(..., embed=True),
    db: Session = Depends(get_fingerprint_db),
):
    patient = db.query(Patient).filter(
        Patient.id == fingerprint_id
    ).first()

    if not patient:
        return {"match": False}

    return {
        "match": True,
        "patient_external_id": str(patient.external_id),
        "patient_name": patient.name,
    }


@app.post("/fingerprint/verify")
def verify_fingerprint(
    payload: FingerprintVerifyRequest,
    db: Session = Depends(get_fingerprint_db),
):
    patient = db.query(Patient).filter(
        Patient.id == payload.patient_id
    ).first()

    if not patient:
        return RedirectResponse(
            url="/patients?error=fingerprint_failed",
            status_code=303
        )

    return RedirectResponse(
        url=f"/patients?matched={patient.id}",
        status_code=303
    )