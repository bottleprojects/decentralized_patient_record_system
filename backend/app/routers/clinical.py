from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import time
import threading

from ..database import get_db
from ..models import User, RoleEnum, AuditLog, Consent, Prescription, Diagnosis, Observation
from ..services.auth import get_current_user

router = APIRouter(prefix="/clinical", tags=["clinical"])

# --- In-Memory IoT Telemetry Store ---
_telemetry_lock = threading.Lock()
LATEST_TELEMETRY = {
    "device_id": "ESP32-VITALS-01",
    "finger_detected": False,
    "ir_value": 0,
    "leads_off": True,
    "heart_rate": 0,
    "spo2": 0,
    "ecg_samples": [],
    "timestamp": None,
    "received_at": None,
}


def update_telemetry(payload: dict):
    """Thread-safe update of latest IoT telemetry packet."""
    with _telemetry_lock:
        for k in ["device_id", "finger_detected", "ir_value", "leads_off", "heart_rate", "spo2", "ecg_samples"]:
            if k in payload:
                LATEST_TELEMETRY[k] = payload[k]
        now = time.time()
        LATEST_TELEMETRY["received_at"] = now
        LATEST_TELEMETRY["timestamp"] = payload.get("timestamp") or datetime.utcnow().isoformat() + "Z"


# --- Pydantic Models ---
class TelemetryIngest(BaseModel):
    device_id: Optional[str] = "ESP32-VITALS-01"
    finger_detected: bool = False
    ir_value: Optional[int] = 0
    leads_off: Optional[bool] = False
    heart_rate: Optional[int] = 0
    spo2: Optional[int] = 0
    ecg_samples: Optional[List[int]] = []
    timestamp: Optional[str] = None
class PrescriptionCreate(BaseModel):
    patient_id: int
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    notes: Optional[str] = None

class DiagnosisCreate(BaseModel):
    patient_id: int
    condition_name: str
    severity: Optional[str] = None
    notes: Optional[str] = None

class ObservationCreate(BaseModel):
    patient_id: int
    observation_type: str
    value: str
    unit: Optional[str] = None

# --- Helper function for authorization ---
def verify_doctor_access(patient_id: int, db: Session, current_user: User):
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add clinical data")
    if current_user.verification_status != "verified":
        raise HTTPException(status_code=403, detail="Doctor account must be verified")
    
    consent = db.query(Consent).filter(
        Consent.patient_id == patient_id,
        Consent.doctor_id == current_user.id,
        Consent.status == "active"
    ).first()
    if not consent:
        raise HTTPException(status_code=403, detail="No active consent from this patient")

# --- Prescriptions ---
@router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
def create_prescription(data: PrescriptionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_doctor_access(data.patient_id, db, current_user)
    
    record = Prescription(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        medication_name=data.medication_name,
        dosage=data.dosage,
        frequency=data.frequency,
        duration=data.duration,
        notes=data.notes
    )
    db.add(record)
    db.add(AuditLog(user_id=current_user.id, action="CREATE_PRESCRIPTION", resource_id=str(data.patient_id)))
    db.commit()
    return {"message": "Prescription created"}

# --- Diagnoses ---
@router.post("/diagnoses", status_code=status.HTTP_201_CREATED)
def create_diagnosis(data: DiagnosisCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_doctor_access(data.patient_id, db, current_user)
    
    record = Diagnosis(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        condition_name=data.condition_name,
        severity=data.severity,
        notes=data.notes
    )
    db.add(record)
    db.add(AuditLog(user_id=current_user.id, action="CREATE_DIAGNOSIS", resource_id=str(data.patient_id)))
    db.commit()
    return {"message": "Diagnosis created"}

# --- Observations ---
@router.post("/observations", status_code=status.HTTP_201_CREATED)
def create_observation(data: ObservationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_doctor_access(data.patient_id, db, current_user)
    
    record = Observation(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        observation_type=data.observation_type,
        value=data.value,
        unit=data.unit
    )
    db.add(record)
    db.add(AuditLog(user_id=current_user.id, action="CREATE_OBSERVATION", resource_id=str(data.patient_id)))
    db.commit()
    return {"message": "Observation created"}

# --- Retrieve for Patient ---
@router.get("/patient-data")
def get_patient_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can view this data")
        
    prescriptions = db.query(Prescription).filter(Prescription.patient_id == current_user.id).all()
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == current_user.id).all()
    observations = db.query(Observation).filter(Observation.patient_id == current_user.id).all()
    
    db.add(AuditLog(user_id=current_user.id, action="VIEW_CLINICAL_DATA"))
    db.commit()
    
    return {
        "prescriptions": prescriptions,
        "diagnoses": diagnoses,
        "observations": observations
    }


# --- IoT Telemetry Endpoints ---
@router.post("/telemetry/ingest", status_code=status.HTTP_200_OK)
def ingest_telemetry(data: TelemetryIngest):
    """
    Ingest live telemetry packet from ESP32 vitals sensor.
    Unauthenticated to allow fast, lightweight push from microcontrollers over Wi-Fi.
    """
    update_telemetry(data.dict())
    return {"status": "ok", "message": "Telemetry received"}


@router.get("/telemetry/latest")
def get_latest_telemetry(current_user: User = Depends(get_current_user)):
    """
    Fetch the latest buffered vitals telemetry packet with connection liveness.
    Connected is True if a packet was received within the last 5.0 seconds.
    """
    with _telemetry_lock:
        data = dict(LATEST_TELEMETRY)

    received_at = data.get("received_at")
    now = time.time()
    if received_at is not None:
        age_seconds = round(now - received_at, 2)
        connected = age_seconds <= 5.0
    else:
        age_seconds = None
        connected = False

    return {
        "connected": connected,
        "age_seconds": age_seconds,
        "device_id": data.get("device_id"),
        "finger_detected": data.get("finger_detected", False),
        "ir_value": data.get("ir_value", 0),
        "leads_off": data.get("leads_off", False),
        "heart_rate": data.get("heart_rate", 0),
        "spo2": data.get("spo2", 0),
        "ecg_samples": data.get("ecg_samples", []),
        "timestamp": data.get("timestamp"),
        "patient_id": current_user.id,
        "patient_name": current_user.full_name,
        "patient_email": current_user.email,
    }
