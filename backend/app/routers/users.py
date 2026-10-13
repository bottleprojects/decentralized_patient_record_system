from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..database import get_db
from ..models import User, RoleEnum
from ..services.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: RoleEnum
    license_number: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user.role == RoleEnum.doctor and not user.license_number:
        raise HTTPException(status_code=400, detail="License number is required for doctors")

    import random
    
    # Generate random 6 digit ID
    while True:
        random_id = random.randint(100000, 999999)
        existing = db.query(User).filter(User.id == random_id).first()
        if not existing:
            break

    hashed_password = get_password_hash(user.password)
    new_user = User(
        id=random_id,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        license_number=user.license_number
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id}

@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    # The deployed frontend has a bug where it sends url-encoded data but sets Content-Type to application/json
    # We must manually parse the body as a string and extract the fields
    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')
    
    import urllib.parse
    parsed_data = urllib.parse.parse_qs(body_str)
    
    username = parsed_data.get('username', [None])[0]
    password = parsed_data.get('password', [None])[0]
    # Fallback to json if somehow it actually is json
    if not username and not password:
        try:
            import json
            json_data = json.loads(body_str)
            username = json_data.get('username')
            password = json_data.get('password')
        except:
            pass

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username or password")

    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}
@router.get("/me")
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "license_number": current_user.license_number
    }

@router.get("/patients")
def get_patients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Only doctors can search for patients.")
    
    from ..models import Consent, ConsentRequest
    patients = db.query(User).filter(User.role == RoleEnum.patient).all()
    result = []
    for p in patients:
        status = "none"
        if db.query(Consent).filter(Consent.patient_id == p.id, Consent.doctor_id == current_user.id, Consent.status == "active").first():
            status = "granted"
        elif db.query(ConsentRequest).filter(ConsentRequest.patient_id == p.id, ConsentRequest.doctor_id == current_user.id, ConsentRequest.status == "pending").first():
            status = "pending"
        result.append({"id": p.id, "email": p.email, "full_name": p.full_name, "consent_status": status})
    return result

@router.get("/doctors")
def get_doctors(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can search for doctors.")
    
    doctors = db.query(User).filter(User.role == RoleEnum.doctor).all()
    return [{"id": d.id, "email": d.email, "full_name": d.full_name, "license_number": d.license_number} for d in doctors]

@router.get("")
def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    
    users = db.query(User).all()
    # Mask passwords before returning
    for u in users:
        u.hashed_password = "*****"
    return users

@router.get("/doctors/pending")
def get_pending_doctors(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
        
    doctors = db.query(User).filter(User.role == RoleEnum.doctor, User.verification_status == "pending").all()
    return [{"id": d.id, "email": d.email, "full_name": d.full_name, "license_number": d.license_number} for d in doctors]

@router.post("/{user_id}/verify")
def verify_doctor(user_id: int, status: str = "verified", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
        
    doctor = db.query(User).filter(User.id == user_id, User.role == RoleEnum.doctor).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    if status not in ["verified", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    doctor.verification_status = status
    db.commit()
    return {"message": f"Doctor verification status updated to {status}"}

@router.delete("/admin/cleanup")
def cleanup_database(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    
    try:
        from ..models import AuditLog, Consent, MedicalRecord
        
        # Delete dependent tables first
        db.query(AuditLog).delete()
        db.query(Consent).delete()
        
        # Clear files from Supabase
        from ..services.storage import storage_service
        try:
            bucket = storage_service.client.storage.from_(storage_service.bucket_name)
            folders = bucket.list()
            paths = []
            for f in folders:
                folder_name = f.get('name')
                if folder_name and folder_name != '.emptyFolderPlaceholder':
                    # Need to list files inside the folder (patient_id)
                    subfiles = bucket.list(folder_name)
                    for sf in subfiles:
                        file_name = sf.get('name')
                        if file_name and file_name != '.emptyFolderPlaceholder':
                            paths.append(f"{folder_name}/{file_name}")
            if paths:
                bucket.remove(paths)
        except Exception as e:
            print(f"Warning: Failed to clean Supabase bucket: {e}")
            
        db.query(MedicalRecord).delete()
        
        # Delete all non-admin users
        db.query(User).filter(User.role != RoleEnum.admin).delete()
        
        db.commit()
        return {"message": "Database successfully cleaned up (all non-admin data removed)."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clean database: {str(e)}")

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_to_delete.role == RoleEnum.admin:
        raise HTTPException(status_code=400, detail="Cannot delete an admin user")

    from ..models import MedicalRecord, Consent, AuditLog, ConsentRequest, Prescription, Diagnosis, Observation
    
    # Manually delete dependent records to avoid Foreign Key violations
    db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
    db.query(Consent).filter((Consent.patient_id == user_id) | (Consent.doctor_id == user_id)).delete()
    db.query(ConsentRequest).filter((ConsentRequest.patient_id == user_id) | (ConsentRequest.doctor_id == user_id)).delete()
    db.query(Prescription).filter((Prescription.patient_id == user_id) | (Prescription.doctor_id == user_id)).delete()
    db.query(Diagnosis).filter((Diagnosis.patient_id == user_id) | (Diagnosis.doctor_id == user_id)).delete()
    db.query(Observation).filter((Observation.patient_id == user_id) | (Observation.doctor_id == user_id)).delete()
    db.query(MedicalRecord).filter((MedicalRecord.patient_id == user_id) | (MedicalRecord.doctor_id == user_id)).delete()
    db.delete(user_to_delete)
    
    db.commit()
    return {"message": "User and all associated data successfully deleted"}

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
