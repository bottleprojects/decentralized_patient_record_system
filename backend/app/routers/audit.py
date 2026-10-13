from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, AuditLog, RoleEnum
from ..services.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("")
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Patients can view their own audit logs
    if current_user.role == RoleEnum.patient:
        logs = db.query(AuditLog).filter(AuditLog.user_id == current_user.id).order_by(AuditLog.timestamp.desc()).all()
        return logs
    
    # Admins can view all audit logs
    if current_user.role == RoleEnum.admin:
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
        return logs
        
    raise HTTPException(status_code=403, detail="Not authorized to view audit logs")
