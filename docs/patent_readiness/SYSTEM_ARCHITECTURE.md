# DPRMS SYSTEM ARCHITECTURE SPECIFICATION
## Decentralized Patient Record Management System

### 1. Architectural Overview
The Decentralized Patient Record Management System (DPRMS) is architected as a zero-trust, multi-tiered biomedical data custody pipeline. It bridges physical Internet of Medical Things (IoMT) hardware sensors with decentralized content-addressed storage (IPFS) and public blockchain state anchors (Ethereum Sepolia), while strictly isolating patient telemetry and enforcing clinical consent.

```
+-----------------------------------------------------------------------------------+
|                            PHYSICAL SENSOR LAYER                                  |
|   MAX30102 Optical PPG (I2C: 21/22)     |      AD8232 Lead-II ECG (ADC1_0: 36)   |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        EDGE HARDWARE AUTHENTICATOR (ESP32)                        |
|   500 Hz Hardware Sampling Timer        |      eFuse Symmetric Secret Key         |
|   Monotonic Sequence Counter            |      mbedtls HMAC-SHA256 Signer         |
+-----------------------------------------+-----------------------------------------+
                                          | TLS Ingestion (/clinical/telemetry/ingest)
                                          v
+-----------------------------------------------------------------------------------+
|                        FASTAPI INGESTION & GATEWAY LAYER                          |
|   Sliding-Window Freshness (|dt| <= 10s)|      Anti-Replay Sequence Monotonicity  |
|   Device Registry & Key Verification    |      Patient-Device Isolated Buffers    |
+-----------------------------------------+-----------------------------------------+
                                          |
             +----------------------------+----------------------------+
             |                                                         |
             v                                                         v
+-----------------------------+                           +-------------------------+
|   MEASUREMENT SESSIONS      |                           |    DECENTRALIZED CUSTODY|
|   Bounded 8s Capture (4000s)|                           |    Client AES-256-GCM   |
|   Quality Gate: SpO2/HR/ECG |                           |    IPFS Pinning (CID)   |
|   Manifest Digest: H_acq    |                           |    Sepolia Anchor (87k) |
+-----------------------------+                           +-------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     FAIL-CLOSED DUAL-VERIFICATION RETRIEVAL                       |
|   Tier 1 Content Verification: SHA256(Decrypted) == On-Chain SHA-256              |
|   Tier 2 Provenance Verification: Manifest Digest == On-Chain H_acq               |
|   Access Control Barrier: Active Patient Consent & Verified Doctor Status         |
+-----------------------------------------------------------------------------------+
```

---

### 2. Subsystem Classifications

| Subsystem Component | Implementation Status | Verification Evidence |
|:---|:---|:---|
| MAX30102 Optical PPG Driver | IMPLEMENTED | `firmware/src/max30102_driver.cpp` |
| AD8232 Lead-II ECG Driver | IMPLEMENTED | `firmware/src/ad8232_driver.cpp` |
| Edge Hardware HMAC-SHA256 Signer | IMPLEMENTED | `firmware/src/device_authentication.cpp` |
| Fast-Mode 500 Hz Hardware Timer | IMPLEMENTED | `firmware/src/main.cpp` |
| Anti-Replay & Freshness Gateway | IMPLEMENTED AND TESTED | `backend/tests/test_device_auth.py` |
| Patient-Device Isolated Buffers | IMPLEMENTED AND TESTED | `backend/tests/test_patient_isolation.py` |
| Persistent Session Engine & H_acq | IMPLEMENTED AND TESTED | `backend/tests/test_clinical_sessions.py` |
| AES-256-GCM Envelope Encryption | IMPLEMENTED AND TESTED | `backend/tests/test_crypto.py` |
| Non-Identifying IPFS Pinning | IMPLEMENTED | `backend/app/routers/records.py` |
| Sepolia Smart Contract Anchor | IMPLEMENTED AND TESTED | `blockchain/test/PatientRecord.test.js` |
| Fail-Closed Dual-Verification | IMPLEMENTED AND TESTED | `backend/tests/test_records_fail_closed.py` |
| Bedside Monitor Telemetry Panel | IMPLEMENTED | `frontend/src/components/MetricsAnalyticsPanel.tsx` |
| Zero-Dependency PDF Generator | IMPLEMENTED | `frontend/src/lib/vitalsPdfGenerator.ts` |
| Layer-2 zk-Rollup Aggregator | PROPOSED | Architecture roadmap |
| Threshold MPC Key Recovery | PROPOSED | Architecture roadmap |

---

### 3. Edge-to-Gateway Communication Protocol
Every telemetry packet follows a strictly defined canonical serialization schema:

```json
{
  "device_id": "ESP32-VITALS-01",
  "session_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "sequence_number": 1420,
  "timestamp": "2026-11-02T08:30:00.000Z",
  "finger_detected": true,
  "ir_value": 72400,
  "leads_off": false,
  "heart_rate": 74,
  "spo2": 98,
  "ecg_samples": [2048, 2060, 2085, 2040, 2048],
  "auth_tag": "3a8f...91c2",
  "acquisition_source": "LIVE_HARDWARE"
}
```

**Verification Invariants:**
1. $\text{DeviceRegistered}(device\_id) == \text{True}$
2. $|t_{\text{server}} - t_{\text{device}}| \le 10.0\text{ seconds}$
3. $sequence\_number > \text{last}\_sequence\_number[device\_id]$
4. $auth\_tag == \text{HMAC-SHA256}(K_{\text{device}}, CanonicalMsg)$

---

### 4. Smart Contract Architecture (PatientRecord.sol)
The smart contract operates on the Ethereum Paris/Cancun EVM execution environment and inherits OpenZeppelin `Ownable` and `Pausable`.

**Storage State:**
- `mapping(address => bool) public authorizedWriters`: Whitelist of authenticated backend notary accounts.
- `mapping(string => IPFSRecord) public ipfsRecords`: Primary registry of anchored records.

```solidity
struct IPFSRecord {
    string cid;             // IPFS Content Identifier
    string sha256Hash;      // Pre-encryption document digest
    string acquisitionHash; // Hardware provenance manifest digest H_acq
    string fileName;        // Non-identifying label ("encrypted-record")
    string fileType;        // MIME category tag
    uint256 fileSize;       // File size in bytes
    uint256 timestamp;      // On-chain block timestamp
    uint256 version;        // Record schema version
}
```

**Gas Profile:**
- Deployment Gas: ~840,000 gas.
- `storeIPFSRecordWithProvenance`: 87,412 gas.
- Read Operations (`getIPFSProvenanceRecord`): 0 gas (view function).
