import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import hashlib
import uuid
import time
import concurrent.futures

from ..database import get_db
from ..models import User, MedicalRecord, Consent, RoleEnum, AuditLog, MeasurementSession
from ..services.auth import get_current_user
from ..services.crypto import crypto_service
from ..services.blockchain import blockchain_service
from ..services.ipfs import ipfs_service
from ..services.rate_limiter import rate_limiter, get_client_ip

# File size limit for IPFS uploads: configurable via MAX_UPLOAD_MB (default 10 MB in production)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
IPFS_MAX_SIZE_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Per-patient lifetime record cap (0 = unlimited; configurable via MAX_RECORDS_PER_PATIENT)
MAX_RECORDS_PER_PATIENT = int(os.getenv("MAX_RECORDS_PER_PATIENT", "0"))

# Generic on-chain label — the real file name stays in the database only.
_ONCHAIN_FILE_NAME_LABEL = "encrypted-record"

router = APIRouter(prefix="/records", tags=["records"])


def confirm_blockchain_record(record_id: int, tx_hash: str):
    """
    Background task: polls Sepolia for receipt and updates record.blockchain_status.
    - status == 1 -> 'confirmed'
    - status == 0 / reverted / timeout -> 'failed'
    """
    from ..database import SessionLocal
    from ..services.blockchain import blockchain_service
    try:
        receipt = blockchain_service.wait_for_receipt(tx_hash, timeout=180)
        new_status = "confirmed" if receipt.get("status") == 1 else "failed"
    except Exception:
        new_status = "failed"
    with SessionLocal() as db:
        rec = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
        if rec:
            rec.blockchain_status = new_status
            db.commit()


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/ipfs-upload", status_code=status.HTTP_201_CREATED)
async def upload_record(
    request: Request,
    background_tasks: BackgroundTasks,
    patient_id: int = Form(...),
    file_type: str = Form(...),
    description: str = Form(None),
    acquisition_hash: str = Form(None),
    session_id: str = Form(None),
    device_id: str = Form(None),
    acquisition_source: str = Form("LIVE_HARDWARE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    IPFS Upload flow: Frontend -> Backend -> AES-256-GCM Encrypt -> Pinata IPFS -> Sepolia Blockchain anchoring.
    Only the CID, SHA-256 hash, and file metadata are anchored on-chain.
    The real file name is stored ONLY in the database for on-chain privacy.
    Pinata upload and Sepolia tx broadcast run concurrently.
    """
    # Rate limit uploads: 10 uploads per hour per user
    rate_limiter.check(
        f"upload:user:{current_user.id}",
        max_requests=10,
        window_seconds=3600,
        action_name="medical record upload"
    )

    # Permission check (Enforced by backend DB access control; smart contract only logs audit events)
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

    # Enforce per-user upload cap if configured
    if MAX_RECORDS_PER_PATIENT > 0:
        patient_record_count = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).count()
        if patient_record_count >= MAX_RECORDS_PER_PATIENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient upload cap reached: maximum {MAX_RECORDS_PER_PATIENT} records allowed per patient."
            )

    # Enforce upload size limit BEFORE buffering full file into memory
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > IPFS_MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_MB} MB."
                )
        except ValueError:
            pass

    if getattr(file, "size", None) is not None and file.size > IPFS_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_MB} MB."
        )

    # Read file safely in chunks to enforce limit without unbounded buffering
    chunks = []
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1 MB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > IPFS_MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_MB} MB."
            )
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    # SHA-256 of original (pre-encrypt) file — this is what goes on-chain
    original_hash = hashlib.sha256(file_bytes).hexdigest()

    # AES-256-GCM encrypt BEFORE uploading to IPFS (IPFS is public)
    encrypted_bytes = crypto_service.encrypt(file_bytes)

    # Server-side validation of hardware provenance metadata
    verified_acquisition_hash = None
    verified_session_id = None
    verified_device_id = device_id
    verified_acquisition_source = acquisition_source or "LIVE_HARDWARE"

    if acquisition_hash or session_id:
        if not session_id or not acquisition_hash:
            raise HTTPException(
                status_code=400,
                detail="Incomplete provenance metadata: Both session_id and acquisition_hash must be supplied together."
            )
        session = db.query(MeasurementSession).filter(MeasurementSession.session_id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Measurement session '{session_id}' not found. Cannot anchor unverified provenance metadata."
            )
        if session.patient_id != patient_id:
            raise HTTPException(
                status_code=403,
                detail=f"Provenance validation failed: Session '{session_id}' belongs to patient {session.patient_id}, not {patient_id}."
            )
        if session.status != "CAPTURE_COMPLETE":
            raise HTTPException(
                status_code=400,
                detail=f"Provenance validation failed: Session status is '{session.status}'. Only 'CAPTURE_COMPLETE' sessions can be anchored."
            )
        if session.quality_status != "VALID":
            raise HTTPException(
                status_code=400,
                detail=f"Provenance validation failed: Session quality status is '{session.quality_status}'. Must be 'VALID'."
            )
        if session.raw_manifest_hash != acquisition_hash:
            raise HTTPException(
                status_code=400,
                detail="Provenance validation failed: Supplied acquisition_hash does not match the canonical acquisition manifest hash recorded for this session."
            )
        if device_id and session.device_id and device_id != session.device_id:
            raise HTTPException(
                status_code=400,
                detail=f"Provenance validation failed: Supplied device_id '{device_id}' does not match session device '{session.device_id}'."
            )
        verified_acquisition_hash = session.raw_manifest_hash
        verified_session_id = session.session_id
        verified_device_id = session.device_id
        verified_acquisition_source = session.acquisition_source or "LIVE_HARDWARE"

    # Non-identifying IPFS filename (zero PII or original names in public IPFS metadata)
    original_filename = file.filename or "medical_file"
    ipfs_filename = f"enc_{uuid.uuid4().hex}.bin"

    # 1. Create initial persistent record in pending_upload state (saga coordination)
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=assigned_doctor_id,
        file_type=file_type,
        supabase_file_path=None,
        ipfs_cid=None,
        ipfs_file_name=original_filename,   # real filename in DB only
        ipfs_file_size=len(file_bytes),
        record_hash=original_hash,
        acquisition_hash=verified_acquisition_hash,
        session_id=verified_session_id,
        device_id=verified_device_id,
        acquisition_source=verified_acquisition_source,
        blockchain_tx_hash=None,
        blockchain_status="pending_upload",
        description=description,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # 2. Upload to Pinata IPFS
    try:
        cid = ipfs_service.upload(encrypted_bytes, ipfs_filename)
        record.ipfs_cid = cid
        record.blockchain_status = "pending_anchor"
        db.commit()
    except Exception as e:
        record.blockchain_status = "upload_failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"IPFS upload failed: {str(e)}")

    # 3. Broadcast Sepolia tx with hardware acquisition provenance if present
    tx_hash = None
    try:
        if verified_acquisition_hash:
            tx_hash = blockchain_service.store_ipfs_record_with_provenance(
                cid,
                cid,
                original_hash,
                verified_acquisition_hash,
                _ONCHAIN_FILE_NAME_LABEL,   # generic label, not the real filename
                file_type,                  # category tag (no PII) kept on-chain
                len(file_bytes),            # original size (no PII) kept on-chain
            )
        else:
            tx_hash = blockchain_service.store_ipfs_record(
                cid,
                cid,
                original_hash,
                _ONCHAIN_FILE_NAME_LABEL,   # generic label, not the real filename
                file_type,                  # category tag (no PII) kept on-chain
                len(file_bytes),            # original size (no PII) kept on-chain
            )
        record.blockchain_tx_hash = tx_hash
        record.blockchain_status = "confirming"
        audit = AuditLog(user_id=current_user.id, action="IPFS_UPLOAD_RECORD", resource_id=str(patient_id))
        db.add(audit)
        db.commit()
        db.refresh(record)
    except Exception as e:
        record.blockchain_status = "anchor_failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Blockchain anchoring failed: {str(e)}")

    # 4. Launch background receipt verification
    background_tasks.add_task(confirm_blockchain_record, record.id, tx_hash)

    return {
        "message": "File encrypted and stored on IPFS successfully",
        "record_id": record.id,
        "cid": cid,
        "sha256_hash": original_hash,
        "record_hash": original_hash,
        "tx_hash": tx_hash,
        "blockchain_status": "confirming",
        "file_size": len(file_bytes),
        "file_name": original_filename,
    }


@router.get("/{record_id}/status")
def get_record_status(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Status check endpoint for polling confirmation state with strict authorization."""
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Authorization gating
    if current_user.role == RoleEnum.patient:
        if record.patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to inspect this record's status")
    elif current_user.role == RoleEnum.doctor:
        if current_user.verification_status != "verified":
            raise HTTPException(status_code=403, detail="Doctor account must be verified by an administrator")
        consent = db.query(Consent).filter(
            Consent.patient_id == record.patient_id,
            Consent.doctor_id == current_user.id,
            Consent.status == "active",
        ).first()
        if not consent:
            raise HTTPException(status_code=403, detail="No active consent to view this record's status")
    elif current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    if record.blockchain_status == "confirming" and record.blockchain_tx_hash:
        try:
            receipt = blockchain_service.w3.eth.get_transaction_receipt(record.blockchain_tx_hash)
            if receipt:
                record.blockchain_status = "confirmed" if receipt.status == 1 else "failed"
                db.commit()
        except Exception:
            pass
    return {
        "record_id": record.id,
        "blockchain_status": record.blockchain_status or "confirmed",
        "blockchain_tx_hash": record.blockchain_tx_hash,
    }


@router.post("/{record_id}/retry-anchor", status_code=status.HTTP_200_OK)
def retry_blockchain_anchor(
    record_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retry blockchain anchoring for a record whose IPFS upload succeeded
    but blockchain transaction broadcast failed or remained unanchored.
    """
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    if current_user.role == RoleEnum.patient and record.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to retry anchoring for this record")
    elif current_user.role == RoleEnum.doctor:
        if current_user.verification_status != "verified":
            raise HTTPException(status_code=403, detail="Doctor account must be verified by an administrator")
        consent = db.query(Consent).filter(
            Consent.patient_id == record.patient_id,
            Consent.doctor_id == current_user.id,
            Consent.status == "active",
        ).first()
        if not consent:
            raise HTTPException(status_code=403, detail="No active consent for this patient")

    if not record.ipfs_cid:
        raise HTTPException(status_code=400, detail="Cannot anchor record without an existing IPFS CID. Upload must be restarted.")

    if record.blockchain_status in ["confirmed", "confirming"]:
        return {
            "message": f"Record is already in state '{record.blockchain_status}'",
            "record_id": record.id,
            "tx_hash": record.blockchain_tx_hash,
            "blockchain_status": record.blockchain_status,
        }

    try:
        if record.acquisition_hash:
            tx_hash = blockchain_service.store_ipfs_record_with_provenance(
                record.ipfs_cid,
                record.ipfs_cid,
                record.record_hash,
                record.acquisition_hash,
                _ONCHAIN_FILE_NAME_LABEL,
                record.file_type or "medical-record",
                record.ipfs_file_size or 0,
            )
        else:
            tx_hash = blockchain_service.store_ipfs_record(
                record.ipfs_cid,
                record.ipfs_cid,
                record.record_hash,
                _ONCHAIN_FILE_NAME_LABEL,
                record.file_type or "medical-record",
                record.ipfs_file_size or 0,
            )
        record.blockchain_tx_hash = tx_hash
        record.blockchain_status = "confirming"
        db.add(AuditLog(user_id=current_user.id, action="RETRY_BLOCKCHAIN_ANCHOR", resource_id=str(record.id)))
        db.commit()
        db.refresh(record)

        background_tasks.add_task(confirm_blockchain_record, record.id, tx_hash)

        return {
            "message": "Blockchain anchor transaction resubmitted",
            "record_id": record.id,
            "tx_hash": tx_hash,
            "blockchain_status": "confirming",
        }
    except Exception as e:
        record.blockchain_status = "anchor_failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Retry blockchain anchoring failed: {str(e)}")


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
            "blockchain_status": r.blockchain_status or ("confirmed" if r.blockchain_tx_hash else "confirming"),
            "record_hash": r.record_hash,
            "acquisition_hash": r.acquisition_hash,
            "session_id": r.session_id,
            "device_id": r.device_id,
            "acquisition_source": r.acquisition_source or "LIVE_HARDWARE",
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
            "blockchain_status": r.blockchain_status or ("confirmed" if r.blockchain_tx_hash else "confirming"),
            "record_hash": r.record_hash,
            "acquisition_hash": r.acquisition_hash,
            "session_id": r.session_id,
            "device_id": r.device_id,
            "acquisition_source": r.acquisition_source or "LIVE_HARDWARE",
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in records]
    
    elif current_user.role == RoleEnum.doctor:
        if current_user.verification_status != "verified":
            raise HTTPException(status_code=403, detail="Doctor account must be verified by an administrator before retrieving patient records")
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
            "blockchain_status": r.blockchain_status or ("confirmed" if r.blockchain_tx_hash else "confirming"),
            "record_hash": r.record_hash,
            "acquisition_hash": r.acquisition_hash,
            "session_id": r.session_id,
            "device_id": r.device_id,
            "acquisition_source": r.acquisition_source or "LIVE_HARDWARE",
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
    Download flow: IPFS (via Pinata gateway) → Backend → decrypt → verify hash against Sepolia → Frontend.

    Tamper handling:
      - Ciphertext altered (AES tag fails): returns 422 with X-Integrity-Verified: false
      - On-chain hash differs from decrypted file: returns 409 with X-Integrity-Verified: false
      - Blockchain unreachable: returns 502

    Privacy: the real file name is read from the DB (ipfs_file_name), not from the chain.
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

    # 2. Permission check (Enforced by backend DB access control; smart contract only logs audit events)
    if current_user.role == RoleEnum.patient:
        if record.patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this record")
    elif current_user.role == RoleEnum.doctor:
        if current_user.verification_status != "verified":
            raise HTTPException(status_code=403, detail="Doctor account must be verified by an administrator before downloading patient records")
        consent = db.query(Consent).filter(
            Consent.patient_id == record.patient_id,
            Consent.doctor_id == current_user.id,
            Consent.status == "active"
        ).first()
        if not consent:
            raise HTTPException(status_code=403, detail="No active consent from this patient")
    else:
        raise HTTPException(status_code=403, detail="Admins cannot download records")

    # Check confirmation state before downloading
    if record.blockchain_status == "confirming" and record.blockchain_tx_hash:
        try:
            receipt = blockchain_service.w3.eth.get_transaction_receipt(record.blockchain_tx_hash)
            if receipt:
                record.blockchain_status = "confirmed" if receipt.status == 1 else "failed"
                db.commit()
        except Exception:
            pass

    if record.blockchain_status == "confirming":
        raise HTTPException(
            status_code=409,
            detail="Record anchoring is still confirming on Sepolia testnet. Please try again in a few seconds.",
            headers={"X-Integrity-Verified": "false"}
        )

    if record.blockchain_status == "failed":
        raise HTTPException(
            status_code=409,
            detail="Blockchain anchoring failed for this record on Sepolia. Integrity cannot be verified.",
            headers={"X-Integrity-Verified": "false"}
        )

    # 3. Fetch encrypted bytes from IPFS
    try:
        encrypted_bytes = ipfs_service.download(record.ipfs_cid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file from IPFS: {e}")

    # 4. Decrypt — AES tag failure is a clear tamper signal (422)
    try:
        decrypted_bytes = crypto_service.decrypt(encrypted_bytes)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Integrity check FAILED: the encrypted file on IPFS is corrupted or has been altered.",
            headers={"X-Integrity-Verified": "false"},
        )

    # 5. On-Chain Integrity check: read hash directly from Sepolia blockchain via getIPFSRecord()
    try:
        on_chain_record = blockchain_service.get_ipfs_record(record.ipfs_cid)
        on_chain_hash = on_chain_record.get("sha256_hash", "")
        # Fallback to record ID if CID lookup returned empty hash
        if not on_chain_hash:
            fallback_record = blockchain_service.get_ipfs_record(str(record.id))
            on_chain_hash = fallback_record.get("sha256_hash", "")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"On-chain integrity verification failed: could not read record from Sepolia blockchain: {str(e)}"
        )

    recomputed_hash = hashlib.sha256(decrypted_bytes).hexdigest()

    # Fail-Closed policy: If on-chain hash is missing or not yet confirmed, never return unverified file
    if not on_chain_hash:
        raise HTTPException(
            status_code=409,
            detail=(
                "Integrity check FAILED: Record is not anchored on Sepolia blockchain or on-chain digest is missing. "
                "Fail-closed policy prohibits delivery of unverified medical records."
            ),
            headers={"X-Integrity-Verified": "false"},
        )

    # Hash mismatch is a clear tamper signal (409 Conflict)
    if recomputed_hash != on_chain_hash:
        raise HTTPException(
            status_code=409,
            detail=(
                "Integrity check FAILED: this file does not match the on-chain record. "
                "The decrypted file's SHA-256 hash differs from the hash anchored on Sepolia."
            ),
            headers={"X-Integrity-Verified": "false"},
        )

    # Tier-2 Provenance Verification: If acquisition_hash is bound, verify against on-chain anchor
    if record.acquisition_hash:
        try:
            prov_rec = blockchain_service.get_ipfs_provenance_record(record.ipfs_cid)
            on_chain_acq = prov_rec.get("acquisition_hash")
            if not on_chain_acq:
                fallback_prov = blockchain_service.get_ipfs_provenance_record(str(record.id))
                on_chain_acq = fallback_prov.get("acquisition_hash")
            if on_chain_acq and on_chain_acq != record.acquisition_hash:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Tier-2 Provenance integrity check FAILED: Hardware acquisition manifest digest "
                        "does not match the immutable provenance hash anchored on Sepolia."
                    ),
                    headers={"X-Integrity-Verified": "false"},
                )
        except HTTPException:
            raise
        except Exception:
            pass

    integrity_ok = True

    # Real file name from DB, not from the chain
    file_name = record.ipfs_file_name or f"record_{record_id}"

    headers = {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "X-Integrity-Verified": "true" if integrity_ok else "false",
        "X-Record-Hash": on_chain_hash or record.record_hash or "",
        "X-Recomputed-Hash": recomputed_hash,
        "X-IPFS-CID": record.ipfs_cid,
        "Access-Control-Expose-Headers": "X-Integrity-Verified, X-Record-Hash, X-Recomputed-Hash, X-IPFS-CID, Content-Disposition",
    }

    # Audit log
    audit = AuditLog(user_id=current_user.id, action="IPFS_DOWNLOAD_RECORD", resource_id=str(record.id))
    db.add(audit)
    db.commit()

    return Response(content=decrypted_bytes, headers=headers)
