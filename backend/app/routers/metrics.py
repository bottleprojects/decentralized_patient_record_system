import os
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import MedicalRecord, User, Consent, RoleEnum
from ..services.auth import get_current_user

router = APIRouter(tags=["metrics"])


def _format_bytes(num_bytes: int) -> str:
    if not num_bytes or num_bytes <= 0:
        return "0 KB"
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.2f} MB"


@router.get("/metrics")
@router.get("/api/metrics")
@router.get("/stats")
@router.get("/api/stats")
def get_system_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns authentic system counters, storage statistics, and role-scoped record metadata.
    Enforces authentication and active patient consent boundaries.
    """
    # 1. Total records
    total_records = db.query(MedicalRecord).count()

    # 2. Total IPFS storage bytes
    total_bytes = db.query(func.coalesce(func.sum(MedicalRecord.ipfs_file_size), 0)).scalar() or 0

    # 3. Confirmed records and actual integrity pass rate
    confirmed_records = db.query(MedicalRecord).filter(
        MedicalRecord.blockchain_status == "confirmed"
    ).count()
    actual_integrity_pass_rate = round((confirmed_records / total_records * 100.0), 2) if total_records > 0 else 0.0

    # 4. User and consent counts
    total_patients = db.query(User).filter(User.role == RoleEnum.patient).count()
    total_doctors = db.query(User).filter(User.role == RoleEnum.doctor).count()
    active_consents = db.query(Consent).filter(Consent.status == "active").count()

    # 5. Role-scoped recent uploaded records (Privacy protection: never leak other patients' CIDs or metadata)
    if current_user.role == RoleEnum.admin:
        recent_records_raw = db.query(MedicalRecord).order_by(MedicalRecord.id.desc()).limit(5).all()
    elif current_user.role == RoleEnum.doctor:
        consents = db.query(Consent).filter(Consent.doctor_id == current_user.id, Consent.status == "active").all()
        patient_ids = [c.patient_id for c in consents]
        recent_records_raw = db.query(MedicalRecord).filter(MedicalRecord.patient_id.in_(patient_ids)).order_by(MedicalRecord.id.desc()).limit(5).all()
    else:
        recent_records_raw = db.query(MedicalRecord).filter(MedicalRecord.patient_id == current_user.id).order_by(MedicalRecord.id.desc()).limit(5).all()

    gateway_url = os.getenv("PINATA_GATEWAY", "https://gateway.pinata.cloud").rstrip("/")

    recent_uploads = []
    for r in recent_records_raw:
        recent_uploads.append({
            "id": r.id,
            "file_name": r.ipfs_file_name or r.file_type or f"Record #{r.id}",
            "file_type": r.file_type,
            "file_size": r.ipfs_file_size or 0,
            "file_size_formatted": _format_bytes(r.ipfs_file_size or 0),
            "ipfs_cid": r.ipfs_cid,
            "ipfs_gateway_url": f"{gateway_url}/ipfs/{r.ipfs_cid}" if r.ipfs_cid else None,
            "record_hash": r.record_hash,
            "blockchain_tx_hash": r.blockchain_tx_hash,
            "blockchain_status": r.blockchain_status or "confirmed",
            "integrity_verified": r.blockchain_status == "confirmed",
            "created_at": r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat(),
        })

    return {
        "counters": {
            "total_records": total_records,
            "total_ipfs_storage_bytes": total_bytes,
            "total_ipfs_storage_formatted": _format_bytes(total_bytes),
            "integrity_pass_rate": actual_integrity_pass_rate,
            "confirmed_records": confirmed_records,
            "encryption_standard": "AES-256-GCM",
            "total_patients": total_patients,
            "total_doctors": total_doctors,
            "active_consents": active_consents,
            "network": "Ethereum Sepolia",
        },
        "charts": {
            "gas_comparison": {
                "naive_onchain": {
                    "label": "Naive On-Chain (5 MB X-Ray)",
                    "gas": 3200000000,
                    "gas_formatted": "~3.2B Gas",
                    "storage_size": "5,242,880 Bytes",
                    "feasible": False,
                    "cost_estimate_usd": "$128,000+",
                    "note": "Exceeds Ethereum block gas limit (30M) by 106x. Technically impossible to mine.",
                },
                "hybrid_architecture": {
                    "label": "DPRMS Hybrid (IPFS + On-Chain)",
                    "gas": 75000,
                    "gas_formatted": "~75,000 Gas",
                    "storage_size": "128 Bytes (CID + Hash)",
                    "feasible": True,
                    "cost_estimate_usd": "< $0.05",
                    "reduction_percentage": "99.998%",
                    "note": "Constant O(1) gas cost independent of original file size.",
                },
            },
        },
        "recent_uploads": recent_uploads,
    }
