# DPRMS TECHNICAL WORKING EXAMPLE & CLINICAL WALKTHROUGH
## Concrete End-to-End Execution Trace

### 1. Test Scenario & Actors
- **Patient:** John Doe (Patient ID: 1042, Email: `patient.doe@vit.edu`)
- **Attending Physician:** Dr. Sarah Smith (Doctor ID: 201, License: `DOC-CARD-8819`, Verified: True)
- **Assigned Gateway Device:** `ESP32-VITALS-01` (Model: `ESP32-WROOM-32`, Firmware: `1.2.0`)
- **Pre-Shared Device Secret:** `DPRMS_SECURE_DEVICE_SECRET_KEY_2026`
- **Clinical Objective:** 8-second continuous Lead-II ECG and Pulse Oximetry acquisition, tamper-proof archival to IPFS, and public blockchain anchoring.

---

### 2. Step-by-Step Execution Trace

#### Step 1: Device Registration & Patient Association
The hospital administrator enrolls the IoT gateway:
```bash
POST /clinical/devices/register
{
  "device_id": "ESP32-VITALS-01",
  "device_model": "ESP32-WROOM-32-V1",
  "firmware_version": "1.2.0",
  "secret_key": "DPRMS_SECURE_DEVICE_SECRET_KEY_2026",
  "patient_id": 1042
}
--> HTTP 201 Created: {"device_id": "ESP32-VITALS-01", "patient_id": 1042, "status": "active"}
```

#### Step 2: Live Physiological Acquisition & Edge Signing
1. The patient places their index finger on the MAX30102 optical sensor and connects chest leads to the AD8232 front-end.
2. The MAX30102 registers optical absorption:
   - Red DC Level: 185,200 counts; IR DC Level: 210,400 counts.
   - AC/DC Ratio ($R$): 0.48.
   - Calculated $SpO_2 = 110 - 25(0.48) = 98\%$.
   - Pulse Rate: 74 BPM.
3. The AD8232 hardware timer interrupt samples the 12-bit ADC at 500 Hz (2.0 ms period), buffering samples `[2048, 2065, 2110, 2040, 2048]`.
4. The ESP32 mbedtls engine constructs the canonical message string:
   `ESP32-VITALS-01||101|2026-11-02T08:45:00.000Z|74|98|210400|False`
   and computes the HMAC-SHA256 signature:
   `auth_tag = "d8e3b2...7a4f"`
5. The packet is transmitted via TLS to `/clinical/telemetry/ingest`.

#### Step 3: Ingestion Validation & Patient-Device Isolation
1. FastAPI gateway intercepts the packet.
2. Secret key `DPRMS_SECURE_DEVICE_SECRET_KEY_2026` is retrieved for `ESP32-VITALS-01`.
3. HMAC-SHA256 tag is verified (`hmac.compare_digest` returns True).
4. Timestamp latency = 0.38s <= 10.0s (Freshness check passes).
5. Sequence 101 > 100 (Anti-replay check passes).
6. Packet is stored in `_device_telemetry["ESP32-VITALS-01"]`.
7. When Patient John Doe calls `/clinical/telemetry/latest`, the backend verifies ownership and returns John Doe's readings. If Patient Jane Smith calls the same endpoint, she receives `connected: false` with zeroed readings.

#### Step 4: Bounded Clinical Capture Session
1. Patient John Doe initiates a recording:
   ```bash
   POST /clinical/session/start
   {"device_id": "ESP32-VITALS-01", "capture_mode": "BOTH", "sampling_rate_hz": 500}
   --> HTTP 201 Created: {"session_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6", "status": "ACQUIRING"}
   ```
2. The client records continuous telemetry for exactly 8.0 seconds, accumulating 4,000 ECG samples and 800 PPG samples.
3. The session is completed:
   ```bash
   POST /clinical/session/complete
   {
     "session_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
     "heart_rate": 74,
     "spo2": 98,
     "quality_status": "VALID",
     "acquisition_source": "LIVE_HARDWARE",
     "ecg_samples": [2048, 2065, ...]
   }
   ```
4. The backend computes the acquisition manifest digest:
   $H_{\text{acq}} = \text{SHA256}(\text{CanonicalJSON}) = \text{"b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"}$
   and stores it in `measurement_sessions.raw_manifest_hash`.

#### Step 5: Report Compilation & Client-Side Encryption
1. The frontend compiles a valid PDF 1.4 report embedding the raw waveforms, demographic data, and acquisition digest $H_{\text{acq}}$.
2. Pre-encryption SHA-256 digest:
   `original_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"`
3. AES-256-GCM authenticated encryption is executed using an ephemeral 256-bit key and random 96-bit nonce:
   $C, T = \text{AES-GCM-Encrypt}(K_{\text{sym}}, Nonce_{12}, Plaintext_{PDF})$
4. Ciphertext is saved as non-identifying binary blob `enc_8f12ac7b.bin`.

#### Step 6: IPFS Archival & Sepolia Blockchain Anchoring
1. The encrypted blob is pinned to IPFS via Pinata:
   `CID = "QmZ8kL2vAbc1234567890XyZ"`
2. The backend notary account broadcasts an Ethereum transaction to `PatientRecord.sol`:
   `storeIPFSRecordWithProvenance("REC-1042-88", "QmZ8kL2v...", "e3b0c442...", "b94d27b9...", "encrypted-record", "Observation (Vitals)", 4096)`
3. Sepolia Transaction Receipt:
   - Transaction Hash: `0x4a7f01c8932b1452e87900bfa321...`
   - Block Number: `5,841,209`
   - Gas Used: `87,412 gas`
   - Status: `1 (Success)`

#### Step 7: Authorized Retrieval & Fail-Closed Dual Verification
1. Dr. Sarah Smith logs in.
2. Dr. Smith requests John Doe's record `/records/88/download`.
3. The backend checks active consent:
   `SELECT * FROM consents WHERE patient_id=1042 AND doctor_id=201 AND status='active'` -> Consent Confirmed.
4. Ciphertext is fetched from IPFS (`QmZ8kL2v...`).
5. AES-256-GCM decrypts ciphertext. The 128-bit authentication tag passes.
6. **Tier 1 Verification:** Decrypted file SHA-256 is computed and compared against on-chain hash:
   `SHA256(decrypted) == on_chain_record.sha256Hash == "e3b0c442..."` -> Tier 1 PASSED.
7. **Tier 2 Verification:** Acquisition digest $H_{\text{acq}}$ is extracted from the report manifest and compared against on-chain provenance:
   `manifest.H_acq == on_chain_record.acquisitionHash == "b94d27b9..."` -> Tier 2 PASSED.
8. File is delivered to Dr. Smith with HTTP 200 OK and header `X-Integrity-Verified: true`.
