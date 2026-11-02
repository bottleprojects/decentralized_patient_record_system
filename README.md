# Decentralized Patient Record Management System (DPRMS)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React: 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Solidity: 0.8.20](https://img.shields.io/badge/Solidity-0.8.20-363636.svg)](https://soliditylang.org/)
[![Ethereum: Sepolia](https://img.shields.io/badge/Ethereum-Sepolia_Testnet-627EEA.svg)](https://sepolia.etherscan.io/)
[![Hardware: ESP32](https://img.shields.io/badge/Hardware-ESP32_DevKit_v1-E7352C.svg)](https://www.espressif.com/)

A privacy-preserving, decentralized electronic health record (EHR) and biometric telemetry management system. DPRMS bridges embedded biomedical IoT hardware (ESP32, AD8232 ECG, MAX30102 PPG) with decentralized distributed storage (IPFS) and public smart contract state anchoring (Ethereum Sepolia), while maintaining strict patient access consent, HIPAA/GDPR-compliant authorization, and FHIR R4 interoperability.

---

## System Architecture & Data Flow

The system operates across four coordinated tiers:

1. **Biomedical Edge Layer (ESP32 IoT Gateway)**:
   - **AD8232 ECG Sensor**: Sampled at 500 Hz on ADC1 via a deterministic, $O(1)$ statically-allocated lockless ISR ring buffer (zero heap allocations in interrupt context).
   - **MAX30102 PPG Sensor**: Optical pulse oximetry sampled at 100 Hz over I2C (400 kHz Fast-Mode) measuring SpO2 and pulse rate.
   - **Edge Attestation**: Telemetry packets signed with hardware-accelerated HMAC-SHA256 and transmitted over TLS/HTTPS to the backend ingestion endpoint.

2. **Backend Application Layer (FastAPI & PostgreSQL)**:
   - **Role & Consent Engine**: Enforces strict HIPAA/GDPR clinical data authorization. Patients control physician access; verified doctor credentials are required.
   - **Symmetric Encryption**: Client files are encrypted via AES-256-GCM with unique initialization vectors prior to IPFS dispatch.
   - **Standards Compliance**: Native FHIR R4 endpoints (`/fhir` and `/fhir/v4`) export standard LOINC and UCUM coded clinical resources.
   - **Saga Orchestration**: Atomic multi-stage persistence pipeline (`pending_upload` -> `pending_anchor` -> `confirming` -> `confirmed`) with auto-recovery retry endpoints and thread-safe transaction nonce locking.

3. **Decentralized Storage & Blockchain State Layer**:
   - **Off-Chain IPFS Storage**: Encrypted files pinned via Pinata with non-identifying randomized CIDs (`enc_<uuid>.bin`). Zero PII/PHI stored off-chain.
   - **On-Chain Smart Contract (`PatientRecord.sol`)**: Anchors immutable cryptographic proofs (SHA-256 document hash, IPFS CID, and hardware provenance hash) on Ethereum Sepolia.

4. **Web Client Application Layer (React + Vite)**:
   - Role-based portals for Patients, Doctors, and Administrators with direct Etherscan verification, consent management, and live telemetry streaming.

---

## Core Capabilities

- **Hybrid Decentralized Storage**: Encrypted biomedical documents and physiological telemetry are stored off-chain via Pinata IPFS using randomized content identifiers (`enc_<uuid>.bin`). Public blockchain storage holds only cryptographic proofs (SHA-256 digests, IPFS CIDs, and hardware provenance hashes), guaranteeing zero Protected Health Information (PHI) or Personally Identifiable Information (PII) on-chain.
- **Hardware-Rooted Provenance ($H_{acq}$)**: Biomedical data captured by ESP32 sensors (AD8232 ECG and MAX30102 PPG) is signed at the edge using hardware-accelerated HMAC-SHA256 tags. Measurement sessions produce canonical JSON acquisition manifests whose SHA-256 digests ($H_{acq}$) are anchored alongside clinical records on-chain.
- **AES-256-GCM Authenticated Encryption**: Document payloads are encrypted symmetrically using AES-256-GCM with randomized 96-bit initialization vectors and 128-bit authentication tags prior to IPFS distribution.
- **Dynamic Patient Consent & Break-Glass Protocol**: Granular patient-controlled consent and revocation for physicians. Includes a secure break-glass emergency override protocol requiring verified doctor credentials, substantive clinical justification (minimum 15 characters), a strict 24-hour expiration window, and immutable audit logging.
- **FHIR R4 Interoperability**: Native FHIR endpoints (`/fhir` and `/fhir/v4`) export standards-conformant `Patient` and `Observation` resources mapped to official LOINC codes (`8867-4` Heart Rate, `2708-6` SpO2, `8889-8` ECG Rhythm) and UCUM unit specifications, strictly gated by active patient consent.
- **Saga Orchestration & Nonce Management**: Multi-phase resilient upload workflow (`pending_upload` &rarr; `pending_anchor` &rarr; `confirming` &rarr; `confirmed`) with auto-recovery retry endpoints (`POST /records/{id}/retry-anchor`) and thread-safe nonce locking to prevent transaction collisions.
- **High-Performance Interrupt Handling**: ESP32 C++ firmware employs an $O(1)$ statically-allocated lockless ring buffer inside the 500 Hz hardware timer ISR, avoiding dynamic heap allocation (`malloc`/`push_back`) to guarantee deterministic sampling without interrupt watchdog panics.

---

## Repository Structure

```
decentralized_patient_record_system/
├── backend/                   # FastAPI Backend Application
│   ├── app/
│   │   ├── contracts/         # Compiled Solidity Contract ABIs
│   │   ├── routers/           # API Routers (auth, records, clinical, consent, fhir, metrics)
│   │   ├── services/          # Core Services (crypto, blockchain, ipfs, auth, rate_limiter)
│   │   ├── database.py        # SQLAlchemy Database Engine & Sessions
│   │   ├── main.py            # FastAPI Entry Point, Migrations & CORS
│   │   └── models.py          # SQLAlchemy ORM Data Models
│   ├── tests/                 # Comprehensive Backend Unit & Integration Tests
│   └── requirements.txt       # Python Dependencies
├── blockchain/                # Smart Contract Workspace (Hardhat)
│   ├── contracts/             # Solidity Source Code (PatientRecord.sol)
│   ├── scripts/               # Contract Deployment & Verification Scripts
│   ├── test/                  # Contract Security & Provenance Hardhat Tests
│   └── hardhat.config.js      # Hardhat Network & Compiler Configuration
├── frontend/                  # React + Vite + TypeScript Frontend
│   ├── src/
│   │   ├── components/        # UI Panels (Metrics, Telemetry, Records, Consent)
│   │   ├── pages/             # Patient, Doctor, Admin Dashboards & Auth Views
│   │   └── lib/               # API Clients & Web3 Utilities
│   └── package.json           # Frontend Dependencies & Build Scripts
├── firmware/                  # ESP32 C++ Firmware (PlatformIO)
│   ├── include/               # Central Pin & Network Configurations (config.h)
│   ├── src/                   # Sensor Drivers (AD8232, MAX30102, TLS Network Manager)
│   └── platformio.ini         # PlatformIO Build & Upload Environment
├── hardware/                  # Physical Schematics & Reference Firmware
│   └── esp32_firmware/        # Arduino IDE Reference Sketch (.ino)
├── DEPLOY.md                  # Click-by-Click Production Cloud Deployment Guide
└── README.md                  # Project Overview & Quickstart Guide
```

---

## Getting Started

### 1. Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher & npm
- **Hardware (Optional)**: ESP32 DevKit v1 with AD8232 and MAX30102 breakout modules

---

### 2. Backend Setup

1. Navigate to the backend directory and set up a virtual environment:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure environment variables in `backend/.env`:
   ```env
   ENVIRONMENT=development
   DATABASE_URL=sqlite:///./local_records.db
   JWT_SECRET_KEY=your_secure_random_jwt_secret_key_min_32_chars
   ENCRYPTION_KEY=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY= # 32-byte Base64 key
   SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
   PRIVATE_KEY=your_ethereum_wallet_private_key_hex
   CONTRACT_ADDRESS=your_deployed_patient_record_contract_address
   PINATA_API_KEY=your_pinata_api_key
   PINATA_API_SECRET=your_pinata_api_secret
   PINATA_GATEWAY=https://gateway.pinata.cloud
   FRONTEND_URL=http://localhost:5173
   ```

3. Launch the FastAPI server:
   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Interactive Swagger API documentation will be available at `http://localhost:8000/docs`.

---

### 3. Smart Contract Deployment & Testing

1. Navigate to the blockchain directory:
   ```bash
   cd blockchain
   npm install
   ```

2. Run automated security and provenance test suite:
   ```bash
   npx hardhat test
   ```

3. Deploy smart contract to Ethereum Sepolia Testnet:
   ```bash
   npx hardhat run scripts/deploy.js --network sepolia
   ```
   *Copy the output contract address into your `backend/.env` file.*

---

### 4. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```

2. Configure `frontend/.env`:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

3. Run development server:
   ```bash
   npm run dev
   ```

4. Build for production:
   ```bash
   npm run build
   ```

---

### 5. Hardware & ESP32 Firmware Setup

1. Connect the AD8232 and MAX30102 sensors to the ESP32:
   - **MAX30102 (I2C)**: SDA &rarr; GPIO 21, SCL &rarr; GPIO 22, VIN &rarr; 3.3V, GND &rarr; GND.
   - **AD8232 (ECG)**: OUTPUT &rarr; GPIO 36 (ADC1), LO+ &rarr; GPIO 34, LO- &rarr; GPIO 35, SDN &rarr; GPIO 32.
2. Open `firmware/` in PlatformIO or `hardware/esp32_firmware/esp32_firmware.ino` in Arduino IDE.
3. Update Wi-Fi SSID, password, and backend gateway URL in `firmware/include/config.h`.
4. Flash the microcontroller:
   ```bash
   pio run --target upload
   pio device monitor -b 115200
   ```

---

## Testing & Quality Assurance

### Run Backend Integration Tests
```bash
PYTHONPATH=. backend/venv/bin/pytest backend/tests/ -v
```
*Executes all 22 automated integration tests covering patient telemetry isolation, doctor verification gating, record fail-closed verification, emergency break-glass bounds, and FHIR consent compliance.*

### Run Smart Contract Tests
```bash
cd blockchain
npx hardhat test
```
*Validates writer access control, non-overwrite integrity checks, emergency pause functionality, hardware provenance retrieval, and consent audit event emission.*

---

## Security & Compliance Architecture

- **Zero Plaintext Storage**: Health records are encrypted with AES-256-GCM prior to transmission to IPFS. Keys are managed exclusively on authenticated client devices.
- **Role-Based Access Control (RBAC)**: Enforced via JWT bearer authentication with separate permission scopes for Patients, Doctors, and Administrators.
- **Fail-Closed Verification**: Decrypted documents are verified against the on-chain SHA-256 digest before being rendered; corrupted or tampered records fail immediately with `422 Unprocessable Entity` or `409 Conflict`.
- **Sanitized Diagnostics**: Exception handlers sanitize internal error messages to prevent database schema or traceback exposure in production.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
