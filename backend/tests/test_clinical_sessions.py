def test_clinical_session_lifecycle_and_provenance_digest(client, test_users):
    headers = {"Authorization": f"Bearer {test_users['token_p_a']}"}

    # 1. Start a session
    start_res = client.post("/clinical/session/start", json={
        "device_id": "ESP32-PATIENT-A",
        "capture_mode": "BOTH",
        "sampling_rate_hz": 500
    }, headers=headers)
    assert start_res.status_code == 201
    start_data = start_res.json()
    session_id = start_data["session_id"]
    assert start_data["status"] == "ACQUIRING"

    # 2. Complete session with valid readings
    complete_res = client.post("/clinical/session/complete", json={
        "session_id": session_id,
        "heart_rate": 74,
        "spo2": 98,
        "quality_status": "VALID",
        "acquisition_source": "LIVE_HARDWARE",
        "ecg_samples": [2048, 2080, 2120, 2040, 2048]
    }, headers=headers)
    assert complete_res.status_code == 200
    complete_data = complete_res.json()
    assert complete_data["status"] == "CAPTURE_COMPLETE"
    assert complete_data["quality_status"] == "VALID"
    # Acquisition hash H_acq must be a valid 64-character SHA-256 hex string
    h_acq = complete_data["acquisition_hash"]
    assert len(h_acq) == 64
    assert all(c in "0123456789abcdef" for c in h_acq)

def test_session_invalid_telemetry_handling(client, test_users):
    headers = {"Authorization": f"Bearer {test_users['token_p_a']}"}

    start_res = client.post("/clinical/session/start", json={
        "device_id": "ESP32-PATIENT-A",
        "capture_mode": "BOTH",
        "sampling_rate_hz": 500
    }, headers=headers)
    session_id = start_res.json()["session_id"]

    # Complete session with completely missing/invalid readings (HR=0, SpO2=0, empty ECG)
    complete_res = client.post("/clinical/session/complete", json={
        "session_id": session_id,
        "heart_rate": 0,
        "spo2": 0,
        "quality_status": "INVALID",
        "ecg_samples": []
    }, headers=headers)
    assert complete_res.status_code == 200
    complete_data = complete_res.json()
    assert complete_data["quality_status"] == "INVALID"
    assert complete_data["status"] == "FAILED"

