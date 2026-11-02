from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models import User, Consent, ConsentRequest, RoleEnum, AuditLog
from ..services.auth import get_current_user

"""
Consent Management Router.
NOTE ON ACCESS CONTROL ARCHITECTURE:
Patient and doctor access permissions are strictly ENFORCED here by the backend API 
and relational database access-control layer. Smart contract consent functions exist solely 
to record immutable on-chain audit events; the smart contract does not enforce access boundaries.
"""

router = APIRouter(prefix="/consent", tags=["consent"])

@router.post("/grant/{doctor_id}")
def grant_consent(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can grant consent")

    doctor = db.query(User).filter(User.id == doctor_id, User.role == RoleEnum.doctor).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    existing_consent = db.query(Consent).filter(
        Consent.patient_id == current_user.id,
        Consent.doctor_id == doctor_id,
        Consent.status == "active"
    ).first()

    if existing_consent:
        return {"message": "Consent already active"}

    consent = Consent(patient_id=current_user.id, doctor_id=doctor_id)
    db.add(consent)

    audit = AuditLog(user_id=current_user.id, action="GRANT_CONSENT", resource_id=str(doctor_id))
    db.add(audit)

    db.commit()
    return {"message": "Consent granted successfully"}

@router.post("/revoke/{doctor_id}")
def revoke_consent(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can revoke consent")

    consent = db.query(Consent).filter(
        Consent.patient_id == current_user.id,
        Consent.doctor_id == doctor_id,
        Consent.status == "active"
    ).first()

    if not consent:
        raise HTTPException(status_code=404, detail="No active consent found for this doctor")

    consent.status = "revoked"
    consent.revoked_at = datetime.utcnow()

    audit = AuditLog(user_id=current_user.id, action="REVOKE_CONSENT", resource_id=str(doctor_id))
    db.add(audit)

    db.commit()
    return {"message": "Consent revoked successfully"}

@router.get("/active")
def get_active_consents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can view their active consents")
    
    consents = db.query(Consent).filter(
        Consent.patient_id == current_user.id,
        Consent.status == "active"
    ).all()
    return consents

@router.get("")
def get_all_consents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    
    return db.query(Consent).all()

@router.post("/request/{patient_id}")
def request_consent(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Only doctors can request consent")
        
    if current_user.verification_status != "verified":
        raise HTTPException(status_code=403, detail="Your doctor account must be verified by an admin before requesting consent")

    patient = db.query(User).filter(User.id == patient_id, User.role == RoleEnum.patient).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing_consent = db.query(Consent).filter(
        Consent.patient_id == patient_id,
        Consent.doctor_id == current_user.id,
        Consent.status == "active"
    ).first()

    if existing_consent:
        return {"message": "Patient has already granted you active consent"}

    existing_request = db.query(ConsentRequest).filter(
        ConsentRequest.patient_id == patient_id,
        ConsentRequest.doctor_id == current_user.id,
        ConsentRequest.status == "pending"
    ).first()

    if existing_request:
        return {"message": "Consent request already pending"}

    req = ConsentRequest(patient_id=patient_id, doctor_id=current_user.id)
    db.add(req)
    db.commit()
    return {"message": "Consent request sent successfully"}

@router.get("/requests/pending")
def get_pending_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can view pending requests")
    
    requests = db.query(ConsentRequest).filter(
        ConsentRequest.patient_id == current_user.id,
        ConsentRequest.status == "pending"
    ).all()
    
    # Enrich with doctor info
    result = []
    for r in requests:
        doctor = db.query(User).filter(User.id == r.doctor_id).first()
        result.append({
            "id": r.id,
            "doctor_id": r.doctor_id,
            "doctor_name": doctor.full_name if doctor else "Unknown",
            "created_at": r.created_at
        })
    return result

@router.post("/requests/{request_id}/approve")
def approve_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can approve requests")

    req = db.query(ConsentRequest).filter(
        ConsentRequest.id == request_id,
        ConsentRequest.patient_id == current_user.id,
        ConsentRequest.status == "pending"
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Pending request not found")

    # Approve request
    req.status = "approved"
    
    # Check if a permanent consent already exists
    existing_consent = db.query(Consent).filter(
        Consent.patient_id == current_user.id,
        Consent.doctor_id == req.doctor_id,
        Consent.status == "active"
    ).first()

    if not existing_consent:
        # Create permanent consent
        consent = Consent(patient_id=current_user.id, doctor_id=req.doctor_id)
        db.add(consent)

    audit = AuditLog(user_id=current_user.id, action="APPROVE_CONSENT_REQUEST", resource_id=str(req.doctor_id))
    db.add(audit)

    db.commit()
    return {"message": "Consent request approved and active consent granted"}

@router.post("/requests/{request_id}/reject")
def reject_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can reject requests")

    req = db.query(ConsentRequest).filter(
        ConsentRequest.id == request_id,
        ConsentRequest.patient_id == current_user.id,
        ConsentRequest.status == "pending"
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Pending request not found")

    # Reject request
    req.status = "rejected"
    
    audit = AuditLog(user_id=current_user.id, action="REJECT_CONSENT_REQUEST", resource_id=str(req.doctor_id))
    db.add(audit)

    db.commit()
    return {"message": "Consent request rejected"}

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

class EmergencyAccessRequest(BaseModel):
    patient_id: int
    justification: str


def check_active_consent(patient_id: int, doctor_id: int, db: Session) -> Optional[Consent]:
    """
    Verifies active consent between patient and doctor, enforcing expiration
    deadlines on emergency break-glass authorizations.
    """
    consent = db.query(Consent).filter(
        Consent.patient_id == patient_id,
        Consent.doctor_id == doctor_id,
        Consent.status == "active",
    ).first()
    if not consent:
        return None
    if consent.expires_at and consent.expires_at < datetime.utcnow():
        consent.status = "expired"
        db.commit()
        return None
    return consent


@router.post("/emergency")
def request_emergency_access(data: EmergencyAccessRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Emergency 'Break-Glass' clinical access protocol.
    Enforces verified-physician credentials, clinical justification requirement,
    a strictly time-bounded 24-hour access lease, and an immutable audit trail.
    """
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Only doctors can request emergency access")
        
    if current_user.verification_status != "verified":
        raise HTTPException(status_code=403, detail="Doctor account must be verified by an administrator to invoke emergency access")

    if not data.justification or len(data.justification.strip()) < 15:
        raise HTTPException(
            status_code=400,
            detail="Emergency break-glass access requires a substantive clinical justification (minimum 15 characters)."
        )

    patient = db.query(User).filter(User.id == data.patient_id, User.role == RoleEnum.patient).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    now = datetime.utcnow()
    # Check if active unexpired consent already exists
    existing = check_active_consent(data.patient_id, current_user.id, db)
    if existing:
        return {"message": "You already have active consent for this patient"}
        
    # Create time-bounded emergency consent (24-hour maximum authorization window)
    expires_at = now + timedelta(hours=24)
    consent = Consent(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        status="active",
        granted_at=now,
        expires_at=expires_at,
    )
    db.add(consent)
    
    # High-priority audit log
    audit = AuditLog(
        user_id=current_user.id, 
        action="EMERGENCY_BREAKGLASS_ACCESS", 
        resource_id=f"patient:{data.patient_id};expires:{expires_at.isoformat()}Z;justification:{data.justification.strip()}"
    )
    db.add(audit)
    db.commit()
    
    return {
        "message": "Emergency access granted. Bounded authorization active for 24 hours.",
        "expires_at": expires_at.isoformat() + "Z",
        "patient_id": data.patient_id,
    }
