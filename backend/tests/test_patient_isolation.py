def test_patient_telemetry_isolation(client, test_users):
    headers_a = {"Authorization": f"Bearer {test_users['token_p_a']}"}
    headers_b = {"Authorization": f"Bearer {test_users['token_p_b']}"}

    # Ingest telemetry for Patient A's device
    client.post("/clinical/telemetry/ingest", json={
        "device_id": "ESP32-PATIENT-A",
        "finger_detected": True,
        "heart_rate": 78,
        "spo2": 99,
        "ir_value": 70000,
        "leads_off": False,
        "ecg_samples": [2048, 2050]
    })

    # Patient A calls get_latest_telemetry
    res_a = client.get("/clinical/telemetry/latest", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["patient_id"] == test_users["patient_a"].id
    assert data_a["device_id"] == "ESP32-PATIENT-A"
    assert data_a["heart_rate"] == 78

    # Patient B calls get_latest_telemetry -> MUST NOT receive Patient A's data!
    res_b = client.get("/clinical/telemetry/latest", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["patient_id"] == test_users["patient_b"].id
    assert data_b["device_id"] == "ESP32-PATIENT-B"
    # Patient B's device has no telemetry sent yet -> must be offline/zeroed
    assert data_b["connected"] is False
    assert data_b["heart_rate"] == 0

def test_doctor_consent_required_for_telemetry(client, test_users):
    headers_doc = {"Authorization": f"Bearer {test_users['token_d_a']}"}

    # Doctor tries to view Patient A's telemetry WITHOUT consent -> 403 Forbidden
    res = client.get(f"/clinical/telemetry/latest?patient_id={test_users['patient_a'].id}", headers=headers_doc)
    assert res.status_code == 403
    assert "No active consent" in res.json()["detail"]

    # Now grant consent using /consent/grant/{doctor_id}
    headers_p_a = {"Authorization": f"Bearer {test_users['token_p_a']}"}
    grant_res = client.post(f"/consent/grant/{test_users['doctor_a'].id}", headers=headers_p_a)
    assert grant_res.status_code == 200

    # Now doctor can access telemetry
    res_after = client.get(f"/clinical/telemetry/latest?patient_id={test_users['patient_a'].id}", headers=headers_doc)
    assert res_after.status_code == 200
    assert res_after.json()["patient_id"] == test_users["patient_a"].id

    # Now patient revokes consent using /consent/revoke/{doctor_id}
    revoke_res = client.post(f"/consent/revoke/{test_users['doctor_a'].id}", headers=headers_p_a)
    assert revoke_res.status_code == 200

    # Doctor access is immediately blocked
    res_revoked = client.get(f"/clinical/telemetry/latest?patient_id={test_users['patient_a'].id}", headers=headers_doc)
    assert res_revoked.status_code == 403
    assert "No active consent" in res_revoked.json()["detail"]

def test_unverified_doctor_blocked(client, test_users):
    headers_doc_b = {"Authorization": f"Bearer {test_users['token_d_b']}"}

    # Doctor B is pending verification
    res = client.post("/clinical/prescriptions", json={
        "patient_id": test_users["patient_a"].id,
        "medication_name": "Atorvastatin",
        "dosage": "20mg",
        "frequency": "Once daily",
        "duration": "30 days"
    }, headers=headers_doc_b)
    assert res.status_code == 403
    assert "Doctor account must be verified" in res.json()["detail"]
