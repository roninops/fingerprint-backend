# importere bibliotekker

from fastapi import FastAPI # fastapi er en bibliotek, Fastapi er en klasse, En klasse er en skabelon til et objekt "tænk jeg vil bruge FastAPIs opskrift"
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates #importere FastAPIs template integration, og bygger ovenpå Ninja2
from fastapi import Form
from fastapi.responses import RedirectResponse
from sqlalchemy import text

app = FastAPI() #opretter et objekt, app er backend-applikationen. ALT backend hænger på app [Her starter mit system]

templates = Jinja2Templates(directory="backend/app/templates") # Det er en stige fortæller Fastapt at her ligger HTML-filen

#tilføjer funktionalitet
@app.get("/health") # @ = dekorator (ændre adfærd af en funktion)
def root():
    return{"status": "ok"}

@app.get("/patients", response_class=HTMLResponse)
def patients(request: Request): # Dette er en template, Alle templates skal have reguest # FastAPI bruger det internt #FastAPI regle
    patients = [
        {"id": 1, "name": "Anna Jensen", "age": 34},
        {"id": 2, "name": "Peter Hansen", "age": 52},
        {"id": 3, "name": "Maria Sørensen", "age": 27},
    ]

    return templates.TemplateResponse( # Render html
        "patients.html",
        {
            "request": request,
            "patients": patients
        }
    )


@app.post("/patients")
def create_patient(
    name: str = Form(...), # Fortæller FastAPI at data kommer fra html-formular
    age: int = Form(...)
):
    print(f"Ny patient: {name}, {age}")

    return RedirectResponse(
        url="/patients",
        status_code=303
    )

from sqlalchemy import text
from backend.app.core.database import (
    fingerprint_engine,
    journal_engine,
)

@app.get("/db-test")
def db_test():
    with fingerprint_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    with journal_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {"status": "Begge databaser svarer"}
