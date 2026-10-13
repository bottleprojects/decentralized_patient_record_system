from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models import User, RoleEnum, AuditLog, Consent, Prescription, Diagnosis, Observation
from ..services.auth import get_current_user

router = APIRouter(prefix="/clinical", tags=["clinical"])

# --- Pydantic Models ---
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
