# INVENTION DISCLOSURE FORM
## INSTITUTIONAL PATENT EVALUATION (K&K REVISED)
**Project Title:** Decentralized Patient Record Management System (DPRMS)

---

### 1. Title of the Invention
**Cryptographically Authenticated Physiological Sensor Provenance, Content-Addressed Archival, and Dual-Verification Blockchain Anchoring System**

---

### 2. What is the Invention?
The present invention provides an end-to-end, zero-trust biomedical informatics system that establishes an immutable chain of custody from physical physiological sensors to decentralized cloud archival and public blockchain anchoring.

**Problem Statement:**
Current Electronic Health Record (EHR) frameworks and first-generation blockchain architectures (e.g., MedRec, Ancile) operate exclusively at the application layer. They accept clinical data files uploaded via web portals or mobile applications without cryptographically authenticating the physical sensor hardware. This creates a critical "origin vulnerability" (garbage-in, immutable-garbage-out), where spoofed telemetry, synthetic ECG waveforms, or replayed vital signs are permanently sealed on-chain as genuine. Furthermore, directly storing high-throughput raw physiological streams on public blockchains is economically and technically impossible due to block gas limits (exceeding 3.2 billion gas per megabyte), while centralized cloud repositories (AWS S3, Supabase) present single points of failure (SPOF) and mutable audit logs.

**Solution Statement:**
The invention resolves this problem through a multi-tier provenance architecture:
1. Physical biomedical sensors (MAX30102 PPG, AD8232 ECG) are coupled to an edge hardware cryptographic authenticator (ESP32) that computes HMAC-SHA256 signatures over raw telemetry packets containing unique device IDs, measurement timestamps, dynamic session IDs, and monotonic sequence counters.
2. An ingestion gateway validates device registration, sliding-window freshness (|t_server - t_device| <= 10.0s), and anti-replay sequence monotonicity before caching in isolated per-patient buffers.
3. A persistent measurement session engine aggregates validated time-series data and cryptographically binds the raw telemetry to an acquisition manifest digest H_acq.
4. An off-chain decentralized storage pipeline encrypts the canonical diagnostic report using client-side AES-256-GCM authenticated encryption and pins the non-identifying ciphertext to IPFS, obtaining a Content Identifier (CID).
5. A lightweight smart contract on Ethereum Sepolia commits an immutable reference tuple consuming only ~87,412 gas (a 99.998% gas reduction).
6. A fail-closed dual-verification retrieval engine independently verifies both off-chain ciphertext integrity (Tier 1) and hardware acquisition provenance (Tier 2) before clinical delivery.

**General Purpose:**
To provide hospitals, physicians, and patients with mathematically indisputable proof that remote physiological monitoring data originated from an authentic, physically calibrated sensor device and has not been altered or replayed.

---

### 3. Search Terms
**IPC Classification Codes:**
- G16H 10/60: ICT specially adapted for the handling or processing of medical or healthcare data (Patient-specific data, e.g. Electronic Health Records).
- H04L 9/32: Arrangements for secret or secure communications including cryptographic authentication protocols and digital signatures.
- H04L 67/1097: Network protocols and architectures for peer-to-peer (P2P) decentralized storage networks.
- A61B 5/00: Measuring for diagnostic purposes; Biomedical sensor acquisition.
- H04L 9/08: Cryptographic key distribution and management.

**Keywords & Common Industry Phrases:**
Physiological sensor provenance; edge cryptographic attestation; hardware-rooted HMAC-SHA256; anti-replay sliding-window freshness; photoplethysmography (PPG); electrocardiography (ECG); decentralized electronic health records (EHR); InterPlanetary File System (IPFS); content identifier (CID); blockchain anchoring; Ethereum Sepolia smart contract; dual-verification engine; AES-256-GCM authenticated encryption; Merkle acquisition digest; zero on-chain protected health information (PHI); fail-closed verification; tamper-evident audit trail; patient-device isolation; medical IoT security.

---

### 4. Background of the Invention
**Present Technologies:**
1. Centralized Hospital EHRs (Epic Systems, Cerner/Oracle Health): Store patient demographics, diagnostic summaries, and medical imaging in centralized relational databases and cloud object stores (AWS S3, Google Cloud, Microsoft Azure).
2. Proprietary Consumer Wearables (Apple HealthKit, Fitbit/Google Fit, Withings): Collect sensor telemetry and transmit proprietary packets to centralized vendor cloud silos.
3. First-Generation Blockchain Healthcare Systems (MedRec, Ancile, MeDShare): Use Ethereum smart contracts as access-control gatekeepers while storing encrypted documents on external hospital databases or cloud servers.

**Limitations of the Same:**
1. Single Point of Failure (SPOF) and Ransomware: Centralized hospital databases represent high-value targets for cyberattacks. A database breach or ransomware lockout paralyses hospital operations and exposes millions of unencrypted records.
2. Complete Absence of Hardware Sensor Provenance: Existing systems assume that any data received from an authorized user's portal or app is authentic. If a terminal is compromised, an adversary can submit falsified physiological readings (e.g. normal 74 BPM / 98% SpO2 or synthetic ECG waveforms), and the blockchain will faithfully record the fraudulent file hash.
3. Vulnerability to Packet Replay & Injection: Standard telemetry streams lack hardware-enforced sequence counters and sliding-window timestamp validation, allowing attackers to replay stale historical packets.
4. Prohibitive Blockchain Gas Economics: Storing raw physiological time-series data on public blockchains costs > 3.2 billion gas per megabyte, exceeding the 30M Ethereum block limit by > 20x.
5. Ineffective On-Chain Access Control Claims: Prior art claims smart contracts enforce data access permissions. In reality, smart contracts cannot restrict off-chain decryption once ciphertext is distributed, and storing patient access lists on-chain violates privacy laws (GDPR Art. 9) by leaking clinical interaction patterns.
6. Single-Layer Verification Defect: Existing decentralized systems only verify if the retrieved file matches the on-chain file hash. They cannot detect if the file's contents were fabricated prior to upload.

---

### 5. Prior Art
1. **MedRec (Ekblaw et al., MIT Media Lab, 2016):**
   - *Architecture:* Employs Ethereum smart contracts to manage patient permission lists and map patient identities to hospital database endpoint URLs.
   - *Deficiencies:* Relies entirely on traditional hospital SQL databases for record storage; has zero IoT sensor authentication; provides no edge cryptographic signing; cannot prevent sensor telemetry replay; provides no dual-verification mechanism.
2. **Ancile (Xia et al., 2017):**
   - *Architecture:* Utilizes smart contracts for privacy-preserving access control, managing encryption keys and off-chain file references.
   - *Deficiencies:* Operates solely at the document layer; does not bind physical biomedical sensors to records; smart-contract permission evaluations incur massive gas costs; access control is bypassed if off-chain ciphertext is intercepted.
3. **MeDShare (Xia et al., IEEE Access 2017):**
   - *Architecture:* A trustless medical data-sharing architecture among cloud service providers using smart contracts.
   - *Deficiencies:* Exclusively targets inter-cloud data exchange; ignores real-time biomedical sensor acquisition, hardware attestation, and streaming vital sign telemetry.
4. **US Patent Publication US20200160950A1 ("Blockchain-Based Health Record Management"):**
   - *Architecture:* Discloses hashing medical files and recording hashes on a distributed ledger.
   - *Deficiencies:* Hashes static documents post-creation; no cryptographic binding between physical sensors, acquisition sessions, and telemetry packets; lacks a two-tier provenance verification engine.
5. **Traditional Cloud Stores (AWS S3, Supabase Storage):**
   - *Deficiencies:* Mutable file paths; centralized administrative credentials can alter or delete historical files without audit detection; single points of failure.

---

### 6. Has the Work Filled a Major Gap in Prior Art?
**YES.** The invention fills four critical gaps in biomedical informatics and decentralized systems:
1. **The "Physical-to-Digital Provenance Gap":** Establishes a hardware-rooted cryptographic bridge that binds physical sensor silicon directly to blockchain transactions, completely eliminating the "garbage-in, immutable-garbage-out" vulnerability.
2. **The "Sensor Telemetry Replay & Injection Gap":** Implements a hardware-session-bound, sliding-window freshness verification mechanism (|t_server - t_device| <= 10.0s) and monotonic sequence tracking that prevents packet replay attacks.
3. **The "On-Chain Scalability vs. Tamper-Proof Custody Gap":** Solves the multi-billion gas scalability barrier by combining client-side AES-256-GCM authenticated encryption and IPFS content-addressing with ultra-lightweight Ethereum Sepolia anchoring (~87,412 gas), achieving a 99.998% gas reduction while maintaining absolute cryptographic tamper-evidence.
4. **The "Single-Hash Verification Defect":** Introduces a dual-verification retrieval engine that independently validates both decentralized storage integrity (Tier 1) and hardware acquisition provenance (Tier 2), alerting clinicians if file integrity is intact but hardware origin is unverified.

---

### 7. Components of the Invention
1. **Edge Biomedical Sensing & Hardware Authenticator Subsystem:**
   - *Optical PPG Sensor (MAX30102):* Dual-wavelength 660nm Red / 880nm IR LED optical sensor measuring arterial pulse waves, SpO2 (70-100%), and pulse rate (35-220 BPM) over I2C at 100 Hz.
   - *Biopotential ECG Front-End (AD8232):* Single-lead analog front-end with right-leg drive amplifier and leads-off detection circuitry (LO+, LO-) connected to ADC1 Channel 0 (GPIO 36).
   - *Edge Microcontroller (ESP32-WROOM-32):* Dual-core Xtensa 32-bit LX6 microprocessor running FreeRTOS with a 500 Hz hardware timer interrupt for ADC sampling.
   - *Hardware Authenticator Module:* Computes HMAC-SHA256 signatures over each telemetry packet using a pre-shared 256-bit symmetric secret stored in secure flash.
2. **Ingestion & Validation Gateway Subsystem:**
   - *FastAPI Asynchronous Microservice:* Python 3.11+ high-throughput gateway.
   - *Device Registry & Authenticator:* Validates device status, pre-shared key, and HMAC signature.
   - *Anti-Replay & Freshness Engine:* Enforces a 10.0-second sliding-window timestamp check and monotonic sequence counter validation.
   - *Patient-Device Isolation Buffer:* Thread-safe, per-device in-memory store preventing cross-patient data exposure.
3. **Persistent Session & Provenance Binding Subsystem:**
   - *Measurement Session Engine:* Manages session lifecycle (IDLE -> CALIBRATING -> ACQUIRING -> VALIDATING -> CAPTURE_COMPLETE).
   - *Canonical Manifest Generator:* Generates JSON manifest of acquisition parameters and raw sample digests.
   - *Acquisition Digest (H_acq):* Computes SHA-256 over the canonical manifest to seal hardware provenance.
4. **Decentralized Storage & Encryption Subsystem:**
   - *Authenticated Encryption Engine:* AES-256-GCM cipher generating ciphertext with unique 96-bit random IVs and 128-bit authentication tags.
   - *Non-Identifying Content Storage:* InterPlanetary File System (IPFS) cluster pinning encrypted blobs under sanitized filenames (enc_UUID.bin) to eliminate metadata leakage.
5. **Blockchain Reference & Dual-Verification Subsystem:**
   - *EVM Smart Contract (PatientRecord.sol):* Deployed on Ethereum Sepolia testnet with Ownable and Pausable controls, storing compact tuples (recordId, cid, sha256Hash, acquisitionHash, timestamp).
   - *Dual-Verification Retrieval Engine:* Validates AES-GCM tag, checks recomputed file hash against on-chain hash, and verifies acquisition manifest against on-chain acquisitionHash.

---

### 8. How does the Invention Work? (The 9-Step Sequence)
- **Step 1:** Actual physiological measurements are obtained by the registered sensor device (MAX30102 PPG at 100 Hz, AD8232 Lead-II ECG at 500 Hz).
- **Step 2:** Each measurement packet is associated with a unique device identity (device_id), high-resolution timestamp, session identifier, and monotonic sequence counter.
- **Step 3:** The edge microcontroller cryptographically authenticates the packet via HMAC-SHA256 using a pre-shared secret key burned into secure hardware memory.
- **Step 4:** The backend gateway validates the device identity, packet freshness (|t_server - t_device| <= 10.0s), and sequence monotonicity before accepting the payload into an isolated patient buffer.
- **Step 5:** The capture module creates a clinical diagnostic report containing the original measurement data and acquisition metadata over a bounded clinical interval (8 seconds).
- **Step 6:** The report is cryptographically bound to its acquisition metadata via a canonical measurement manifest digest H_acq = SHA256(canonical_manifest).
- **Step 7:** The completed report is encrypted using AES-256-GCM with a random 96-bit IV and pinned to IPFS under an anonymous filename (enc_UUID.bin), returning Content Identifier CID.
- **Step 8:** The blockchain records an immutable cryptographic reference tuple (recordId, CID, original_sha256_hash, H_acq, timestamp) in PatientRecord.sol on Sepolia (~87,412 gas).
- **Step 9:** During retrieval, the fail-closed dual-verification engine independently verifies both ciphertext integrity (Tier 1: AES tag + on-chain SHA-256 match) and hardware acquisition provenance (Tier 2: manifest H_acq match + device signature).

---

### 9. Novelty / Inventive Step
The invention provides four foundational differentiators over existing literature:
1. **Hardware-Bound Edge Provenance Bridge:** Physical sensor registers are cryptographically bound to blockchain records via edge HMAC-SHA256 signatures and monotonic counters, eliminating the origin vulnerability.
2. **Deterministic Merkle Binding of Telemetry to Clinical Reports:** The acquisition manifest digest H_acq mathematically binds raw time-series samples directly into the diagnostic PDF and the smart contract state.
3. **Fail-Closed Dual-Verification Retrieval:** Evaluates both storage-layer content integrity and physical hardware provenance, returning 409 Conflict if on-chain records are missing or mismatched, and 422 if ciphertext is altered.
4. **99.998% Gas-Optimized Anchoring with Decoupled Access Control:** Anchors compact 32-byte cryptographic digests on-chain while enforcing access permissions in an audited backend layer, satisfying HIPAA and GDPR Article 17 ("Right to be Forgotten").

---

### 10. Advantages & Improvements Over Existing Methods
- **99.998% Gas Cost Reduction:** Reduces transaction cost from > 672 million gas ($40,000+) to 87,412 gas (~$3.50 on Ethereum L1, <$0.02 on L2 rollups).
- **Zero Cloud Lock-In & Elimination of SPOF:** Content-addressed IPFS archival eliminates recurring database egress tariffs and centralized cloud vulnerability.
- **Tamper-Proof Origin Guarantee:** Prevents synthetic waveforms or spoofed pulse oximetry readings from being recorded as genuine clinical data.
- **Sub-Second Telemetry Latency:** Achieves 381.98 ms warm retrieval for real-time clinical bedside monitoring.

---

### 11. Alternative Embodiments
1. Multi-parameter ICU telemetry bridges aggregating 12-lead ECG, arterial pressure, and capnography.
2. Wearable continuous medical patches with hardware ATECC608A secure elements for ECDSA signatures.
3. Layer-2 Zero-Knowledge Rollups (zk-SNARKs on Arbitrum/Optimism/Starknet) aggregating 10,000 records for < 1,000 gas.
4. Decentralized Identity (W3C DID) and Verifiable Credentials for medical devices and clinicians.
5. Threshold Multi-Party Computation (MPC) for decentralized emergency break-glass key recovery.

---

### 12. Images and Diagrams
Detailed SVG schematics are located in `docs/patent_readiness/drawings/`:
- **FIG. 1:** Overall System Architecture (Set A and Set B)
- **FIG. 2:** Sensor Hardware Interfaces & Pin Connections (Set A and Set B)
- **FIG. 3:** Authenticated Telemetry & Anti-Replay Protocol (Set A and Set B)
- **FIG. 4:** Persistent Sensor Capture Workflow (Set A and Set B)
- **FIG. 5:** Cryptographic Processing, IPFS & Blockchain Anchoring (Set A and Set B)
- **FIG. 6:** Fail-Closed Record Retrieval & Dual-Verification Engine (Set A and Set B)
- **FIG. 7:** Patient Consent & Doctor Authorization Architecture (Set A and Set B)
- **FIG. 8:** End-to-End Measurement Provenance Verification (Set A and Set B)

---

### 13. Brief Description of Drawings
- *FIG. 1:* Multi-tier system topology illustrating physical sensors (102), ESP32 gateway (110), FastAPI gateway (120), IPFS cluster (140), EVM contract (150), and clinical dashboard (160).
- *FIG. 2:* Hardware pinout diagram showing MAX30102 on I2C GPIO 21/22 and AD8232 on ADC1 GPIO 36, LO+ GPIO 34, LO- GPIO 35, SDN GPIO 32.
- *FIG. 3:* Protocol sequence diagram illustrating edge HMAC signing (304), sliding-window freshness (310), and patient isolation (312).
- *FIG. 4:* State machine diagram of capture phases: IDLE (402), CALIBRATING (404), ACQUIRING (406), VALIDATING (408), CAPTURE_COMPLETE (410), and FAILED (412).
- *FIG. 5:* Block diagram of report generation (502), AES-256-GCM cipher (504), IPFS archival (506), and Sepolia commit (508).
- *FIG. 6:* Flowchart of fail-closed retrieval and dual-verification logic.
- *FIG. 7:* Architecture diagram of consent workflow and on-chain event logs.
- *FIG. 8:* Provenance verification bridge connecting hardware sensor (802), manifest (804), blockchain anchor (806), and dual-verification engine (808).

---

### 14. Complete Technical Description & Working Examples
*(See `WORKING_EXAMPLE.md` for full step-by-step mathematical execution and clinical walkthrough).*

---

### 15. Experiments, Benchmarks & Mathematical Formulations
- **Total Benchmark Operations:** 785 operations across throttled (Fast 4G) and unthrottled gigabit networks.
- **Upload Latency:** 100 KB = 3,549.95 ms (IPFS); 1 MB = 5,931.68 ms (IPFS); 5 MB = 18,010.74 ms (IPFS vs. 71,367.04 ms centralized).
- **Warm Retrieval Latency:** 381.98 ms (bedside monitor cache).
- **Gas Economics:** 87,412 gas per anchored record vs. 672,158,216 gas for direct on-chain storage (99.998% savings).
- **Formulas:**
  - $Tag = 	ext{HMAC-SHA256}(K_{\text{device}}, DeviceID \parallel SessionID \parallel Seq \parallel Timestamp \parallel Vitals)$
  - $C, T = \text{AES-GCM-Encrypt}(K_{\text{sym}}, IV_{96}, Plaintext, AAD)$
  - $H_{\text{acq}} = \text{SHA256}(\text{CanonicalJSON}(Manifest))$

---

### 16. Software Code Details
Core implementation artifacts:
1. `blockchain/contracts/PatientRecord.sol` (Solidity 0.8.20 with OpenZeppelin Ownable & Pausable)
2. `backend/app/routers/clinical.py` (FastAPI hardware validator, isolated telemetry store, and session engine)
3. `firmware/src/main.cpp` (ESP32 FreeRTOS 500 Hz timer and mbedtls HMAC signer)

---

### 17. Training Data / ML
**Not Applicable - Deterministic Cryptographic Pipeline.**
The invention relies exclusively on mathematically provable, deterministic algorithms (HMAC-SHA256, AES-256-GCM, SHA-256 Merkle trees). It does not use stochastic machine learning or generative AI for its core integrity claims, guaranteeing 100% reproducible, hallucination-free medical validation.

---

### 18. Public Disclosure
**No public disclosure has been made.** Internal academic evaluation and laboratory benchmarking at VIT Chennai SCOPE. The subject matter is fully patentable under novelty grace periods.

---

### 19. Stage of Development
**[ ✔ ] Completed and Results Validated (TRL 5 / TRL 6).** Full working prototype integrated across physical sensors, edge firmware, FastAPI backend, IPFS nodes, and Ethereum Sepolia smart contract.

---

### 20. Proposed Claims
*(See `PROPOSED_CLAIMS.md` for 1 independent system claim, 1 independent method claim, and 10 dependent claims).*

---

### 21. Novelty Search
Conducted across Google Patents, USPTO, EPO Espacenet, IEEE Xplore, and PubMed. Matrix demonstrates non-anticipation by MedRec (2016), Ancile (2017), or US20200160950A1. *(See `PRIOR_ART_COMPARISON.md`).*

---

### 22. Non-Obviousness Analysis
A PHOSITA would not combine edge microcontroller cryptographic signing with decentralized content-addressed storage and dual-layer verification due to prevailing technical prejudices regarding microcontroller processing limits, storage cost trade-offs, and single-hash verification conventions.

---

### 23. Parameter Ranges
- Sensor Sampling Frequency: 100 Hz to 1,000 Hz (500 Hz preferred for ECG).
- ADC Resolution: 10-bit to 24-bit (12-bit preferred).
- Freshness Threshold: 1.0s to 30.0s (10.0s preferred).
- AES Key Length: 256 bits; IV: 96 bits; Tag: 128 bits.
- IPFS Payload: 10 KB to 50 MB (100 KB to 5 MB sweet spot).
- Smart Contract Gas: 75,000 to 110,000 gas (87,412 gas benchmarked).

---

### 24. Commercialization Data
**Target Companies:**
1. Medtronic plc: 710 Medtronic Parkway, Minneapolis, MN 55432, USA.
2. Koninklijke Philips N.V.: High Tech Campus 52, 5656 AG Eindhoven, The Netherlands.
3. GE HealthCare Technologies Inc.: 500 W Monroe St, Chicago, IL 60661, USA.
4. Epic Systems Corporation: 1979 Milky Way, Verona, WI 53593, USA.
5. Oracle Health (Cerner Corporation): 2800 Rockcreek Pkwy, North Kansas City, MO 64117, USA.

---

### 25. Market Potential & Industry Trends
- Global EHR Market: USD 34.93 Billion (2024) -> USD 52.41 Billion (2030) at 7.0% CAGR.
- IoMT Market: USD 89.6 Billion (2023) -> USD 289.2 Billion (2028) at 16.5% CAGR.
- Healthcare Blockchain: USD 2.31 Billion (2023) -> USD 16.30 Billion (2030) at 32.2% CAGR.

---

### 26. Names of Inventors
1. **Abhinav S P** (Reg No: 25BCE5381), SCOPE, VIT Chennai Campus, Tamil Nadu, India.
2. **G Prathish Rajan** (Reg No: 25BCE5367), SCOPE, VIT Chennai Campus, Tamil Nadu, India.

---

### 27. User Information
- **Potential Users:** Clinicians, Cardiologists, Patients, Hospitals, Medical Device OEMs, CROs.
- **Age Groups:** All demographics (Pediatric, Adult, Geriatric).
- **Benefits:** Non-repudiable vital signs, prevention of duplicate tests, remote cardiac safety.
- **Cost Advantage:** 99.998% reduction in blockchain transaction costs, elimination of cloud lock-in.

---

### 28. Technology Readiness Level (TRL)
**[ ✔ ] TRL 5:** Technology validated in relevant environment (simulated hospital network and Ethereum Sepolia testnet).

---

### 29. Additional Notes & Regulatory Remarks
- **HIPAA Security Rule (45 CFR § 164.312):** Zero on-chain PHI; AES-256-GCM encryption at rest; TLS 1.3 in transit.
- **EU GDPR Compliance:** Article 9 consent barriers; Article 17 ("Right to be Forgotten") fulfilled via off-chain crypto-shredding key destruction.
- **Zero-Knowledge Roadmap:** Planned zk-SNARK rollup migration for sub-cent transaction processing.
