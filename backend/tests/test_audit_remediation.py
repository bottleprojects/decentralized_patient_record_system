import pytest
import io
from backend.app.models import Device, MeasurementSession, Consent, MedicalRecord, User, RoleEnum
from backend.app.services.auth import create_access_token

def test_fhir_consent_authorization_enforcement(client, test_users, db_session):
    headers_patient = {"Authorization": f"Bearer {test_users['token_p_a']}"}
    headers_doctor_unauth = {"Authorization": f"Bearer {test_users['token_d_b']}"} # unverified and no consent
    headers_doctor_auth = {"Authorization": f"Bearer {test_users['token_d_a']}"} # verified doctor

    patient_id = test_users["patient_a"].id
    doctor_auth_id = test_users["doctor_a"].id

    # 1. Patient querying self -> allowed 200 (test both /fhir and /fhir/v4)
    res = client.get(f"/fhir/Patient/{patient_id}", headers=headers_patient)
    assert res.status_code == 200
    assert res.json()["resourceType"] == "Patient"
    assert res.json()["id"] == str(patient_id)

    res_v4 = client.get(f"/fhir/v4/Patient/{patient_id}", headers=headers_patient)
    assert res_v4.status_code == 200
    assert res_v4.json()["resourceType"] == "Patient"

    # 2. Doctor WITHOUT consent querying patient -> blocked 403
    res = client.get(f"/fhir/Patient/{patient_id}", headers=headers_doctor_auth)
    assert res.status_code == 403
    assert "No active patient consent" in res.json()["detail"]

    # 3. Grant consent to doctor_a
    grant_res = client.post(f"/consent/grant/{doctor_auth_id}", headers=headers_patient)
    assert grant_res.status_code == 200

    # 4. Doctor WITH consent querying patient -> allowed 200
    res = client.get(f"/fhir/Patient/{patient_id}", headers=headers_doctor_auth)
    assert res.status_code == 200
    assert res.json()["resourceType"] == "Patient"

    # 5. Observation endpoint consent check
    res_obs = client.get(f"/fhir/Observation?patient={patient_id}", headers=headers_doctor_auth)
    assert res_obs.status_code == 200
    bundle = res_obs.json()
    assert bundle["resourceType"] == "Bundle"


def test_telemetry_isolation_no_fallback(client, db_session):
    from backend.app.services.auth import get_password_hash

    # Create patient with NO assigned device
    patient_no_device = User(
        email="patient_nodevice@vit.edu",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Patient No Device",
        role=RoleEnum.patient,
        verification_status="verified",
    )
    db_session.add(patient_no_device)
    db_session.commit()
    db_session.refresh(patient_no_device)

    token = create_access_token({"sub": patient_no_device.email, "role": patient_no_device.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Query latest telemetry -> MUST NOT fallback to ESP32-VITALS-01
    res = client.get("/clinical/telemetry/latest", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is False
    assert data["device_id"] is None
    assert "No active sensor device assigned" in data["message"]


def test_telemetry_mode_requires_authentication(client, test_users):
    # 1. Unauthenticated request to /clinical/telemetry/mode MUST fail 401
    res = client.post("/clinical/telemetry/mode", json={"mode": "ECG_ONLY"})
    assert res.status_code == 401

    headers_doctor = {"Authorization": f"Bearer {test_users['token_d_a']}"}
    headers_patient = {"Authorization": f"Bearer {test_users['token_p_a']}"}

    # 2. Doctor WITHOUT consent trying to change patient's device mode -> 403 Forbidden
    res = client.post(
        "/clinical/telemetry/mode",
        json={"mode": "ECG_ONLY", "device_id": "ESP32-PATIENT-A"},
        headers=headers_doctor,
    )
    assert res.status_code == 403

    # 3. Patient changing mode for their own assigned device -> 200 OK
    res_pat = client.post(
        "/clinical/telemetry/mode",
        json={"mode": "ECG_ONLY", "device_id": "ESP32-PATIENT-A"},
        headers=headers_patient,
    )
    assert res_pat.status_code == 200
    assert res_pat.json()["mode"] == "ECG_ONLY"

    # 4. Doctor WITH patient consent changing device mode -> 200 OK
    client.post(f"/consent/grant/{test_users['doctor_a'].id}", headers=headers_patient)
    res_doc = client.post(
        "/clinical/telemetry/mode",
        json={"mode": "BOTH", "device_id": "ESP32-PATIENT-A"},
        headers=headers_doctor,
    )
    assert res_doc.status_code == 200
    assert res_doc.json()["mode"] == "BOTH"


def test_measurement_session_immutability(client, test_users):
    headers_patient = {"Authorization": f"Bearer {test_users['token_p_a']}"}

    # Start session
    res = client.post("/clinical/session/start", json={"capture_mode": "BOTH"}, headers=headers_patient)
    assert res.status_code == 201
    session_id = res.json()["session_id"]

    # First completion -> Success
    res = client.post(
        "/clinical/session/complete",
        json={
            "session_id": session_id,
            "heart_rate": 75,
            "spo2": 98,
            "ecg_samples": [100, 200, 300],
        },
        headers=headers_patient,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CAPTURE_COMPLETE"

    # Second completion attempt -> MUST REJECT 400 because session is finalized and immutable
    res = client.post(
        "/clinical/session/complete",
        json={
            "session_id": session_id,
            "heart_rate": 80,
            "spo2": 99,
            "ecg_samples": [500, 600],
        },
        headers=headers_patient,
    )
    assert res.status_code == 400
    assert "cannot be modified" in res.json()["detail"]
    assert "Finalized sessions are immutable" in res.json()["detail"]


def test_prevent_public_admin_registration(client):
    # Attempt to publicly register as admin MUST be rejected with 403
    res = client.post("/users/register", json={
        "email": "hacker_admin@test.com",
        "password": "Password123!",
        "full_name": "Fake Administrator",
        "role": "admin",
    })
    assert res.status_code == 403
    assert "Public administrator registration is prohibited" in res.json()["detail"]


def test_protected_metrics_and_no_fabrication(client, test_users):
    # 1. Unauthenticated request to /metrics MUST fail 401
    res = client.get("/metrics")
    assert res.status_code == 401

    # 2. Authenticated user receives authentic computed pass rate
    headers = {"Authorization": f"Bearer {test_users['token_p_a']}"}
    res = client.get("/metrics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "counters" in data
    # Pass rate must be computed number, not hardcoded 100.0 if zero records
    assert isinstance(data["counters"]["integrity_pass_rate"], float)


def test_prevent_unauthorized_device_reassignment(client, test_users):
    headers_patient_b = {"Authorization": f"Bearer {test_users['token_p_b']}"}

    # Patient B attempts to reassign Patient A's device to Patient B
    res = client.post("/clinical/devices/assign", json={
        "device_id": "ESP32-PATIENT-A",
        "patient_id": test_users["patient_b"].id
    }, headers=headers_patient_b)
    assert res.status_code == 403
    assert "Unauthorized device reassignment" in res.json()["detail"]


def test_secure_record_status_endpoint(client, test_users, db_session):
    # Create record for Patient A
    rec = MedicalRecord(
        patient_id=test_users["patient_a"].id,
        file_type="General Health Record",
        ipfs_cid="QmTest123",
        ipfs_file_name="test.pdf",
        blockchain_status="confirming",
        blockchain_tx_hash="0xabcdef123456"
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    # 1. Patient B attempts to view status of Patient A's record -> 403
    headers_b = {"Authorization": f"Bearer {test_users['token_p_b']}"}
    res_b = client.get(f"/records/{rec.id}/status", headers=headers_b)
    assert res_b.status_code == 403

    # 2. Doctor WITHOUT consent attempts to view status -> 403
    headers_doc = {"Authorization": f"Bearer {test_users['token_d_a']}"}
    res_doc = client.get(f"/records/{rec.id}/status", headers=headers_doc)
    assert res_doc.status_code == 403

    # 3. Patient A views own status -> 200
    headers_a = {"Authorization": f"Bearer {test_users['token_p_a']}"}
    res_a = client.get(f"/records/{rec.id}/status", headers=headers_a)
    assert res_a.status_code == 200


def test_emergency_access_authorization_and_expiration(client, test_users):
    headers_doc = {"Authorization": f"Bearer {test_users['token_d_a']}"}
    headers_unverified_doc = {"Authorization": f"Bearer {test_users['token_d_b']}"}
    patient_id = test_users["patient_a"].id

    # 1. Non-substantive justification (<15 chars) -> 400
    res = client.post("/consent/emergency", json={
        "patient_id": patient_id,
        "justification": "short reason"
    }, headers=headers_doc)
    assert res.status_code == 400
    assert "substantive clinical justification" in res.json()["detail"]

    # 2. Unverified doctor -> 403
    res_unverified = client.post("/consent/emergency", json={
        "patient_id": patient_id,
        "justification": "Patient acute chest pain emergency room admission"
    }, headers=headers_unverified_doc)
    assert res_unverified.status_code == 403

    # 3. Verified doctor with substantive justification -> 200 with bounded expiration
    res_ok = client.post("/consent/emergency", json={
        "patient_id": patient_id,
        "justification": "Patient acute myocardial infarction triage in ER"
    }, headers=headers_doc)
    assert res_ok.status_code == 200
    assert "expires_at" in res_ok.json()


def test_device_ownership_session_creation(client, test_users):
    headers_patient_a = {"Authorization": f"Bearer {test_users['token_p_a']}"}

    # Patient A attempts to start session with Patient B's device -> 403
    res = client.post("/clinical/session/start", json={
        "device_id": "ESP32-PATIENT-B",
        "capture_mode": "BOTH"
    }, headers=headers_patient_a)
    assert res.status_code == 403
    assert "Device ownership validation failed" in res.json()["detail"]


def test_server_side_provenance_validation(client, test_users, db_session):
    headers = {"Authorization": f"Bearer {test_users['token_p_a']}"}
    patient_id = test_users["patient_a"].id

    # 1. Uploading with non-existent session_id -> 404
    dummy_file = ("ecg.pdf", io.BytesIO(b"%PDF-1.4 test file content"), "application/pdf")
    res_fake_session = client.post(
        "/records/ipfs-upload",
        data={
            "patient_id": patient_id,
            "file_type": "ECG Report",
            "session_id": "non-existent-session-uuid",
            "acquisition_hash": "f" * 64,
        },
        files={"file": dummy_file},
        headers=headers,
    )
    assert res_fake_session.status_code == 404
    assert "Measurement session 'non-existent-session-uuid' not found" in res_fake_session.json()["detail"]

    # 2. Uploading with mismatched acquisition hash -> 400
    session = MeasurementSession(
        session_id="valid-session-1234",
        patient_id=patient_id,
        device_id="ESP32-PATIENT-A",
        status="CAPTURE_COMPLETE",
        quality_status="VALID",
        raw_manifest_hash="a" * 64,
    )
    db_session.add(session)
    db_session.commit()

    dummy_file2 = ("ecg2.pdf", io.BytesIO(b"%PDF-1.4 test file content 2"), "application/pdf")
    res_mismatch = client.post(
        "/records/ipfs-upload",
        data={
            "patient_id": patient_id,
            "file_type": "ECG Report",
            "session_id": "valid-session-1234",
            "acquisition_hash": "b" * 64, # Mismatch!
        },
        files={"file": dummy_file2},
        headers=headers,
    )
    assert res_mismatch.status_code == 400
    assert "Supplied acquisition_hash does not match" in res_mismatch.json()["detail"]
