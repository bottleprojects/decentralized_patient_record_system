from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, Request
from sqlalchemy.orm import Session
from typing import List
import hashlib
import uuid
import time

from ..database import get_db
from ..models import User, MedicalRecord, Consent, RoleEnum, AuditLog
from ..services.auth import get_current_user
from ..services.crypto import crypto_service
from ..services.blockchain import blockchain_service
from ..services.ipfs import ipfs_service
from ..services.rate_limiter import rate_limiter, get_client_ip

# File size limit for IPFS uploads: 50 MB
IPFS_MAX_SIZE_BYTES = 50 * 1024 * 1024
# Per-patient lifetime record cap for demo deployment
MAX_RECORDS_PER_PATIENT = 25

router = APIRouter(prefix="/records", tags=["records"])

@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/ipfs-upload", status_code=status.HTTP_201_CREATED)
async def upload_record(
    request: Request,
    patient_id: int = Form(...),
    file_type: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    IPFS Upload flow: Frontend -> Backend -> AES-256-GCM Encrypt -> Pinata IPFS -> Sepolia Blockchain anchoring.
    Only the CID, SHA-256 hash, and file metadata are anchored on-chain.
    """
    # Rate limit uploads: 10 uploads per hour per user
    rate_limiter.check(
        f"upload:user:{current_user.id}",
        max_requests=10,
        window_seconds=3600,
        action_name="medical record upload"
    )

    # Permission check
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

    # Enforce per-user upload cap
    patient_record_count = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).count()
    if patient_record_count >= MAX_RECORDS_PER_PATIENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient upload cap reached: maximum {MAX_RECORDS_PER_PATIENT} records allowed per patient in this demo."
        )

    # Read file
    file_bytes = await file.read()

    # File size validation (50 MB limit)
    if len(file_bytes) > IPFS_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 50 MB (got {len(file_bytes) / (1024*1024):.1f} MB)."
        )

    # SHA-256 of original (pre-encrypt) file — this is what goes on-chain
    original_hash = hashlib.sha256(file_bytes).hexdigest()

    # AES-256-GCM encrypt BEFORE uploading to IPFS (IPFS is public)
    encrypted_bytes = crypto_service.encrypt(file_bytes)

    # Upload encrypted file to IPFS via Pinata
    original_filename = file.filename or "medical_file"
    ipfs_filename = f"{patient_id}_{uuid.uuid4()}_{original_filename}.enc"
    try:
        cid = ipfs_service.upload(encrypted_bytes, ipfs_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IPFS upload failed: {str(e)}")

    # Store IPFS metadata on-chain: only CID + hash + file metadata (never the file itself)
    record_uuid = str(uuid.uuid4())
    tx_hash = None
    try:
        tx_hash = blockchain_service.store_ipfs_record(
            record_uuid,
            cid,
            original_hash,
            original_filename,
            file_type,
            len(file_bytes),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blockchain anchoring failed: {str(e)}")

    # Save to database
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=assigned_doctor_id,
        file_type=file_type,
        supabase_file_path=None,
        ipfs_cid=cid,
        ipfs_file_name=original_filename,
        ipfs_file_size=len(file_bytes),
        record_hash=original_hash,
        blockchain_tx_hash=tx_hash,
        description=description,
    )
    db.add(record)
    audit = AuditLog(user_id=current_user.id, action="IPFS_UPLOAD_RECORD", resource_id=str(patient_id))
    db.add(audit)
    db.commit()
    db.refresh(record)

    return {
        "message": "File encrypted and stored on IPFS successfully",
        "record_id": record.id,
        "cid": cid,
        "sha256_hash": original_hash,
        "tx_hash": tx_hash,
        "file_size": len(file_bytes),
        "file_name": original_filename,
    }


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
            "ipfs_cid": r.ipfs_cid,
            "ipfs_file_name": r.ipfs_file_name,
            "ipfs_file_size": r.ipfs_file_size,
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
            "ipfs_cid": r.ipfs_cid,
            "ipfs_file_name": r.ipfs_file_name,
            "ipfs_file_size": r.ipfs_file_size,
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
            "ipfs_cid": r.ipfs_cid,
            "ipfs_file_name": r.ipfs_file_name,
            "ipfs_file_size": r.ipfs_file_size,
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
@router.get("/{record_id}/ipfs-download")
def download_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Download flow: IPFS (via Pinata gateway) → Backend → decrypt → verify hash → Frontend.
    Returns the decrypted file with an 'X-Integrity-Verified' header.
    """
    # 1. Get record
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if not record.ipfs_cid:
        raise HTTPException(
            status_code=400,
            detail="This record was uploaded under legacy storage and has no IPFS CID. Please re-upload to IPFS."
        )

    # 2. Permission check
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

    # 3. Fetch encrypted bytes from IPFS
    try:
        encrypted_bytes = ipfs_service.download(record.ipfs_cid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file from IPFS: {e}")

    # 4. Decrypt
    try:
        decrypted_bytes = crypto_service.decrypt(encrypted_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decrypt file — it may be corrupted.")

    # 5. Integrity check: recompute SHA-256 and compare to on-chain hash stored in DB
    recomputed_hash = hashlib.sha256(decrypted_bytes).hexdigest()
    integrity_ok = (record.record_hash is not None) and (recomputed_hash == record.record_hash)

    file_name = record.ipfs_file_name or f"record_{record_id}"

    headers = {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "X-Integrity-Verified": "true" if integrity_ok else "false",
        "X-Record-Hash": record.record_hash or "",
        "X-Recomputed-Hash": recomputed_hash,
        "X-IPFS-CID": record.ipfs_cid,
        "Access-Control-Expose-Headers": "X-Integrity-Verified, X-Record-Hash, X-Recomputed-Hash, X-IPFS-CID, Content-Disposition",
    }

    # Audit log
    audit = AuditLog(user_id=current_user.id, action="IPFS_DOWNLOAD_RECORD", resource_id=str(record.id))
    db.add(audit)
    db.commit()

    return Response(content=decrypted_bytes, headers=headers)
