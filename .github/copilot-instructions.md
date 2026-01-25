# Fingerprint Backend AI Coding Agent Instructions

## Architecture Overview
This is a **FastAPI-based biometric authentication system** with two separate PostgreSQL databases:
- **Fingerprint DB**: Stores patient identities, fingerprint templates, and sensor slot mappings (auth domain)
- **Journal DB**: Stores medical records linked to patients by `external_id` (medical domain)

The system separates concerns: fingerprint verification (auth/access control) is independent from medical record storage, allowing secure cross-domain queries using `external_id` as the only link.

## Project Structure
```
backend/app/
├── main.py              # FastAPI app, startup hooks, all HTTP endpoints
├── core/
│   ├── config.py        # DB URLs from .env (FINGERPRINT_DB_URL, JOURNAL_DB_URL)
│   ├── database.py      # Dual SQLAlchemy engines + declarative bases per DB
│   └── security.py      # (Empty - add auth/permission logic here)
├── models/
│   ├── patient.py       # Fingerprint DB: Patient with external_id (UUID)
│   ├── fingerprint.py   # Fingerprint DB: Template + sensor_slot, FK to patient
│   └── medical_record.py # Journal DB: Records linked via patient_external_id
├── api/
│   ├── esp32.py         # (Empty - ESP32 device communication)
│   └── web.py           # (Empty - web-only endpoints)
└── services/
    ├── access_service.py    # (Empty - fingerprint verification logic)
    ├── journal_service.py   # (Empty - medical record queries)
    └── patient_service.py   # (Empty - patient CRUD)
```

## Key Patterns & Conventions

### Database Session Management
- Use `FingerprintSessionLocal()` for fingerprint DB, `JournalSessionLocal()` for journal DB
- Always wrap in try/finally for cleanup: see `get_fingerprint_db()` dependency in [main.py](main.py#L28-L31)
- Queries return ORM objects; use `db.query(Model).filter(...).first()` or `.all()`

### API Endpoints
- **HTML Templates** (Jinja2 at `backend/app/templates/`): `/patients` (GET/POST)
- **Fingerprint APIs**: `/fingerprint/verify` (POST) - returns match status + patient data
- **Health Check**: `/health` (GET)
- **DB Test**: `/db-test` (GET) - verifies both DB connections
- Forms use FastAPI's `Form(...)` for HTML submission; JSON uses `Body(...)`

### Model Design
- **Patient**: Lives in Fingerprint DB; has `external_id` (UUID) for journal cross-references
- **Fingerprint**: Links to Patient via FK; stores binary template + sensor_slot (for multi-finger support)
- **MedicalRecord**: Lives in Journal DB; references Patient only via `external_id` (no direct FK to enforce separation)

### Startup Behavior
- `@app.on_event("startup")` creates all tables via `metadata.create_all()` for both DBs
- No migrations framework configured (add Alembic for production)

## Development Workflows

### Run the Application
```bash
cd backend
python -m uvicorn app.main:app --reload
# Starts on http://localhost:8000
```

### Create Tables
- Tables auto-create on startup (see `init_db()`)
- For schema changes: modify model files, restart app, or use Alembic migrations

### Access Logs
- Template responses: check FastAPI console output for errors
- DB errors: check stderr for SQLAlchemy logs

## Integration Points

### ESP32 Device Communication (Planned)
- Endpoint stub: [api/esp32.py](backend/app/api/esp32.py) - implement fingerprint capture/matching here
- Will likely POST fingerprint template to `POST /fingerprint/verify`
- Sensor slot mapping in Fingerprint model supports multi-finger enrollment

### Cross-Database Patient Queries
- **Never** FK from Journal DB to Fingerprint DB directly
- Link via `patient.external_id` (UUID) in code: `Patient.external_id == MedicalRecord.patient_external_id`
- Allows independent scaling and isolation of the two domains

## Common Tasks

### Add a New Endpoint
1. Define request/response models as Pydantic `BaseModel` (see `FingerprintVerifyRequest`)
2. Add route with `@app.get()` or `@app.post()` in [main.py](backend/app/main.py)
3. Inject DB session: `db: Session = Depends(get_fingerprint_db)`
4. Query model, return response or redirect

### Link Patient to Medical Record
```python
# In a service (e.g., journal_service.py):
patient = db_fingerprint.query(Patient).filter(Patient.id == patient_id).first()
record = db_journal.query(MedicalRecord).filter(
    MedicalRecord.patient_external_id == patient.external_id
).first()
```

### Verify Fingerprint (Current Stub)
- See `/fingerprint/verify` endpoint in [main.py](backend/app/main.py#L110-L130)
- Currently does patient lookup only; add actual matching logic in [access_service.py](backend/app/services/access_service.py)
- Returns `{"match": bool, "patient_external_id": str, "patient_name": str}`
