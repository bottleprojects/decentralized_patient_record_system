import io
import hashlib
from backend.app.models import MedicalRecord
from backend.app.services.crypto import crypto_service
from backend.app.services.ipfs import ipfs_service
from backend.app.services.blockchain import blockchain_service

def test_record_upload_and_fail_closed_verification(client, test_users, db_session, monkeypatch):
    headers = {"Authorization": f"Bearer {test_users['token_p_a']}"}

    file_content = b"ORIGINAL_CLINICAL_REPORT_PATIENT_ALPHA_2026"
    expected_hash = hashlib.sha256(file_content).hexdigest()

    # Mock IPFS upload
    monkeypatch.setattr(ipfs_service, "upload", lambda b, fn: "QmTestUploadCID1234567890")

    # 1. Upload record
    files = {"file": ("report.pdf", io.BytesIO(file_content), "application/pdf")}
    data = {
        "patient_id": test_users["patient_a"].id,
        "file_type": "Observation (Vitals)",
        "description": "Lead-II ECG Report",
        "acquisition_source": "LIVE_HARDWARE",
        "device_id": "ESP32-PATIENT-A",
        "acquisition_hash": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    }

    upload_res = client.post("/records/ipfs-upload", files=files, data=data, headers=headers)
    assert upload_res.status_code == 201
    resp_data = upload_res.json()
    record_id = resp_data["record_id"]
    cid = resp_data["cid"]
    assert cid == "QmTestUploadCID1234567890"

    # 2. Update record status in DB to confirmed for download test
    rec = db_session.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    rec.blockchain_status = "confirmed"
    db_session.commit()

    # 3. Successful download with verified integrity
    valid_encrypted = crypto_service.encrypt(file_content)
    monkeypatch.setattr(ipfs_service, "download", lambda c: valid_encrypted)
    monkeypatch.setattr(blockchain_service, "get_ipfs_record", lambda c: {"sha256_hash": expected_hash})

    dl_res = client.get(f"/records/{record_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.content == file_content
    assert dl_res.headers["X-Integrity-Verified"] == "true"
    assert dl_res.headers["X-Record-Hash"] == expected_hash

    # 4. Fail-closed: Tampered ciphertext (corrupted byte) -> 422
    tampered_bytes = bytearray(valid_encrypted)
    tampered_bytes[-1] ^= 0xFF
    monkeypatch.setattr(ipfs_service, "download", lambda c: bytes(tampered_bytes))

    dl_tamper_res = client.get(f"/records/{record_id}/download", headers=headers)
    assert dl_tamper_res.status_code == 422
    assert dl_tamper_res.headers["X-Integrity-Verified"] == "false"

    # 5. Fail-closed: On-chain hash mismatch -> 409 Conflict
    forged_content = b"FORGED_CLINICAL_DATA_SUBSTITUTED"
    forged_encrypted = crypto_service.encrypt(forged_content)
    monkeypatch.setattr(ipfs_service, "download", lambda c: forged_encrypted)
    monkeypatch.setattr(blockchain_service, "get_ipfs_record", lambda c: {"sha256_hash": expected_hash})

    dl_mismatch_res = client.get(f"/records/{record_id}/download", headers=headers)
    assert dl_mismatch_res.status_code == 409
    assert dl_mismatch_res.headers["X-Integrity-Verified"] == "false"
    assert "Integrity check FAILED" in dl_mismatch_res.json()["detail"]

    # 6. Fail-closed: Missing on-chain hash -> 409 Conflict
    monkeypatch.setattr(blockchain_service, "get_ipfs_record", lambda c: {"sha256_hash": ""})
    dl_missing_res = client.get(f"/records/{record_id}/download", headers=headers)
    assert dl_missing_res.status_code == 409
    assert dl_missing_res.headers["X-Integrity-Verified"] == "false"

    # 7. Fail-closed: Tier-2 Provenance mismatch (H_acq altered on-chain or spoofed) -> 409 Conflict
    monkeypatch.setattr(ipfs_service, "download", lambda c: valid_encrypted)
    monkeypatch.setattr(blockchain_service, "get_ipfs_record", lambda c: {"sha256_hash": expected_hash})
    monkeypatch.setattr(blockchain_service, "get_ipfs_provenance_record", lambda c: {
        "sha256_hash": expected_hash,
        "acquisition_hash": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    })
    dl_prov_mismatch = client.get(f"/records/{record_id}/download", headers=headers)
    assert dl_prov_mismatch.status_code == 409
    assert dl_prov_mismatch.headers["X-Integrity-Verified"] == "false"
    assert "Tier-2 Provenance integrity check FAILED" in dl_prov_mismatch.json()["detail"]
