import pytest
from backend.app.models import Device, MeasurementSession, Consent

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
    from backend.app.models import User, RoleEnum
    from backend.app.services.auth import get_password_hash, create_access_token

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
