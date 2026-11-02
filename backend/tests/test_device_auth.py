import hmac
import hashlib
import time
from datetime import datetime, timezone, timedelta

def test_device_packet_authentication_and_replay(client, test_users):
    headers = {"Authorization": f"Bearer {test_users['token_p_a']}"}
    device_id = "ESP32-TEST-AUTH-01"
    secret_key = "SuperSecretDeviceKey2026!#"

    # 1. Register device
    reg_res = client.post("/clinical/devices/register", json={
        "device_id": device_id,
        "device_model": "ESP32-VITALS-01",
        "firmware_version": "1.2.0",
        "secret_key": secret_key,
        "patient_id": test_users["patient_a"].id
    }, headers=headers)
    assert reg_res.status_code == 201

    # 2. Ingest valid packet with correct HMAC
    seq = 1
    now_iso = datetime.now(timezone.utc).isoformat()
    canonical = f"{device_id}||{seq}|{now_iso}|72|98|65000|False"
    valid_sig = hmac.new(secret_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    ingest_res = client.post("/clinical/telemetry/ingest", json={
        "device_id": device_id,
        "sequence_number": seq,
        "timestamp": now_iso,
        "heart_rate": 72,
        "spo2": 98,
        "ir_value": 65000,
        "leads_off": False,
        "auth_tag": valid_sig,
        "finger_detected": True,
        "ecg_samples": [2048, 2060, 2070]
    })
    assert ingest_res.status_code == 200

    # 3. Ingest packet with INVALID signature -> Must fail 401 Unauthorized
    bad_res = client.post("/clinical/telemetry/ingest", json={
        "device_id": device_id,
        "sequence_number": 2,
        "timestamp": now_iso,
        "heart_rate": 72,
        "spo2": 98,
        "ir_value": 65000,
        "leads_off": False,
        "auth_tag": "invalid_forged_hmac_hex_tag",
        "finger_detected": True,
    })
    assert bad_res.status_code == 401
    assert "Packet signature verification failed" in bad_res.json()["detail"]

    # 4. Anti-replay test: send replayed packet with sequence_number <= 1 -> Must fail 400
    replay_res = client.post("/clinical/telemetry/ingest", json={
        "device_id": device_id,
        "sequence_number": 1, # Replayed sequence
        "timestamp": now_iso,
        "heart_rate": 72,
        "spo2": 98,
        "ir_value": 65000,
        "leads_off": False,
        "auth_tag": valid_sig,
        "finger_detected": True,
    })
    assert replay_res.status_code == 400
    assert "Replay rejected" in replay_res.json()["detail"]

    # 5. Freshness test: packet older than 10.0 seconds -> Must fail 400
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=25)).isoformat()
    stale_canonical = f"{device_id}||10|{stale_time}|72|98|65000|False"
    stale_sig = hmac.new(secret_key.encode("utf-8"), stale_canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    stale_res = client.post("/clinical/telemetry/ingest", json={
        "device_id": device_id,
        "sequence_number": 10,
        "timestamp": stale_time,
        "heart_rate": 72,
        "spo2": 98,
        "ir_value": 65000,
        "leads_off": False,
        "auth_tag": stale_sig,
    })
    assert stale_res.status_code == 400
    assert "Packet freshness violation" in stale_res.json()["detail"]

