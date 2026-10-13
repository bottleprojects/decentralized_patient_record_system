from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from typing import List
import hashlib
import uuid
import time

from ..database import get_db
from ..models import User, MedicalRecord, Consent, RoleEnum, AuditLog
from ..services.auth import get_current_user
from ..services.crypto import crypto_service
from ..services.storage import storage_service
from ..services.blockchain import blockchain_service

router = APIRouter(prefix="/records", tags=["records"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_record(
    patient_id: int = Form(...),
    file_type: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == RoleEnum.patient:
        if patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Patients can only upload their own records")
        assigned_doctor_id = None
    elif current_user.role == RoleEnum.doctor:
        if current_user.verification_status != "verified":
            raise HTTPException(status_code=403, detail="Your doctor account must be verified by an admin before uploading records")
        # Check if doctor has consent
        consent = db.query(Consent).filter(
            Consent.patient_id == patient_id,
            Consent.doctor_id == current_user.id,
            Consent.status == "active"
        ).first()

        if not consent:
            raise HTTPException(status_code=403, detail="No active consent from this patient")
        assigned_doctor_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="Admins cannot upload records")

    # Read and hash original file
    file_bytes = await file.read()
    original_hash = hashlib.sha256(file_bytes).hexdigest()

    # Encrypt file
    encrypted_bytes = crypto_service.encrypt(file_bytes)
    
    # Upload to Supabase
    file_name = f"{patient_id}/{uuid.uuid4()}_{file.filename}.enc"
    storage_path = storage_service.upload_file(file_name, encrypted_bytes, file.content_type or "application/octet-stream")

    # Store hash on Blockchain
    record_uuid = str(uuid.uuid4())
    tx_hash = None
    try:
        # Require blockchain verification 
        tx_hash = blockchain_service.store_record_hash(record_uuid, original_hash)
    except Exception as e:
        # Delete the uploaded file from Supabase if blockchain fails so we don't leave orphaned files
        try:
            storage_service.client.storage.from_(storage_service.bucket_name).remove([file_name])
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Blockchain verification failed: {str(e)}")

    # Save to Database
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=assigned_doctor_id,
        file_type=file_type,
        supabase_file_path=storage_path,
        record_hash=original_hash,
        blockchain_tx_hash=tx_hash,
        description=description
    )
    db.add(record)
    
    # Audit log
    audit = AuditLog(user_id=current_user.id, action="UPLOAD_RECORD", resource_id=str(patient_id))
    db.add(audit)
    
    db.commit()
    db.refresh(record)

    return {"message": "Record uploaded and encrypted successfully", "record_id": record.id, "tx_hash": tx_hash}

@router.get("")
def get_records(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == RoleEnum.admin:
        records = db.query(MedicalRecord).all()
        return [{
            "id": r.id,
            "patient_id": r.patient_id,
            "doctor_id": r.doctor_id,
            "file_type": r.file_type or "General Health Record",
            "supabase_file_path": r.supabase_file_path,
            "ipfs_hash": r.ipfs_hash,
            "blockchain_tx_hash": r.blockchain_tx_hash,
            "record_hash": r.record_hash,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in records]
        
    elif current_user.role == RoleEnum.patient:
        records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == current_user.id).all()
        # Audit log
        audit = AuditLog(user_id=current_user.id, action="VIEW_OWN_RECORDS")
        db.add(audit)
        db.commit()
        return [{
            "id": r.id,
            "patient_id": r.patient_id,
            "doctor_id": r.doctor_id,
            "file_type": r.file_type or "General Health Record",
            "supabase_file_path": r.supabase_file_path,
            "ipfs_hash": r.ipfs_hash,
            "blockchain_tx_hash": r.blockchain_tx_hash,
            "record_hash": r.record_hash,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in records]
    
    elif current_user.role == RoleEnum.doctor:
        # Doctor can see records of patients they have active consent for
        consents = db.query(Consent).filter(Consent.doctor_id == current_user.id, Consent.status == "active").all()
        patient_ids = [c.patient_id for c in consents]
        records = db.query(MedicalRecord).filter(MedicalRecord.patient_id.in_(patient_ids)).all()
        return [{
            "id": r.id,
            "patient_id": r.patient_id,
            "doctor_id": r.doctor_id,
            "file_type": r.file_type or "General Health Record",
            "supabase_file_path": r.supabase_file_path,
            "ipfs_hash": r.ipfs_hash,
            "blockchain_tx_hash": r.blockchain_tx_hash,
            "record_hash": r.record_hash,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in records]

@router.get("/export")
def export_patient_records(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can export their full history")
        
    records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == current_user.id).all()
    consents = db.query(Consent).filter(Consent.patient_id == current_user.id).all()
    audit_logs = db.query(AuditLog).filter(AuditLog.user_id == current_user.id).all()
    
    # We would also get clinical data but it's handled in clinical router. 
    # For a full export, we can just dump what we have here.
    
    db.add(AuditLog(user_id=current_user.id, action="EXPORT_FULL_HISTORY"))
    db.commit()
    
    return {
        "user_profile": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name
        },
        "medical_records": [
            {
                "id": r.id,
                "file_type": r.file_type,
                "description": r.description,
                "created_at": r.created_at,
                "doctor_id": r.doctor_id,
                "blockchain_tx_hash": r.blockchain_tx_hash
            } for r in records
        ],
        "consents": [
            {
                "id": c.id,
                "doctor_id": c.doctor_id,
                "status": c.status,
                "granted_at": c.granted_at,
                "revoked_at": c.revoked_at
            } for c in consents
        ],
        "audit_logs": [
            {
                "id": a.id,
                "action": a.action,
                "timestamp": a.timestamp,
                "resource_id": a.resource_id
            } for a in audit_logs
        ]
    }

@router.get("/{record_id}/download")
def download_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Get record
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    # 2. Check permissions
    if current_user.role == RoleEnum.patient:
        if record.patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this record")
    elif current_user.role == RoleEnum.doctor:
        consent = db.query(Consent).filter(
            Consent.patient_id == record.patient_id,
            Consent.doctor_id == current_user.id,
            Consent.status == "active"
        ).first()
        if not consent:
            raise HTTPException(status_code=403, detail="No active consent from this patient")
    else:
        raise HTTPException(status_code=403, detail="Admins cannot download records")
        
    # 3. Download from Supabase
    try:
        encrypted_bytes = storage_service.download_file(record.supabase_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file from storage: {e}")
        
    # 4. Decrypt
    try:
        decrypted_bytes = crypto_service.decrypt(encrypted_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decrypt file")
        
    # Extract original filename from supabase_file_path if possible
    # format is: patient_id/uuid_filename.ext.enc
    file_name = record.supabase_file_path.split("/")[-1]
    if file_name.endswith(".enc"):
        file_name = file_name[:-4] # strip .enc
    # also strip uuid_ (36 chars + 1 underscore)
    if len(file_name) > 37 and file_name[36] == "_":
        file_name = file_name[37:]
        
    headers = {
        'Content-Disposition': f'attachment; filename="{file_name}"'
    }
    
    # log audit
    audit = AuditLog(user_id=current_user.id, action="DOWNLOAD_RECORD", resource_id=str(record.id))
    db.add(audit)
    db.commit()
    
    return Response(content=decrypted_bytes, headers=headers)
