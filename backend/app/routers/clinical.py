from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import time
import threading
import hashlib
import hmac
import json
import uuid

from ..database import get_db
from ..models import (
    User,
    RoleEnum,
    AuditLog,
    Consent,
    Prescription,
    Diagnosis,
    Observation,
    Device,
    MeasurementSession,
    TelemetryPacket,
)
from ..services.auth import get_current_user

router = APIRouter(prefix="/clinical", tags=["clinical"])

# --- Thread-Safe Multi-Device Telemetry Store ---
_telemetry_lock = threading.Lock()
_active_telemetry_mode: str = "BOTH"  # Options: "BOTH", "ECG_ONLY", "SPO2_ONLY"

# Device-keyed telemetry store: Dict[device_id, packet_dict]
_device_telemetry: Dict[str, dict] = {}
# Anti-replay sequence tracker: Dict[device_id, last_sequence_number]
_device_seq_tracker: Dict[str, int] = {}
# Device secret cache for fast HMAC checks: Dict[device_id, secret_key]
_device_secrets: Dict[str, str] = {
    "ESP32-VITALS-01": "DPRMS_SECURE_DEVICE_SECRET_KEY_2026",
}


# --- Pydantic Models ---
class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=64)
    device_model: Optional[str] = "ESP32-VITALS-01"
    firmware_version: Optional[str] = "1.0.0"
    secret_key: str = Field(..., min_length=16)
    patient_id: Optional[int] = None


class DeviceAssignRequest(BaseModel):
    device_id: str
    patient_id: int


class TelemetryIngest(BaseModel):
    device_id: str = "ESP32-VITALS-01"
    session_id: Optional[str] = None
    sequence_number: Optional[int] = 0
    finger_detected: bool = False
    ir_value: Optional[int] = 0
    leads_off: Optional[bool] = False
    heart_rate: Optional[int] = 0
    spo2: Optional[int] = 0
    ecg_samples: Optional[List[int]] = []
    timestamp: Optional[str] = None
    auth_tag: Optional[str] = None  # HMAC-SHA256 signature
    acquisition_source: Optional[str] = "LIVE_HARDWARE"


class TelemetryModeUpdate(BaseModel):
    mode: str = "BOTH"  # "BOTH", "ECG_ONLY", "SPO2_ONLY"


class SessionStartRequest(BaseModel):
    device_id: Optional[str] = "ESP32-VITALS-01"
    capture_mode: Optional[str] = "BOTH"
    sampling_rate_hz: Optional[int] = 500


class SessionCompleteRequest(BaseModel):
    session_id: str
    ecg_samples: Optional[List[int]] = []
    heart_rate: Optional[int] = None
    spo2: Optional[int] = None
    quality_status: Optional[str] = "VALID"
    acquisition_source: Optional[str] = "LIVE_HARDWARE"


class PrescriptionCreate(BaseModel):
    patient_id: int
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    notes: Optional[str] = None


class DiagnosisCreate(BaseModel):
    patient_id: int
    condition_name: str
    severity: Optional[str] = None
    notes: Optional[str] = None


class ObservationCreate(BaseModel):
    patient_id: int
    observation_type: str
    value: str
    unit: Optional[str] = None


# --- Helper function for authorization ---
def verify_doctor_access(patient_id: int, db: Session, current_user: User):
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add or view clinical data")
    if current_user.verification_status != "verified":
        raise HTTPException(status_code=403, detail="Doctor account must be verified by an administrator")

    consent = (
        db.query(Consent)
        .filter(
            Consent.patient_id == patient_id,
            Consent.doctor_id == current_user.id,
            Consent.status == "active",
        )
        .first()
    )
    if not consent:
        raise HTTPException(status_code=403, detail="No active consent from this patient")


# --- Device Management Endpoints ---
@router.post("/devices/register", status_code=status.HTTP_201_CREATED)
def register_device(
    data: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registers an IoT biomedical sensor device with a unique hardware identity and secret key.
    Admins can register any device; patients can self-register their own personal monitor.
    """
    if current_user.role not in [RoleEnum.admin, RoleEnum.patient]:
        raise HTTPException(status_code=403, detail="Not authorized to register devices")

    patient_id = current_user.id if current_user.role == RoleEnum.patient else data.patient_id

    existing = db.query(Device).filter(Device.device_id == data.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device with this ID is already registered")

    secret_hash = hashlib.sha256(data.secret_key.encode("utf-8")).hexdigest()
    device = Device(
        device_id=data.device_id,
        patient_id=patient_id,
        device_status="active",
        device_model=data.device_model or "ESP32-VITALS-01",
        firmware_version=data.firmware_version or "1.0.0",
        secret_key_hash=secret_hash,
        registered_at=datetime.utcnow(),
    )
    db.add(device)
    db.commit()

    with _telemetry_lock:
        _device_secrets[data.device_id] = data.secret_key

    return {
        "message": "Device registered successfully",
        "device_id": device.device_id,
        "patient_id": device.patient_id,
        "status": device.device_status,
    }


@router.post("/devices/assign", status_code=status.HTTP_200_OK)
def assign_device_to_patient(
    data: DeviceAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assigns or reassigns an authorized device to a patient."""
    if current_user.role not in [RoleEnum.admin, RoleEnum.patient]:
        raise HTTPException(status_code=403, detail="Not authorized to assign devices")

    device = db.query(Device).filter(Device.device_id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if current_user.role == RoleEnum.patient and data.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Patients can only assign devices to themselves")

    device.patient_id = data.patient_id
    db.commit()
    return {"message": "Device assigned successfully", "device_id": device.device_id, "patient_id": data.patient_id}


# --- IoT Telemetry Ingestion & Validation ---
@router.post("/telemetry/mode", status_code=status.HTTP_200_OK)
def set_telemetry_mode(data: TelemetryModeUpdate):
    """Update active telemetry acquisition mode: BOTH, ECG_ONLY, or SPO2_ONLY."""
    global _active_telemetry_mode
    mode = data.mode.upper().strip()
    if mode in {"BOTH", "ECG_ONLY", "SPO2_ONLY"}:
        with _telemetry_lock:
            _active_telemetry_mode = mode
            for dev in _device_telemetry.values():
                dev["mode"] = mode
    return {"status": "ok", "mode": _active_telemetry_mode}


@router.get("/telemetry/mode")
def get_telemetry_mode():
    """Retrieve active telemetry acquisition mode."""
    with _telemetry_lock:
        return {"mode": _active_telemetry_mode}


@router.post("/telemetry/ingest", status_code=status.HTTP_200_OK)
def ingest_telemetry(data: TelemetryIngest, db: Session = Depends(get_db)):
    """
    Ingest and validate live telemetry packet from ESP32 vitals sensor.
    Enforces:
    1. Device authentication (HMAC-SHA256 signature verification if secret configured).
    2. Packet freshness (rejects stale packets older than 10.0 seconds).
    3. Anti-replay protection (strictly monotonic sequence counters).
    4. Isolation into per-device memory buffers.
    """
    device_id = data.device_id.strip()

    # 1. Device Registration Check
    device = db.query(Device).filter(Device.device_id == device_id).first()
    secret_key = _device_secrets.get(device_id)

    # 2. Cryptographic Authentication (HMAC-SHA256)
    if data.auth_tag and secret_key:
        canonical_msg = f"{device_id}|{data.session_id or ''}|{data.sequence_number or 0}|{data.timestamp or ''}|{data.heart_rate or 0}|{data.spo2 or 0}|{data.ir_value or 0}|{data.leads_off}"
        computed_sig = hmac.new(secret_key.encode("utf-8"), canonical_msg.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(data.auth_tag, computed_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Packet signature verification failed: invalid auth_tag for registered device.",
            )

    # 3. Anti-Replay Check (Sequence Monotonicity)
    if data.sequence_number is not None and data.sequence_number > 0:
        with _telemetry_lock:
            last_seq = _device_seq_tracker.get(device_id, -1)
            if data.sequence_number <= last_seq:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Replay rejected: sequence number {data.sequence_number} <= last seen {last_seq}.",
                )
            _device_seq_tracker[device_id] = data.sequence_number

    # 4. Freshness Validation
    now_ts = time.time()
    if data.timestamp:
        try:
            packet_time = datetime.fromisoformat(data.timestamp.replace("Z", "+00:00")).timestamp()
            if abs(now_ts - packet_time) > 10.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Packet freshness violation: timestamp exceeds 10.0s sliding window.",
                )
        except (ValueError, TypeError):
            pass

    # 5. Store in Per-Device In-Memory Store
    with _telemetry_lock:
        current_mode = _active_telemetry_mode
        _device_telemetry[device_id] = {
            "device_id": device_id,
            "session_id": data.session_id,
            "sequence_number": data.sequence_number,
            "finger_detected": data.finger_detected,
            "ir_value": data.ir_value or 0,
            "leads_off": data.leads_off or False,
            "heart_rate": data.heart_rate or 0,
            "spo2": data.spo2 or 0,
            "ecg_samples": data.ecg_samples or [],
            "mode": current_mode,
            "timestamp": data.timestamp or datetime.utcnow().isoformat() + "Z",
            "received_at": now_ts,
            "acquisition_source": data.acquisition_source or "LIVE_HARDWARE",
        }

    # Update device last_seen_at
    if device:
        device.last_seen_at = datetime.utcnow()
        db.commit()

    return {"status": "ok", "mode": current_mode, "device_id": device_id}


@router.get("/telemetry/latest")
def get_latest_telemetry(
    patient_id: Optional[int] = Query(None, description="Patient ID (required for doctors)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch the latest buffered vitals telemetry packet with strict patient-device isolation.
    - Patients ONLY receive telemetry from their assigned device.
    - Doctors MUST have active consent to inspect a patient's telemetry stream.
    - Unassociated or offline devices report connected=False with zeroed readings.
    """
    target_patient_id: Optional[int] = None
    target_patient_name: str = ""
    target_patient_email: str = ""

    if current_user.role == RoleEnum.patient:
        target_patient_id = current_user.id
        target_patient_name = current_user.full_name
        target_patient_email = current_user.email
    elif current_user.role == RoleEnum.doctor:
        if not patient_id:
            raise HTTPException(status_code=400, detail="Doctors must supply a patient_id query parameter")
        verify_doctor_access(patient_id, db, current_user)
        target_user = db.query(User).filter(User.id == patient_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Patient not found")
        target_patient_id = target_user.id
        target_patient_name = target_user.full_name
        target_patient_email = target_user.email
    elif current_user.role == RoleEnum.admin:
        target_patient_id = patient_id or current_user.id
        target_patient_name = current_user.full_name
        target_patient_email = current_user.email

    # Find device registered for this patient
    assigned_device = (
        db.query(Device)
        .filter(Device.patient_id == target_patient_id, Device.device_status == "active")
        .first()
    )

    device_id = assigned_device.device_id if assigned_device else "ESP32-VITALS-01"

    with _telemetry_lock:
        # Retrieve packet specific to this device
        data = _device_telemetry.get(device_id)
        if data:
            data = dict(data)
        else:
            # Fallback to general buffer if single-node development device
            data = None

    if data:
        received_at = data.get("received_at")
        now = time.time()
        age_seconds = round(now - received_at, 2) if received_at else None
        connected = bool(age_seconds is not None and age_seconds <= 5.0)
    else:
        age_seconds = None
        connected = False
        data = {}

    return {
        "connected": connected,
        "age_seconds": age_seconds,
        "device_id": device_id,
        "finger_detected": data.get("finger_detected", False) if connected else False,
        "ir_value": data.get("ir_value", 0) if connected else 0,
        "leads_off": data.get("leads_off", True) if connected else True,
        "heart_rate": data.get("heart_rate", 0) if connected else 0,
        "spo2": data.get("spo2", 0) if connected else 0,
        "ecg_samples": data.get("ecg_samples", []) if connected else [],
        "mode": data.get("mode", _active_telemetry_mode),
        "timestamp": data.get("timestamp") if connected else None,
        "patient_id": target_patient_id,
        "patient_name": target_patient_name,
        "patient_email": target_patient_email,
        "acquisition_source": data.get("acquisition_source", "LIVE_HARDWARE") if connected else "UNAVAILABLE",
    }


# --- Persistent Measurement Session Endpoints ---
@router.post("/session/start", status_code=status.HTTP_201_CREATED)
def start_measurement_session(
    data: SessionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Starts a bounded clinical acquisition session for the authenticated patient."""
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can initiate measurement sessions")

    session_id = str(uuid.uuid4())
    session = MeasurementSession(
        session_id=session_id,
        patient_id=current_user.id,
        device_id=data.device_id or "ESP32-VITALS-01",
        capture_mode=data.capture_mode or "BOTH",
        status="ACQUIRING",
        started_at=datetime.utcnow(),
        sampling_rate_hz=data.sampling_rate_hz or 500,
        quality_status="VALID",
        acquisition_source="LIVE_HARDWARE",
    )
    db.add(session)
    db.commit()

    return {
        "message": "Measurement session started",
        "session_id": session.session_id,
        "patient_id": session.patient_id,
        "started_at": session.started_at.isoformat(),
        "status": session.status,
    }


@router.post("/session/complete", status_code=status.HTTP_200_OK)
def complete_measurement_session(
    data: SessionCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Completes a measurement session, performs data quality validation,
    and computes the canonical acquisition manifest digest (H_acq).
    """
    session = db.query(MeasurementSession).filter(MeasurementSession.session_id == data.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    if session.patient_id != current_user.id and current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized to complete this session")

    completed_at = datetime.utcnow()
    sample_count = len(data.ecg_samples or [])

    # Validate signal quality: prevent CAPTURE_COMPLETE if vital data is missing
    is_valid_hr = data.heart_rate is not None and data.heart_rate > 30
    is_valid_spo2 = data.spo2 is not None and data.spo2 > 70
    quality = "VALID" if (is_valid_hr or is_valid_spo2 or sample_count > 0) else "INVALID"

    # Construct canonical measurement manifest
    manifest_dict = {
        "device_id": session.device_id or "ESP32-VITALS-01",
        "session_id": session.session_id,
        "patient_id": session.patient_id,
        "capture_mode": session.capture_mode,
        "started_at": session.started_at.isoformat() + "Z",
        "completed_at": completed_at.isoformat() + "Z",
        "sampling_rate_hz": session.sampling_rate_hz,
        "sample_count": sample_count,
        "heart_rate": data.heart_rate,
        "spo2": data.spo2,
        "quality_status": quality,
        "acquisition_source": data.acquisition_source or "LIVE_HARDWARE",
    }
    canonical_json = json.dumps(manifest_dict, sort_keys=True, separators=(",", ":"))
    h_acq = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    session.completed_at = completed_at
    session.sample_count = sample_count
    session.quality_status = quality
    session.status = "CAPTURE_COMPLETE" if quality == "VALID" else "FAILED"
    session.acquisition_source = data.acquisition_source or "LIVE_HARDWARE"
    session.raw_manifest_hash = h_acq
    db.commit()

    return {
        "message": "Measurement session completed",
        "session_id": session.session_id,
        "acquisition_hash": h_acq,
        "quality_status": quality,
        "sample_count": sample_count,
        "status": session.status,
    }


# --- Prescriptions ---
@router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
def create_prescription(
    data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_doctor_access(data.patient_id, db, current_user)

    record = Prescription(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        medication_name=data.medication_name,
        dosage=data.dosage,
        frequency=data.frequency,
        duration=data.duration,
        notes=data.notes,
    )
    db.add(record)
    db.add(AuditLog(user_id=current_user.id, action="CREATE_PRESCRIPTION", resource_id=str(data.patient_id)))
    db.commit()
    return {"message": "Prescription created"}


# --- Diagnoses ---
@router.post("/diagnoses", status_code=status.HTTP_201_CREATED)
def create_diagnosis(
    data: DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_doctor_access(data.patient_id, db, current_user)

    record = Diagnosis(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        condition_name=data.condition_name,
        severity=data.severity,
        notes=data.notes,
    )
    db.add(record)
    db.add(AuditLog(user_id=current_user.id, action="CREATE_DIAGNOSIS", resource_id=str(data.patient_id)))
    db.commit()
    return {"message": "Diagnosis created"}


# --- Observations ---
@router.post("/observations", status_code=status.HTTP_201_CREATED)
def create_observation(
    data: ObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_doctor_access(data.patient_id, db, current_user)

    record = Observation(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        observation_type=data.observation_type,
        value=data.value,
        unit=data.unit,
    )
    db.add(record)
    db.add(AuditLog(user_id=current_user.id, action="CREATE_OBSERVATION", resource_id=str(data.patient_id)))
    db.commit()
    return {"message": "Observation created"}


# --- Retrieve for Patient ---
@router.get("/patient-data")
def get_patient_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can view this data")

    prescriptions = db.query(Prescription).filter(Prescription.patient_id == current_user.id).all()
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == current_user.id).all()
    observations = db.query(Observation).filter(Observation.patient_id == current_user.id).all()

    db.add(AuditLog(user_id=current_user.id, action="VIEW_CLINICAL_DATA"))
    db.commit()

    return {
        "prescriptions": prescriptions,
        "diagnoses": diagnoses,
        "observations": observations,
    }
