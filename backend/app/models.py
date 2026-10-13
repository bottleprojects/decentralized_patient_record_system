from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum

class RoleEnum(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    license_number = Column(String, nullable=True) # Only for doctors
    verification_status = Column(String, default="pending") # pending, verified, rejected (only for doctors)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    records_as_patient = relationship("MedicalRecord", back_populates="patient", foreign_keys="MedicalRecord.patient_id")
    records_as_doctor = relationship("MedicalRecord", back_populates="doctor", foreign_keys="MedicalRecord.doctor_id")

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_type = Column(String, nullable=False) # e.g., 'Blood Test', 'Prescription'
    supabase_file_path = Column(String, nullable=False) # Path in Supabase storage
    ipfs_hash = Column(String, nullable=True) # Optional IPFS hash if used
    blockchain_tx_hash = Column(String, nullable=True) # The tx hash where the record hash was stored
    record_hash = Column(String, nullable=False) # SHA-256 hash of the encrypted file
    description = Column(String, nullable=True) # Description of the medical record
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("User", back_populates="records_as_patient", foreign_keys=[patient_id])
    doctor = relationship("User", back_populates="records_as_doctor", foreign_keys=[doctor_id])

class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="active") # active, revoked
    granted_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False) # e.g., "VIEW_RECORD", "GRANT_CONSENT"
    resource_id = Column(String, nullable=True) # ID of record or consent
    timestamp = Column(DateTime, default=datetime.utcnow)

class ConsentRequest(Base):
    __tablename__ = "consent_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending") # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    duration = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    condition_name = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    observation_type = Column(String, nullable=False) # e.g., Blood Pressure, Heart Rate
    value = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
