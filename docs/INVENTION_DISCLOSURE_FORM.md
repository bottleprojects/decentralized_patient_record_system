# Invention Disclosure Form: DPRMS
**Document Reference**: K&K Revised Clean (2026)  
**Project**: Decentralized Patient Record Management System (DPRMS)  
**Inventors**: Abhinav S P (25BCE5381), G Prathish Rajan (25BCE5367)  
**Department & Institution**: School of Computer Science and Engineering (SCOPE), Vellore Institute of Technology (VIT), Chennai Campus, Tamil Nadu, India.

---

### Section 1: Title of the Invention
**SYSTEM AND METHOD FOR CRYPTOGRAPHICALLY BOUND IOT SENSOR ACQUISITION AND DUAL-INTEGRITY DECENTRALIZED RECORD ARCHIVAL** *(14 words)*

---

### Section 2: What is the Invention? (Problem & Solution Statement)

#### A. Problem Statement
Modern electronic health record (EHR) management faces a critical, systemic architectural vulnerability known as the **"Garbage-In, Garbage-Out" (GIGO) trust gap**. While distributed ledger technologies (blockchains) and decentralized storage networks (e.g., IPFS) can guarantee that an archived digital file remains tamper-evident once committed, they operate completely disconnected from the physical telemetry acquisition layer. 

Existing systems take arbitrary, unauthenticated documents (such as client-synthesized PDFs or doctor-terminal CSVs) and store their cryptographic hashes on-chain. This creates three fatal security vulnerabilities:
1. **Ingestion Fraud & Malpractice Masking**: A compromised client or rogue practitioner can submit synthetically fabricated vitals (e.g., normal cardiac rhythms to conceal medical negligence), which the blockchain then immutably notarizes as truth.
2. **Replay & Man-in-the-Middle Attacks**: Sensor telemetry packets sent over hospital or home Wi-Fi/cellular networks lack hardware-rooted cryptographic authentication, allowing adversaries to replay historical physiological packets.
3. **Inadequate Verification**: Existing retrieval protocols only verify single-layer file integrity (`retrieved file hash == blockchain hash`), possessing zero cryptographic capability to audit whether the document contents legitimately originated from an authorized physical sensor during an authenticated measurement session.

#### B. Solution Provided by the Invention
The present invention solves this foundational trust gap by establishing an unbroken, cyber-physical cryptographic provenance chain extending from physical sensor silicon to retrieval-time verification through an integrated 9-step architecture:
1. **Physical Acquisition**: A pre-registered IoT sensor device (e.g., micro-optical photoplethysmography and Lead-II biopotential analog front-end) obtains actual physiological measurements from a patient.
2. **Ingestion Binding**: Each raw measurement packet is bound at the edge to a triple consisting of a unique hardware device identity (`Device_ID`), high-resolution measurement timestamp (Epoch UTC), and an ephemeral capture-session identifier (`Session_UUID`).
3. **Edge Authentication**: The sensor device cryptographically authenticates each measurement packet at the edge utilizing a hardware-protected cryptographic key (HMAC-SHA256 digest or asymmetric digital signature).
4. **Ingestion Gating & Freshness Validation**: A backend ingestion gateway validates device identity against an authorized registry, verifies packet freshness within a strict dynamic temporal tolerance window ($\Delta t \le 120$ seconds) to mathematically preclude replay attacks, and enforces physiological boundary integrity (strictly rejecting synthetic placeholders such as static 74 BPM or 98% SpO₂ constants).
5. **Clinical Report Synthesis**: A specialized capture module compiles the authenticated raw time-series data into a standardized diagnostic record (e.g., PDF/A or structured FHIR payload).
6. **Cryptographic Metadata Binding**: The synthesized report is cryptographically bound to its acquisition metadata by embedding a cryptographically verifiable acquisition manifest (containing device identity, session UUID, acquisition start/end timestamps, sample count, and edge signature) directly into the file structure.
7. **Off-Chain Decentralized Archival**: The cryptographically bound report is encrypted using authenticated symmetric encryption (AES-256-GCM, producing ciphertext, initialization vector, and a 128-bit authentication tag) and pinned to a decentralized content-addressed storage swarm (IPFS).
8. **On-Chain Verifiable Cryptographic Reference**: A compact 128-byte cryptographic seal (encapsulating the IPFS multihash, ciphertext/plaintext SHA-256 digest, acquisition session digest, and timestamp) is anchored to an Ethereum smart contract. Access control permissions are strictly enforced at the application/backend layer, ensuring the smart contract functions purely as an immutable, tamper-evident notarization and event registry without incurring unsustainable on-chain gas costs.
9. **Dual-Integrity Retrieval Verification**: During retrieval by an authorized physician, the system executes an automated two-tier verification algorithm: Tier 1 verifies file storage integrity against the on-chain cryptographic reference, while Tier 2 decrypts the encapsulated acquisition manifest and verifies that the physiological data is cryptographically authenticated by the registered hardware sensor from that specific physical session.

#### C. General Purpose
The general purpose of this invention is to deliver an end-to-end, zero-trust remote patient monitoring (RPM) and clinical record management architecture that guarantees non-repudiable medical telemetry integrity, completely eliminates data falsification at the ingestion point, and ensures regulatory compliance with HIPAA, FDA IoMT cybersecurity mandates, and EU MDR.

---

### Section 3: Search Terms
Internet of Medical Things (IoMT); Hardware-Rooted Cryptographic Provenance; Edge Sensor Authentication; Dual-Integrity Verification; Replay Attack Mitigation; Decentralized Patient Record Management; InterPlanetary File System (IPFS) Content-Addressing; Smart Contract Notarization; AES-256-GCM Envelope Encryption; Capture-Session Binding; Physiological Waveform Validation; Tamper-Evident Biometric Auditing; Zero-Trust Healthcare Ingestion; Merkle Directed Acyclic Graph (DAG); Non-Repudiable Clinical Telemetry.

---

### Section 4: Background of the Invention
- **Present Technologies**:
  1. *Centralized Cloud EHR Systems*: AWS S3, Google Cloud Healthcare API, Azure Health Data Services, and Supabase Object Storage, referenced by relational database pointers.
  2. *First-Generation Blockchain Healthcare*: MIT MedRec (Ekblaw et al., 2016), Ancile (Xia et al., 2017), and generic blockchain-IPFS implementations.
  3. *Standalone IoMT Gateways*: Bedside monitors streaming unencrypted or TLS-only telemetry to centralized hospital servers.
- **Limitations**:
  1. *GIGO Blindspot*: Blockchain only verifies that uploaded files haven't changed; zero visibility into physical sensor validity.
  2. *Replay Attacks*: Standard IoMT streams lack session-UUID binding.
  3. *Silent Cloud Corruption*: Mutable URI paths allow silent overwrites by compromised administrators or ransomware.
  4. *Prohibitive Gas Costs*: Storing 1 MB directly on-chain consumes ~3.2 billion gas ($3,500+).

---

### Section 5: Prior Art & Clear Technical Distinctions
1. **MIT MedRec (Ekblaw et al., 2016)**:
   - *Limitation*: Manages database pointers across hospital EHR servers.
   - *DPRMS Distinction*: MedRec assumes the database is honest and has no concept of edge sensor registration, packet authentication, or dual-integrity retrieval.
2. **Ancile (Xia et al., 2017)**:
   - *Limitation*: Uses smart contracts for access control and proxy re-encryption.
   - *DPRMS Distinction*: High latency/gas for routine permissions; lacks hardware-rooted sensor provenance and acquisition manifest encapsulation.
3. **US Patent App US20180096110A1**:
   - *Limitation*: Software-level document indexing.
   - *DPRMS Distinction*: Fails to bridge the cyber-physical gap between sensor hardware sampling and immutable retrieval auditing.

---

### Section 6: Major Gap Filled
The invention fills the **Cyber-Physical Ingestion Trust Boundary in Decentralized Healthcare**. It replaces blind trust in client-uploaded documents with mathematically verifiable silicon-to-retrieval provenance.

---

### Section 7: Components of the Invention
- **Registered Edge IoT Sensor**: ESP32 MCU, MAX30102 PPG sensor, AD8232 Lead-II ECG front-end, secure key storage.
- **Backend Ingestion Gateway**: FastAPI async service, HMAC signature verification, temporal freshness validator ($\Delta t \le 120$s), physiological boundary checker.
- **Capture Module**: Vitals report compiler (PDF/A, FHIR) with embedded Acquisition Metadata Manifest.
- **Decentralized Archival**: Authenticated AES-256-GCM cipher and Kubo IPFS cluster node.
- **Distributed Ledger**: `PatientRecord.sol` deployed on Ethereum Sepolia, anchoring 128-byte seals.
- **Dual-Integrity Retrieval Engine**: Two-tier verification algorithm (file integrity + acquisition provenance).

---

### Section 8: Chronological Sequence (The 9-Step Pipeline)
1. Device Registration & Key Provisioning
2. Physical Sensor Acquisition
3. Edge Cryptographic Authentication
4. Ingestion Gating & Freshness Validation ($\Delta t \le 120$s)
5. Clinical Report Synthesis
6. Cryptographic Metadata Binding (Acquisition Manifest)
7. AES-256-GCM Encryption & IPFS Archival
8. On-Chain Cryptographic Reference Anchoring (128-Byte Seal)
9. Dual-Integrity Retrieval Verification

---

### Section 9: Novelty & Inventive Step
The inventive step resides in the non-obvious combination of edge-rooted cryptographic packet signing, dynamic temporal freshness gating, document-level acquisition manifest encapsulation, and dual-integrity retrieval verification.

---

### Section 10: Advantages & Improvements
- **99.998% Gas Fee Reduction**: 75,214 gas vs. 3.2 billion gas for on-chain storage.
- **Zero GIGO Ingestion Vulnerability**: Mathematically proves physical sensor provenance.
- **Immunity to Replay Attacks**: Temporal tolerance window ($\Delta t \le 120$s) and session nonces.
- **29.3% Faster FCP**: 590 ms on edge vs. 834 ms on centralized architecture.

---

### Section 15: Empirical Benchmark Data (785 Total Operations)
- **Upload Latency**: 100 KB takes 1,065 ms (centralized) vs 3,549 ms (IPFS); 1 MB takes 2,319 ms vs 5,931 ms.
- **The 5 MB Monolithic Upload Cliff**: 90% socket timeout failure rate on unchunked 5 MB payloads over international IPFS links, establishing 1 MB as the optimal chunking threshold.
- **Warm Cache Retrieval**: 381 ms (centralized) vs 5,884 ms (IPFS). The 5.5s difference represents the required cost of zero-trust verification (dynamic IPFS fetch + AES-256-GCM decryption + Ethereum Sepolia hash verification).

---

### Section 20: Proposed Claims
- **Claim 1 (Independent Method Claim)**: 9-step acquisition, binding, archival, and dual-integrity verification method.
- **Claim 2 (Independent System Claim)**: Cyber-physical decentralized patient record apparatus.
- **Claim 3 (Dependent Claim - Freshness & Anti-Replay)**: Temporal gating ($\Delta t \le 120$s) and monotonic sequence auditing.
- **Claim 4 (Dependent Claim - Metadata Binding)**: Byte-level acquisition manifest embedding in PDF/A or FHIR.
- **Claim 5 (Independent Claim - Dual-Integrity Engine)**: Two-tier validation algorithm.

---

### Section 24: Commercialization Data
1. **Philips Healthcare** (Amsterdam, Netherlands)
2. **Medtronic plc** (Dublin, Ireland / Minneapolis, USA)
3. **GE HealthCare Technologies Inc.** (Chicago, USA)
4. **Epic Systems Corporation** (Verona, USA)
5. **Oracle Health / Cerner** (Austin, USA)

---

### Section 28: Technology Readiness Level
**TRL 4** (Technology validated in lab) & **TRL 5** (Validated in relevant clinical environment).
