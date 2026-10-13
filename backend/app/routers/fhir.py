from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, RoleEnum, Observation, AuditLog
from ..services.auth import get_current_user

router = APIRouter(prefix="/fhir/v4", tags=["fhir"])

@router.get("/Patient/{patient_id}")
def get_fhir_patient(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Simple authorization: Patient can only fetch their own FHIR record
    if current_user.role == RoleEnum.patient and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this FHIR resource")
        
    patient = db.query(User).filter(User.id == patient_id, User.role == RoleEnum.patient).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    # Log access
    db.add(AuditLog(user_id=current_user.id, action="EXPORT_FHIR_PATIENT", resource_id=str(patient_id)))
    db.commit()

    return {
        "resourceType": "Patient",
        "id": str(patient.id),
        "identifier": [
            {
                "system": "urn:oid:1.2.36.146.595.217.0.1",
                "value": str(patient.id)
            }
        ],
        "name": [
            {
                "use": "official",
                "text": patient.full_name
            }
        ],
        "telecom": [
            {
                "system": "email",
                "value": patient.email
            }
        ]
    }

@router.get("/Observation")
def get_fhir_observations(patient: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient_id = patient
    if current_user.role == RoleEnum.patient and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to access these FHIR resources")
        
    observations = db.query(Observation).filter(Observation.patient_id == patient_id).all()
    
    # Log access
    db.add(AuditLog(user_id=current_user.id, action="EXPORT_FHIR_OBSERVATION", resource_id=str(patient_id)))
    db.commit()

    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(observations),
        "entry": []
    }
    
    for obs in observations:
        bundle["entry"].append({
            "resource": {
                "resourceType": "Observation",
                "id": str(obs.id),
                "status": "final",
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "code": {
                    "text": obs.observation_type
                },
                "valueQuantity": {
                    "value": obs.value,
                    "unit": obs.unit if obs.unit else ""
                }
            }
        })
        
    return bundle
