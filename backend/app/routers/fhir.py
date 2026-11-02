from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import User, RoleEnum, Observation, AuditLog, Consent
from ..services.auth import get_current_user

router = APIRouter(tags=["fhir"])


def verify_fhir_access(patient_id: int, db: Session, current_user: User):
    """
    Enforces HIPAA/GDPR clinical data authorization for FHIR endpoints:
    1. Authenticated user check.
    2. Patients can strictly only query their own resources.
    3. Physicians must be verified AND have active patient consent.
    4. Unassigned or unverified doctors receive 403 Forbidden.
    """
    if current_user.role == RoleEnum.patient:
        if current_user.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized: Patients can only access their own FHIR resources"
            )
    elif current_user.role == RoleEnum.doctor:
        if current_user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized: Physician account must be verified by an administrator"
            )
        from .consent import check_active_consent
        consent = check_active_consent(patient_id, current_user.id, db)
        if not consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized: No active patient consent granted to this physician"
            )
    elif current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access clinical FHIR resources"
        )


def _get_loinc_and_ucum(observation_type: str, raw_unit: Optional[str] = None):
    """Maps observation types to standard LOINC terminology and UCUM unit specifications."""
    obs_clean = observation_type.strip().lower()
    if "heart" in obs_clean or "pulse" in obs_clean or "hr" in obs_clean:
        return {
            "loinc_code": "8867-4",
            "display": "Heart rate",
            "unit": "beats/minute",
            "ucum_code": "/min"
        }
    elif "spo2" in obs_clean or "oxygen" in obs_clean or "saturation" in obs_clean:
        return {
            "loinc_code": "2708-6",
            "display": "Oxygen saturation in Arterial blood",
            "unit": "%",
            "ucum_code": "%"
        }
    elif "ecg" in obs_clean or "lead" in obs_clean:
        return {
            "loinc_code": "8889-8",
            "display": "Physiological rhythm strip",
            "unit": "mV",
            "ucum_code": "mV"
        }
    elif "systolic" in obs_clean:
        return {
            "loinc_code": "8480-6",
            "display": "Systolic blood pressure",
            "unit": "mmHg",
            "ucum_code": "mm[Hg]"
        }
    elif "diastolic" in obs_clean:
        return {
            "loinc_code": "8462-4",
            "display": "Diastolic blood pressure",
            "unit": "mmHg",
            "ucum_code": "mm[Hg]"
        }
    else:
        return {
            "loinc_code": "36407-5",
            "display": observation_type,
            "unit": raw_unit or "",
            "ucum_code": raw_unit or "{count}"
        }


@router.get("/Patient/{patient_id}")
def get_fhir_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FHIR R4 Patient Resource endpoint with full role, verification, and consent gating.
    """
    verify_fhir_access(patient_id, db, current_user)

    patient = db.query(User).filter(User.id == patient_id, User.role == RoleEnum.patient).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Mandatory security audit log
    db.add(AuditLog(user_id=current_user.id, action="EXPORT_FHIR_PATIENT", resource_id=str(patient_id)))
    db.commit()

    return {
        "resourceType": "Patient",
        "id": str(patient.id),
        "identifier": [
            {
                "use": "official",
                "system": "urn:oid:1.2.36.146.595.217.0.1",
                "value": f"PATIENT-{patient.id:06d}"
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "text": patient.full_name
            }
        ],
        "telecom": [
            {
                "system": "email",
                "value": patient.email,
                "use": "home"
            }
        ]
    }


@router.get("/Observation")
def get_fhir_observations(
    patient: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FHIR R4 Observation Bundle with LOINC semantic coding, numeric decimal Quantity.value,
    UCUM standardized units, and strict patient consent enforcement.
    """
    patient_id = patient
    verify_fhir_access(patient_id, db, current_user)

    observations = db.query(Observation).filter(Observation.patient_id == patient_id).all()

    # Mandatory security audit log
    db.add(AuditLog(user_id=current_user.id, action="EXPORT_FHIR_OBSERVATION", resource_id=str(patient_id)))
    db.commit()

    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(observations),
        "entry": []
    }

    for obs in observations:
        # Standards conformance: Quantity.value MUST be a JSON number (decimal)
        numeric_val = None
        try:
            numeric_val = float(obs.value) if "." in str(obs.value) else int(obs.value)
        except (ValueError, TypeError):
            numeric_val = obs.value

        spec = _get_loinc_and_ucum(obs.observation_type, obs.unit)

        obs_resource = {
            "resource": {
                "resourceType": "Observation",
                "id": str(obs.id),
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "vital-signs",
                                "display": "Vital Signs"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": spec["loinc_code"],
                            "display": spec["display"]
                        }
                    ],
                    "text": obs.observation_type
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "effectiveDateTime": obs.created_at.isoformat() + "Z" if hasattr(obs, "created_at") and obs.created_at else None,
                "valueQuantity": {
                    "value": numeric_val,
                    "unit": spec["unit"],
                    "system": "http://unitsofmeasure.org",
                    "code": spec["ucum_code"]
                }
            }
        }
        bundle["entry"].append(obs_resource)

    return bundle
