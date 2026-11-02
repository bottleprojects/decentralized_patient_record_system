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
    devices = relationship("Device", back_populates="patient", foreign_keys="Device.patient_id")
    measurement_sessions = relationship("MeasurementSession", back_populates="patient", foreign_keys="MeasurementSession.patient_id")

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False) # e.g. "ESP32-VITALS-01"
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=True) # associated patient
    device_status = Column(String, default="active") # active, revoked, suspended
    device_model = Column(String, default="ESP32-WROOM-32")
    firmware_version = Column(String, default="1.0.0")
    secret_key_hash = Column(String, nullable=True) # SHA-256 hex of device-unique pre-shared HMAC key
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    patient = relationship("User", back_populates="devices", foreign_keys=[patient_id])
    sessions = relationship("MeasurementSession", back_populates="device")

class MeasurementSession(Base):
    __tablename__ = "measurement_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False) # UUID
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=True)
    capture_mode = Column(String, default="BOTH") # BOTH, ECG_ONLY, SPO2_ONLY
    status = Column(String, default="IDLE") # IDLE, CALIBRATING, ACQUIRING, VALIDATING, CAPTURE_COMPLETE, FAILED, CANCELLED
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    sampling_rate_hz = Column(Integer, default=500)
    sample_count = Column(Integer, default=0)
    quality_status = Column(String, default="VALID") # VALID, INVALID, SIGNAL_UNAVAILABLE, INSUFFICIENT_SIGNAL
    acquisition_source = Column(String, default="LIVE_HARDWARE") # LIVE_HARDWARE, DEMO_SIMULATED, UNAVAILABLE
    firmware_version = Column(String, default="1.0.0")
    raw_manifest_hash = Column(String, nullable=True) # Acquisition digest H_acq (SHA-256)

    patient = relationship("User", back_populates="measurement_sessions", foreign_keys=[patient_id])
    device = relationship("Device", back_populates="sessions", foreign_keys=[device_id])
    telemetry_packets = relationship("TelemetryPacket", back_populates="session")

class TelemetryPacket(Base):
    __tablename__ = "telemetry_packets"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String, ForeignKey("measurement_sessions.session_id"), nullable=True)
    sequence_number = Column(Integer, nullable=False, default=0)
    device_timestamp = Column(DateTime, nullable=False)
    server_timestamp = Column(DateTime, default=datetime.utcnow)
    heart_rate = Column(Integer, nullable=True)
    spo2 = Column(Integer, nullable=True)
    ir_value = Column(Integer, nullable=True)
    red_value = Column(Integer, nullable=True)
    ecg_samples = Column(Text, nullable=True) # JSON list of integer ADC samples
    sample_rate_hz = Column(Integer, default=500)
    signal_quality = Column(String, default="VALID")
    acquisition_source = Column(String, default="LIVE_HARDWARE")
    verification_status = Column(String, default="VALID") # VALID, INVALID_SIG, REPLAY_REJECTED, STALE

    session = relationship("MeasurementSession", back_populates="telemetry_packets")

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_type = Column(String, nullable=False) # e.g., 'Blood Test', 'Prescription', 'Vitals Telemetry'
    supabase_file_path = Column(String, nullable=True) # Path in Supabase storage (nullable for IPFS-only records)
    ipfs_hash = Column(String, nullable=True) # Kept for legacy compat
    ipfs_cid = Column(String, nullable=True) # IPFS Content Identifier (CID) from Pinata
    ipfs_file_name = Column(String, nullable=True) # Original file name
    ipfs_file_size = Column(Integer, nullable=True) # File size in bytes
    blockchain_tx_hash = Column(String, nullable=True) # The tx hash where the record hash was stored
    blockchain_status = Column(String, default="confirming") # confirming, confirmed, failed
    record_hash = Column(String, nullable=True) # SHA-256 hash of the original file (pre-encrypt)
    acquisition_hash = Column(String, nullable=True) # SHA-256 of acquisition manifest (hardware provenance digest)
    session_id = Column(String, nullable=True) # Bound measurement session identifier
    device_id = Column(String, nullable=True) # Bound hardware device identifier
    acquisition_source = Column(String, default="LIVE_HARDWARE") # LIVE_HARDWARE, DEMO_SIMULATED, IMPORTED_MEASUREMENT
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

class BlockchainTransactionCounter(Base):
    __tablename__ = "blockchain_tx_counters"

    id = Column(Integer, primary_key=True, index=True)
    date_str = Column(String, unique=True, index=True, nullable=False) # "YYYY-MM-DD"
    tx_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
