# INVENTION DISCLOSURE FORM (K&K REVISED)
**Project Title**: Decentralized Patient Record Management System (DPRMS)  
**Inventors**: Abhinav S P (25BCE5381), G Prathish Rajan (25BCE5367)  
**Institution**: School of Computer Science and Engineering (SCOPE), Vellore Institute of Technology (VIT), Chennai Campus, Tamil Nadu, India.  

---


## Section 1. Title of the Invention (should not exceed 15 words)

SYSTEM AND METHOD FOR CRYPTOGRAPHICALLY BOUND IOT SENSOR ACQUISITION AND DUAL-INTEGRITY DECENTRALIZED RECORD ARCHIVAL


## Section 2. What is the Invention?
(Should include Problem and Solution statement and general purpose in relation with your invention)

A. Problem Statement:
Modern electronic health record (EHR) management faces a critical, systemic architectural vulnerability known as the 'Garbage-In, Garbage-Out' (GIGO) trust gap. While distributed ledger technologies (blockchains) and decentralized storage networks (e.g., IPFS) can guarantee that an archived digital file remains tamper-evident once committed, they operate completely disconnected from the physical telemetry acquisition layer. Existing systems take arbitrary, unauthenticated documents (such as client-synthesized PDFs or doctor-terminal CSVs) and store their cryptographic hashes on-chain. This creates three fatal security vulnerabilities: (1) Ingestion Fraud & Malpractice Masking: A compromised client or rogue practitioner can submit synthetically fabricated vitals (e.g., normal cardiac rhythms to conceal medical negligence), which the blockchain then immutably notarizes as truth; (2) Replay & Man-in-the-Middle Attacks: Sensor telemetry packets sent over hospital or home Wi-Fi/cellular networks lack hardware-rooted cryptographic authentication, allowing adversaries to replay historical physiological packets; and (3) Inadequate Verification: Existing retrieval protocols only verify single-layer file integrity (retrieved file hash == blockchain hash), possessing zero cryptographic capability to audit whether the document contents legitimately originated from an authorized physical sensor during an authenticated measurement session.
B. Solution Provided by the Invention:
The present invention solves this foundational trust gap by establishing an unbroken, cyber-physical cryptographic provenance chain extending from physical sensor silicon to retrieval-time verification through an integrated 9-step architecture:
1. Physical Acquisition: A pre-registered IoT sensor device (e.g., micro-optical photoplethysmography and Lead-II biopotential analog front-end) obtains actual physiological measurements from a patient.
2. Ingestion Binding: Each raw measurement packet is bound at the edge to a triple consisting of a unique hardware device identity (Device_ID), high-resolution measurement timestamp (Epoch UTC), and an ephemeral capture-session identifier (Session_UUID).
3. Edge Authentication: The sensor device cryptographically authenticates each measurement packet at the edge utilizing a hardware-protected cryptographic key (HMAC-SHA256 digest or asymmetric digital signature).
4. Ingestion Gating & Freshness Validation: A backend ingestion gateway validates device identity against an authorized registry, verifies packet freshness within a strict dynamic temporal tolerance window (Delta_t <= 120 seconds) to mathematically preclude replay attacks, and enforces physiological boundary integrity (strictly rejecting synthetic placeholders such as static 74 BPM or 98% SpO2 constants).
5. Clinical Report Synthesis: A specialized capture module compiles the authenticated raw time-series data into a standardized diagnostic record (e.g., PDF/A or structured FHIR payload).
6. Cryptographic Metadata Binding: The synthesized report is cryptographically bound to its acquisition metadata by embedding a cryptographically verifiable acquisition manifest (containing device identity, session UUID, acquisition start/end timestamps, sample count, and edge signature) directly into the file structure.
7. Off-Chain Decentralized Archival: The cryptographically bound report is encrypted using authenticated symmetric encryption (AES-256-GCM, producing ciphertext, initialization vector, and a 128-bit authentication tag) and pinned to a decentralized content-addressed storage swarm (IPFS).
8. On-Chain Verifiable Cryptographic Reference: A compact 128-byte cryptographic seal (encapsulating the IPFS multihash, ciphertext/plaintext SHA-256 digest, acquisition session digest, and timestamp) is anchored to an Ethereum smart contract. Access control permissions are strictly enforced at the application/backend layer, ensuring the smart contract functions purely as an immutable, tamper-evident notarization and event registry without incurring unsustainable on-chain gas costs.
9. Dual-Integrity Retrieval Verification: During retrieval by an authorized physician, the system executes an automated two-tier verification algorithm: Tier 1 verifies file storage integrity against the on-chain cryptographic reference, while Tier 2 decrypts the encapsulated acquisition manifest and verifies that the physiological data is cryptographically authenticated by the registered hardware sensor from that specific physical session.
C. General Purpose:
The general purpose of this invention is to deliver an end-to-end, zero-trust remote patient monitoring (RPM) and clinical record management architecture that guarantees non-repudiable medical telemetry integrity, completely eliminates data falsification at the ingestion point, and ensures regulatory compliance with HIPAA, FDA IoMT cybersecurity mandates, and EU MDR.


## Section 3. Search Terms
(Please provide key words and common industry phrases on the basis of which this invention could be connected with the prior art)

Internet of Medical Things (IoMT); Hardware-Rooted Cryptographic Provenance; Edge Sensor Authentication; Dual-Integrity Verification; Replay Attack Mitigation; Decentralized Patient Record Management; InterPlanetary File System (IPFS) Content-Addressing; Smart Contract Notarization; AES-256-GCM Envelope Encryption; Capture-Session Binding; Physiological Waveform Validation; Tamper-Evident Biometric Auditing; Zero-Trust Healthcare Ingestion; Merkle Directed Acyclic Graph (DAG); Non-Repudiable Clinical Telemetry.


## Section 4. Background of the Invention (Present state of Art)


### What are the present technologies that exist in the field of your invention
Existing healthcare architectures predominantly fall into three categories:
1. Centralized Cloud Electronic Health Record (EHR) Systems: Cloud platforms (such as AWS S3, Google Cloud Healthcare API, Microsoft Azure Health Data Services, and Supabase Object Storage) referenced by relational database pointers (PostgreSQL, MySQL). Standard enterprise EHR software includes Epic Systems, Cerner (Oracle Health), and MEDITECH.
2. First-Generation Blockchain Healthcare Architectures: Academic and pilot frameworks such as MIT MedRec (Ekblaw et al., 2016), Ancile (Xia et al., 2017), and generic blockchain-IPFS implementations that store patient document pointers or cryptographic hashes on an Ethereum or Hyperledger Fabric ledger.
3. Standalone Internet of Medical Things (IoMT) Gateways: Proprietary bedside patient monitors and remote monitoring hubs (e.g., Philips IntelliVue, GE Healthcare CARESCAPE) that stream unencrypted or TLS-only telemetry to centralized hospital telemetry servers.


### What are the limitations of the same?
Current technologies suffer from profound architectural limitations:
1. The 'Garbage-In, Garbage-Out' (GIGO) Ingestion Blindspot: Prior blockchain systems (MedRec, Ancile, etc.) provide immutability ONLY for data after it has been uploaded. They have zero visibility into how the data was acquired. If an attacker, rogue practitioner, or compromised client uploads a fabricated PDF containing falsified heart rates or synthesized ECG waveforms (e.g., to hide patient distress or avoid malpractice claims), the blockchain faithfully seals the fraudulent file forever. Prior art fails to bridge the cyber-physical gap between sensor hardware and the ledger.
2. Vulnerability to Replay & Sensor Spoofing: Standard IoMT systems lack hardware-level cryptographic session binding. An adversary with network access can intercept a benign vitals packet and replay it continuously while a patient is in acute cardiac arrest, completely bypassing server checks.
3. Silent Data Corruption in Centralized Stores: Centralized object stores address files by mutable uniform resource identifiers (URIs). If a database superuser, rogue system administrator, or ransomware payload alters the stored document bytes without changing the URI path, the clinical application cannot detect the corruption, endangering patient life.
4. Prohibitive On-Chain Storage Costs: Attempting to store raw medical telemetry or clinical reports directly on a blockchain is economically impossible. As proven by our empirical benchmarks, storing a single 1 MB record on Ethereum requires approximately 3.2 billion gas (costing thousands of dollars per record), rendering pure on-chain systems unviable.
5. Single-Layer Integrity Checks: Existing decentralized systems only check if retrieved_file_hash == onchain_hash. If the file hash matches, the system considers it valid, failing to verify whether the underlying biometric waveform was genuine or synthesized.


## Section 5. Prior Art
(Please provide the details of the product or process by the help of which the problem solved by the invention was tackled before this invention. Please details of prior technologies, patents, or publications relevant to this invention)

Detailed Prior Art Breakdown and Clear Technical Distinctions:
1. MIT MedRec (Ekblaw et al., 'A Case Study for Blockchain in Healthcare', IEEE, 2016):
   - Nature of Prior Art: MedRec uses Ethereum smart contracts to manage access permissions, data ownership, and database pointers across disparate hospital EHR systems. Medical data remains stored in traditional hospital databases.
   - Deficiencies & DPRMS Distinctions: MedRec does not interact with IoT medical hardware. It does not perform edge cryptographic signing, packet freshness gating, capture-session metadata binding, or dual-integrity verification. MedRec assumes the hospital database is already honest. DPRMS establishes a zero-trust hardware provenance chain directly from IoT sensor silicon.

2. Ancile (Xia et al., 'Ancile: Privacy-preserving framework for access control of electronic health records using blockchain', IEEE, 2017):
   - Nature of Prior Art: Ancile employs smart contracts on Ethereum to enforce advanced cryptographic access control and proxy re-encryption over off-chain cloud databases.
   - Deficiencies & DPRMS Distinctions: Ancile attempts to enforce authorization logic directly on-chain, causing severe scalability and latency bottlenecks. Crucially, Ancile has no mechanism to cryptographically authenticate sensor telemetry at ingestion or bind physical acquisition metadata to archived files. DPRMS offloads access permissions to a high-speed backend while using the ledger purely for immutable cryptographic anchoring, achieving dual-integrity validation on retrieval.

3. US Patent Application US20180096110A1 ('Blockchain-based Electronic Health Record System'):
   - Nature of Prior Art: Discloses methods for storing and updating encrypted health records using blockchain transactions and distributed file systems.
   - Deficiencies & DPRMS Distinctions: Fails to disclose or anticipate: (i) edge IoT sensor packet authentication with session-UUID binding; (ii) backend freshness gating (Delta_t <= 120s); (iii) report-level acquisition metadata binding; and (iv) dual-integrity retrieval that independently validates file hash and acquisition provenance.

4. Generic IPFS + Blockchain EHR Models (Literature Survey):
   - Nature of Prior Art: Numerous academic papers propose uploading user-generated medical PDFs to IPFS and storing the IPFS hash (CID) on Ethereum.
   - Deficiencies & DPRMS Distinctions: Generic models suffer from the fatal GIGO flaw: anyone can upload an arbitrary file. DPRMS rejects arbitrary files by requiring cryptographic proof of physical sensor acquisition, enforcing dual-integrity verification on every download.


## Section 6. Has the work filled a major gap in the prior art? If yes, a brief description of this gap.

Yes, the invention definitively fills the primary unresolved gap in the state of the art: the Cyber-Physical Ingestion Trust Boundary in Decentralized Healthcare.
Prior art in decentralized healthcare has treated the 'medical record' as an abstract digital file that appears magically at the application layer. By ignoring the physical acquisition process, all existing blockchain EHR systems remain entirely vulnerable to ingestion-level data fabrication, sensor impersonation, and replay attacks.

The present invention bridges this gap by creating an unbroken, mathematically provable chain of custody: from the physical silicon photodiode and analog front-end electrode pins, through edge cryptographic signing, backend freshness gating, report-level manifest encapsulation, authenticated AES-256-GCM encryption, IPFS content-addressed archival, and smart contract anchoring, culminating in a dual-integrity retrieval protocol. This ensures that a doctor reviewing a record is guaranteed not only that the file was not altered in storage, but that the underlying physiological signals were authentically acquired from a registered patient device during an authenticated physical session.


## Section 7. What are the components of the Invention?
(Explain the external and internal parts/blocks/systems-subsystems/ composition/steps of process of your invention).

The invention comprises an integrated cyber-physical architecture divided into six primary sub-systems:
1. Registered Edge IoT Sensor Subsystem (Hardware & Firmware Tier):
   - Optical PPG Sensor: Integrated MAX30102 pulse oximeter operating red (660 nm) and infrared (880 nm) LEDs with photodiode digitizer, configured via I2C at 100 Hz sample rate.
   - Biopotential Cardiac Sensor: AD8232 single-lead heart-rate ECG analog front-end with Lead-Off detection (LO+, LO-), operational instrumentation amplifier, and high-pass filtering (0.5 Hz - 40 Hz bandwidth).
   - Edge Microcontroller: ESP32 32-bit dual-core Tensilica processor with hardware SHA/AES crypto accelerators, secure eFuse/ATECC608A key storage, and secure Wi-Fi/BLE telemetry stack.
   - Firmware Ingestion Engine: Firmware strictly programmed to sample real ADC/I2C registers, rejecting synthetic placeholders. Embeds hardware Device_ID, UTC timestamp, and Session_UUID into every packet, authenticated via HMAC-SHA256.

2. Ingestion Gateway & Security Gatekeeper (Backend Tier):
   - FastAPI Asynchronous Gateway: High-throughput ingestion endpoint handling edge telemetry streams.
   - Device Authentication Engine: Validates edge HMAC/ECDSA signatures against a cryptographic device registry.
   - Freshness & Anti-Replay Validator: Enforces strict temporal gating: abs(t_current - t_packet) <= Delta_t (configured to 120s).
   - Physiological Sanity Engine: Validates sample bounds (HR: 30-240 BPM, SpO2: 70-100%, ECG amplitude: 0.1-5.0 mV), eliminating static constants.

3. Vitals Capture & Cryptographic Binding Module:
   - Report Generator: Compiles raw authenticated time-series samples into clinical PDF/A and FHIR JSON structures.
   - Acquisition Manifest Binder: Constructs a cryptographically structured metadata manifest containing {Device_ID, Session_UUID, Start_Time, End_Time, Sample_Count, Edge_Signature, Raw_Data_Checksum} and embeds it into the file binary.

4. Encryption & Decentralized Storage Subsystem:
   - AES-256-GCM Envelope Encryption Engine: Encrypts the bound report using authenticated symmetric cipher with 96-bit unique IV and 128-bit authentication tag.
   - Content-Addressed IPFS Swarm Node: Locally hosted Kubo IPFS node with cluster pinning, transforming ciphertext into an immutable Merkle DAG CID.

5. Distributed Ledger Notarization Subsystem:
   - Smart Contract Engine: 'PatientRecord.sol' deployed on Ethereum (Sepolia testnet / mainnet), recording 128-byte cryptographic seals {fileHash, ipfsCid, sessionDigest, owner, timestamp} and emitting verifiable event logs.
   - Application Permission Enforcement: RBAC/ABAC access control enforced strictly at the database/JWT layer, preserving ledger efficiency.

6. Dual-Integrity Retrieval & Verification Engine:
   - Retrieval Orchestrator: Fetches encrypted payload from IPFS, decrypts via AES-256-GCM, and executes two-tier verification: Tier 1 validates file hash against blockchain; Tier 2 extracts the acquisition manifest and verifies edge sensor provenance.


## Section 8. How does the Invention work? Please describe the complete sequence of operation of the invention, including the inputs received, processing or operations performed, interaction between the relevant components, and the resulting output, action, or technical effect.
(This portion of your invention disclosure deals with the working of your invention, the processes involved and the interactive actions taking place between the various components of your invention to give the desired output.)

Complete Chronological Sequence of Operation (The 9-Step Pipeline):
Step 1: Device Registration and Key Provisioning
Each IoT medical sensor device is provisioned with a unique cryptographic identity (Device_ID) and symmetric/asymmetric key pair stored in secure silicon (eFuse or hardware secure element). The public credential or shared key is registered within the secure backend registry linked to authorized clinical assets.

Step 2: Physical Sensor Acquisition
Upon clinical initiation, an ephemeral capture-session identifier (Session_UUID) is negotiated. The registered sensor obtains actual physiological signals from the patient (e.g., raw IR/Red photoplethysmographic absorption from MAX30102 and biopotential microvolt deflections from AD8232). The firmware samples hardware registers directly at 100-250 Hz without synthetic interpolation.

Step 3: Edge Cryptographic Authentication
The edge MCU aggregates raw sample vectors into measurement packets: P = {Device_ID, Session_UUID, Timestamp_UTC, Vitals_Vector}. The MCU computes a cryptographic authenticator over P using its hardware key: Sig_Dev = HMAC-SHA256(K_Dev, P) or ECDSA_Sign(PrivKey_Dev, H(P)).

Step 4: Backend Ingestion Gating & Freshness Validation
The backend gateway receives packet P and Sig_Dev. It performs three mandatory checks: (i) Cryptographic verification of Sig_Dev; (ii) Freshness audit: abs(T_server - Timestamp_UTC) <= 120s; packets outside the window or with duplicate nonces are dropped as replay attacks; (iii) Physiological validity check: verifies that readings represent authentic dynamic waveforms rather than synthetic constants (rejecting static 74 BPM / 98% SpO2).

Step 5: Clinical Report Synthesis
The capture module ingests the validated stream for the entire capture session (e.g., 60 seconds) and generates a standardized clinical report (PDF/A or structured FHIR record), plotting the genuine physiological waveforms and computing clinical indices.

Step 6: Cryptographic Metadata Binding
The capture module constructs an Acquisition Metadata Manifest: M_acq = {Device_ID, Session_UUID, Start_Time, End_Time, Sample_Count, Aggregate_Sensor_Hash, Edge_Signature}. This manifest is embedded into the report binary, binding the document inextricably to its physical acquisition provenance: Bound_Report = Embed(Report, M_acq).

Step 7: AES-256-GCM Encryption & IPFS Archival
The bound report is encrypted using AES-256-GCM with a freshly generated symmetric key K_sym and IV_96, producing Ciphertext and a 128-bit Auth_Tag. The Ciphertext is uploaded to an IPFS node, which chunks the payload into a Merkle DAG and returns an immutable Content Identifier (CID).

Step 8: On-Chain Cryptographic Reference Anchoring
The system commits a compact 128-byte cryptographic seal to the Ethereum smart contract ('PatientRecord.sol'): Seal = {fileHash: SHA256(Plaintext), ipfsCid: CID, sessionDigest: SHA256(M_acq), timestamp: now}. The contract emits a verifiable RecordCreated event. The application database manages patient/doctor access control permissions independently, keeping on-chain gas costs at a minimal ~75,000 gas.

Step 9: Dual-Integrity Retrieval Verification
When an authorized doctor accesses the record: (i) Backend verifies doctor permissions via JWT; (ii) The encrypted payload is fetched from IPFS using CID; (iii) Payload is decrypted via AES-256-GCM and Auth_Tag is checked; (iv) Tier 1 Verification: Computes SHA256(Decrypted_File) and compares with on-chain fileHash; (v) Tier 2 Verification: Extracts M_acq, verifies SHA256(M_acq) == on-chain sessionDigest, and validates that M_acq matches the authenticated physical sensor device signature. Only when both tiers pass is the record certified as authentic to the physician.


## Section 9. Novelty of the Invention/Inventive Step of the Invention
(Please state the unique/ novel aspect of your invention and how it is different and/or better than the existing technologies):

The inventive step lies in the non-obvious synergy of hardware-rooted edge authentication, report-level acquisition metadata binding, and dual-integrity decentralized retrieval:
1. Elimination of the GIGO Trust Boundary: Unlike all prior art (which only guarantees that an uploaded file hasn't changed), the present invention provides end-to-end cryptographic proof that the data inside the file actually originated from authenticated silicon sensor pins on a real patient during an authenticated temporal session.

2. Edge-to-Report Cryptographic Binding: Encapsulating the physical acquisition manifest (device identity, edge signature, sample count, session UUID) directly within the encrypted archival artifact, linking off-chain physical reality to on-chain cryptographic reference.

3. Dual-Integrity Verification Protocol: Decoupling storage integrity verification (file tamper-proofing) from acquisition provenance verification (sensor authenticity auditing), enabling automated detection of client-level forgery.

4. Pragmatic Gas-Optimized Scalability: Recording a 128-byte cryptographic seal on-chain while keeping access control enforcement at the backend application layer, reducing gas consumption by 99.998% compared to on-chain storage while preserving 100% cryptographic auditability.


## Section 10. What are the advantages and improvements over the existing methods/devices? (Please list advantages and improvements against closest patent and non-patent documents/products in pipeline explaining technical advancement of present invention over the existing technologies)

Empirically Validated Advantages over Existing Systems:
1. Absolute Mathematical Non-Repudiation: Malicious doctors or administrators cannot forge, alter, or retrospectively doctor patient vitals. Ingestion-level hardware signing guarantees legal and forensic integrity.
2. Immunity to Replay and Spoofing Attacks: Dynamic temporal freshness gating (Delta_t <= 120s) and session nonces prevent adversaries from replaying recorded vitals packets.
3. 99.998% Gas Fee Reduction: On-chain anchoring of a 128-byte seal consumes only ~75,000 gas per record, compared to ~3.2 billion gas required to store a 1 MB payload directly on Ethereum, making decentralized healthcare economically viable.
4. Immunity to Silent Cloud Corruption: By leveraging IPFS cryptographic content-addressing (SHA-256 multihashes), any bit rot, server compromise, or unauthorized file overwrite immediately breaks the CID and is caught during retrieval.
5. Superior Edge Performance: Deployment of the decentralized frontend on edge networks achieves a 29.3% faster First Contentful Paint (590 ms vs 834 ms for centralized architecture), improving clinical UI responsiveness.


## Section 11. Do you have in your mind as a researcher/inventor some ideas as to what are the various other/alternative forms in which your Invention can be depicted or utilized, in addition to one basic embodiment that has been described above?
(This will lay the foundation, for making your patent as broad as possible. These are called preferred embodiments or variants.)

Alternative Embodiments and Implementations in the Inventor's Mind:
1. Wearable Consumer Health Integration: Integration with smartwatches (Apple Watch, Samsung Galaxy Watch, Fitbit) where the onboard secure enclave signs photoplethysmography and single-lead ECG packets for decentralized home monitoring.
2. Multi-Parameter ICU Patient Monitor Integration: Adapting the edge cryptographic firmware into commercial multi-parameter monitors (Mindray, Philips IntelliVue) via an auxiliary hardware security module (HSM) to authenticate 12-lead ECG, invasive blood pressure, and capnography streams.
3. Zero-Knowledge Proof (zk-SNARK) Verification: Generating zero-knowledge cryptographic proofs of sensor readings (e.g., proving a patient's pulse exceeded 150 BPM or SpO2 dropped below 90% to trigger an automated smart contract insurance payout) without revealing private patient identity or medical data.
4. Post-Quantum Cryptographic Migration: Upgrading edge signature schemes and on-chain hashing to lattice-based post-quantum cryptography (e.g., CRYSTALS-Dilithium) to resist future quantum computing threats.
5. Decentralized Autonomous Clinical Trials: Applying the dual-integrity pipeline to pharmaceutical clinical trials, preventing research organizations from manipulating patient drug response vitals.


## Section 12. Please provide final CAD images, line diagrams, and schematic images of the final prototype illustrating all the essential elements of the invention, and shortlist the major/primary drawings that need to be incorporated in the Complete Specification. 
(Please prepare images in two sets, one completely labeled to details and the second one without any description, legends/labeling or numbering. Include relevant Flow charts.)

System Architecture and Dual-Integrity Dataflow Schematics:
DIAGRAM 1: END-TO-END CRYPTOGRAPHIC PROVENANCE PIPELINE
+-------------------------+       +--------------------------+       +------------------------+
|   PHYSICAL SENSOR       |       |     INGESTION GATEWAY    |       |   REPORT SYNTHESIS     |
| MAX30102 (PPG / SpO2)   | ----> | 1. Authenticate Sig_Dev  | ----> | 1. Synthesize PDF/FHIR |
| AD8232 (Lead-II ECG)    |       | 2. Freshness: dt <= 120s |       | 2. Bind Acquisition    |
| ESP32 Hardware Signing  |       | 3. Boundary Integrity    |       |    Manifest (M_acq)    |
+-------------------------+       +--------------------------+       +------------------------+
                                                                                  |
                                                                                  v
+-------------------------+       +--------------------------+       +------------------------+
|    ETHEREUM LEDGER      |       |  DUAL-INTEGRITY ENGINE   |       |   ENCRYPTION & IPFS    |
| Seal: {fileHash, CID,   | <---- | Tier 1: File Integrity   | <---- | 1. AES-256-GCM Encrypt |
|        sessionDigest}   |       | Tier 2: Sensor Provenance|       | 2. Pin to IPFS Swarm   |
+-------------------------+       +--------------------------+       +------------------------+

DIAGRAM 2: PACKET DATA STRUCTURE & VERIFICATION FLOW
Edge Packet:    [ Device_ID | Session_UUID | Timestamp_UTC | Vitals_Data | HMAC-SHA256 Signature ]
Report Manifest:[ Device_ID | Session_UUID | Sample_Count | Raw_Checksum | Edge_Signature ]
On-Chain Seal:  [ bytes32 fileHash | string ipfsCid | bytes32 sessionDigest | address owner ]
Verification:   (1) SHA256(Decrypted_File) == fileHash   AND   (2) SHA256(M_acq) == sessionDigest


## Section 13. Brief description from the researcher/inventor in his own words explaining the images/ drawings.

Brief Description from the Inventors:
We have built an end-to-end decentralized healthcare record system that solves the biggest vulnerability in modern digital medicine: trusting the source of medical data. Until now, all blockchain healthcare systems just took a PDF or data file from a computer and hashed it onto a blockchain. But if someone faked the heart rate or ECG on that computer, the blockchain would just permanently record a lie.

Our system changes this completely. We start right at the physical sensor hardware: an ESP32 microcontroller reading genuine optical pulse and ECG signals from a patient. The sensor cryptographically signs every data packet with its own hardware key, tagging it with a session ID and timestamp. Our backend checks that the sensor is genuine, that the data is arriving in real-time (preventing replays), and that the readings are real human signals. It compiles the data into a report, locks the sensor's signature and session details directly into the report bytes, encrypts it with AES-256-GCM, stores it on IPFS, and commits a 128-byte cryptographic seal to an Ethereum smart contract.

When a doctor opens the record, the system automatically checks two things: first, that the file has never been modified (matching the blockchain hash), and second, that the data inside truly came from the authenticated sensor during that exact patient session. It gives doctors, patients, and hospitals 100% mathematical certainty that clinical records are genuine, tamper-free, and legally non-repudiable, while costing 99.998% less than storing records on-chain.


## Section 14. Please provide a complete description of the invention, including its working methodology and working examples illustrating the inventive aspects of the corresponding invention.

Complete Technical Description of the Invention:
1. Cyber-Physical Ingestion Architecture:
The system utilizes a dedicated IoT edge device comprising an ESP32 microcontroller interfaced with a MAX30102 optical sensor (for photoplethysmographic pulse rate and SpO2 calculation via red/IR absorption ratios) and an AD8232 analog front-end (for Lead-II biopotential electrocardiography with lead-off detection). The firmware operates an unbuffered reading routine that pulls raw ADC samples directly from hardware pins, rejecting placeholder constants.

2. Edge Cryptographic Protocol:
Upon initiating a monitoring session, an authenticated handshake establishes an ephemeral Session_UUID. Every telemetry packet P contains: P = {device_id, session_uuid, timestamp, sequence_num, pulse_rate, spo2, ecg_samples[]}. The ESP32 computes an HMAC-SHA256 signature using a pre-provisioned secret key stored in protected silicon. The packet and signature are transmitted via secure HTTPS/WSS to the backend gateway.

3. Multi-Stage Ingestion Gatekeeper:
The FastAPI backend gateway subjects every incoming packet to three deterministic verification gates before accepting it:
   - Gate 1 (Cryptographic Authenticity): Verifies the HMAC-SHA256 signature against the device registry public key.
   - Gate 2 (Temporal Freshness & Anti-Replay): Calculates delta_t = |t_server - t_packet|. If delta_t > 120 seconds, or if sequence_num is non-monotonic, the packet is rejected and flagged as an attempted replay.
   - Gate 3 (Physiological Sanity): Validates that physiological values fall within plausible human biometric bounds (BPM between 30 and 240, SpO2 between 70% and 100%, ECG microvolts dynamic and non-flatline), explicitly filtering synthetic placeholders.

4. Vitals Report Compilation and Manifest Encapsulation:
When a session completes, the capture module synthesizes a standardized diagnostic PDF/A report. Crucially, the module computes an Acquisition Metadata Manifest M_acq = {device_id, session_uuid, start_time, end_time, total_samples, edge_signature_root, raw_checksum}. This manifest is embedded into the binary structure of the document (within the document metadata dictionary and structural trailer), cryptographically binding the report to the physical sensor session.

5. Authenticated AES-256-GCM Envelope Encryption and IPFS Archival:
The bound report byte stream is encrypted using AES-256 in Galois/Counter Mode (GCM). A 256-bit symmetric key K_sym is generated, yielding ciphertext C, 96-bit initialization vector IV, and 128-bit authentication tag Tag. The ciphertext C is submitted to a local IPFS daemon, which constructs a UnixFS Merkle Directed Acyclic Graph (DAG) and returns a unique, immutable Content Identifier (CID).

6. Smart Contract Notarization & Access Control Architecture:
A lightweight Ethereum smart contract ('PatientRecord.sol') maintains the cryptographic audit trail. Instead of storing large payloads or managing granular access control on-chain (which causes extreme gas costs), the contract exposes a notarizeRecord() function accepting a compact 128-byte seal: {bytes32 fileHash, string ipfsCid, bytes32 sessionDigest, address owner, uint256 timestamp}. Access control (patient consent, doctor permissions) is strictly enforced at the backend/application layer using signed JSON Web Tokens (JWT) and PostgreSQL row-level security. The smart contract acts as an immutable, tamper-evident public notary.

7. Dual-Integrity Retrieval Engine:
When an authorized physician requests the record: (1) Backend verifies authorization token; (2) Encrypted payload is streamed from IPFS via CID; (3) AES-256-GCM decryption executes and checks Tag; (4) Tier 1 Verification computes SHA256(Decrypted_File) and queries the smart contract to confirm identity with on-chain fileHash; (5) Tier 2 Verification extracts M_acq, computes SHA256(M_acq), and verifies identity with on-chain sessionDigest while validating the device signature against the hardware registry. Both tiers must yield mathematical equality for the record to be rendered.


## Section 15. Please provide details of experiments conducted and/or third-party validation data, if any, along with the mathematical equations, formulas, or calculations used in the invention, wherever the invention performs arithmetic calculations or mathematical operations.

Comprehensive Empirical Benchmarking (785 Total Transaction Executions):
Rigorous empirical performance and security testing was conducted comparing the decentralized DPRMS architecture against traditional centralized cloud storage (Supabase / AWS S3). The benchmarks evaluated synthetic medical payloads of 100 KB, 1 MB, and 5 MB across unthrottled Gigabit Fiber and throttled Fast 4G cellular profiles:

1. Ingestion and Upload Latency:
   - At 100 KB payload: Centralized cloud achieved upload in 1,065.49 ms, whereas the decentralized IPFS pipeline required 3,549.95 ms.
   - At 1 MB payload: Centralized cloud required 2,319.02 ms, whereas decentralized IPFS required 5,931.68 ms.
   - Discovery of the 5 MB Monolithic Upload Cliff: The benchmarks uncovered that unchunked 5 MB payloads over international IPFS gateway links suffer a 90% failure rate due to gateway socket timeouts, empirically proving that 1 MB is the optimal payload boundary for decentralized clinical record chunking.

2. Retrieval Latency and Cryptographic Verification Overhead:
   - Warm Cache 100 KB Retrieval: Centralized storage took 381.98 ms (direct edge byte streaming), whereas decentralized retrieval took 5,884.78 ms. This 5.5-second differential is the direct computational cost of zero-trust security: the backend must dynamically stream from IPFS, execute AES-256-GCM decryption, verify on-chain hashes on Ethereum Sepolia, and validate the acquisition manifest.

3. Core Web Vitals & Frontend Performance:
   - First Contentful Paint (FCP): The decentralized architecture deployed on Vercel Edge achieved an FCP of 590 ms, which is 29.3% faster than the centralized system (834 ms).

4. Blockchain Gas Consumption & Cost Analysis:
   - Monolithic On-Chain Storage: Storing a 1 MB record directly on Ethereum consumes ~3.2 billion gas (costing over $3,500 at standard gas prices).
   - DPRMS 128-Byte Seal Anchoring: Our smart contract notarization consumes only 75,214 gas (~$0.08 equivalent), representing a 99.998% reduction in gas fees while maintaining identical cryptographic immutability.


## Section 16. Please provide a set of instructions or an exemplary set of code, including the code type, version, and any modifications or parameter tuning, where the invention primarily relies on software, code, or an algorithm.

Exemplary Step-by-Step Operating Instructions:
1. Device Setup: Power on ESP32 device containing provisioned HMAC key. Connect MAX30102 to I2C pins (SDA: GPIO 21, SCL: GPIO 22) and AD8232 to ADC1 (GPIO 34, LO+: GPIO 35, LO-: GPIO 32).
2. Session Initialization: Patient logs into dashboard, initiates 'Vitals Recording Session'. Backend generates session_uuid = 'sess_9f82a1' and transmits challenge nonce to ESP32.
3. Sensor Acquisition: Patient applies finger to MAX30102 and chest leads to AD8232. ESP32 continuously reads optical and biopotential signals for 60 seconds, packaging 1-second packets containing timestamp, sequence number, pulse rate, SpO2, and 100 ECG samples.
4. Ingestion Authentication: ESP32 computes HMAC-SHA256 signature per packet and posts to backend /api/clinical/vitals/stream.
5. Gateway Gating: Backend checks HMAC signature, confirms packet timestamp is within 120 seconds of server clock, and verifies values are dynamic human vitals.
6. Report Generation & Binding: Backend compiles 60-second dataset into clinical PDF, generates Acquisition Manifest M_acq, and embeds M_acq into PDF trailer.
7. Encryption & IPFS Pinning: Backend encrypts PDF via AES-256-GCM, uploads ciphertext to IPFS daemon, receiving CID 'QmZtmD2qtPBs...'.
8. Smart Contract Seal: Backend calls PatientRecord.notarizeRecord(fileHash, ipfsCid, sessionDigest) on Ethereum Sepolia, recording the 128-byte seal.
9. Retrieval Verification: Doctor accesses patient profile, clicks 'View Diagnostic Report'. System fetches ciphertext from IPFS, decrypts payload, verifies SHA256(File) == on-chain fileHash, and verifies SHA256(M_acq) == on-chain sessionDigest. UI displays green 'Dual-Integrity Verified: Authenticated Sensor & Storage' badge.


## Section 17. Please provide details of the training data, including its source, type, and relevant characteristics, where the invention relates to a machine learning (ML) model. Also, specify the ML model used and explain how the ML model is trained, implemented, and utilized in the invention.

Clarification Regarding AI / Training Data:
The core invention is a cyber-physical cryptographic architecture and distributed systems protocol; it does not rely on opaque or non-deterministic statistical machine learning models for its core validity.

Ingestion boundary checking and physiological validation are executed via deterministic clinical rule engines based on established medical biometric parameters (e.g., physiological pulse limits between 30 and 240 BPM, blood oxygen saturation between 70% and 100%, and Lead-II P-Q-R-S-T biopotential morphological waveform bounds between 0.1 mV and 5.0 mV). This deterministic approach ensures 100% mathematical auditability and eliminates the hallucination and drift risks inherent in black-box AI algorithms.


## Section 18. Please provide details of any public disclosure done/ any publication made.

Public Disclosure Status:
Academic Project Evaluation / Academic Review:
- Presented as an internal academic research project demonstration at the School of Computer Science and Engineering (SCOPE), Vellore Institute of Technology (VIT), Chennai Campus.
- The benchmark study was compiled as an internal technical report ('DPRMS Benchmark Report').
- No commercial sale, public patent publication, or commercial licensing has taken place.
- The GitHub development repository was managed under restricted development access.


## Section 19. What is the stage/level of development of the Invention?

At a basic conceptualization stage?
No, the invention has advanced significantly beyond conceptualization. A fully operational, end-to-end working cyber-physical prototype has been constructed, deployed, and tested.


### b. Completed and results validated?
Yes. Fully completed, integrated, and validated across 785 transaction executions. The operational system includes: (1) Custom ESP32 firmware running MAX30102 PPG and AD8232 ECG hardware; (2) Production FastAPI backend with cryptographic verification; (3) Live IPFS cluster node; (4) Solidity smart contract ('PatientRecord.sol') deployed and active on Ethereum Sepolia testnet; and (5) React/TypeScript physician and patient dashboard.


## Section 20. What are the aspects of your disclosure that you want to claim/monopolize? (Proposed Claims)

Proposed Patent Claims for Legal Monopoly:
Claim 1 (Independent Method Claim):
A method for cryptographically authenticating and archiving physiological telemetry in a decentralized record system, the method comprising:
  (a) obtaining physiological measurements from a patient via at least one physical sensor of a registered sensor device;
  (b) associating each measurement packet at the sensor device with a unique hardware device identity, a measurement timestamp, and a capture-session identifier;
  (c) generating a cryptographic authenticator at the sensor device over the measurement packet utilizing a hardware-secured key;
  (d) transmitting the authenticated measurement packet to a backend ingestion gateway, wherein the gateway validates the device identity, verifies packet freshness within a predetermined temporal window, and verifies physiological data integrity;
  (e) compiling validated measurement packets from the capture session into a clinical diagnostic report;
  (f) cryptographically binding the clinical diagnostic report to acquisition metadata comprising the device identity, capture-session identifier, and sensor cryptographic authenticator, forming a bound report artifact;
  (g) encrypting the bound report artifact using an authenticated symmetric encryption cipher and storing the resulting ciphertext on a content-addressed decentralized storage network to obtain a content identifier;
  (h) recording a verifiable cryptographic reference on a distributed ledger smart contract, the cryptographic reference encapsulating a digest of the bound report artifact, the content identifier, and a digest of the acquisition metadata;
  (i) upon receiving an authorized retrieval request, retrieving the ciphertext from the decentralized storage network, decrypting the ciphertext, and executing a dual-integrity verification comprising verifying the integrity of the retrieved report against the cryptographic reference on the distributed ledger, and verifying the association between the retrieved report and the authenticated acquisition metadata.

Claim 2 (Independent System Claim):
A cyber-physical decentralized patient record management system comprising:
  - an edge IoT sensor device comprising at least one physiological sensor, a processor, and a hardware key storage, configured to sample physiological signals, generate measurement packets bound to a device identity, timestamp, and session identifier, and cryptographically authenticate said packets at the edge;
  - a backend ingestion server configured to receive said packets, validate device identity, verify packet freshness against a server clock, enforce physiological validity bounds, compile validated packets into a diagnostic report, and embed an acquisition manifest into the report;
  - an encryption and decentralized storage module configured to encrypt the bound report via AES-256-GCM and pin the ciphertext to an IPFS content-addressed swarm;
  - a distributed ledger smart contract configured to record an immutable cryptographic seal comprising a file hash, an IPFS content identifier, and an acquisition session digest; and
  - a dual-integrity retrieval engine configured to decrypt retrieved records and independently verify storage integrity and sensor acquisition provenance prior to rendering.

Claim 3 (Dependent Claim - Freshness & Anti-Replay):
The method of Claim 1, wherein validating packet freshness comprises verifying that the difference between server reception time and measurement timestamp is less than or equal to 120 seconds, and rejecting packets containing duplicate sequence numbers or timestamps.

Claim 4 (Dependent Claim - Byte-Level Metadata Binding):
The method of Claim 1, wherein cryptographically binding the report to the acquisition metadata comprises embedding a binary acquisition manifest directly within the file structural metadata dictionary of a PDF/A or FHIR document.

Claim 5 (Independent Dual-Integrity Retrieval Claim):
A method for validating decentralized health records, comprising retrieving an encrypted file from a content-addressed storage network; decrypting the file using an authenticated cipher; computing a first hash of the decrypted file and verifying equality against a ledger-anchored file digest; extracting an embedded acquisition manifest from the decrypted file; computing a second hash of the acquisition manifest and verifying equality against a ledger-anchored session digest; and validating an edge hardware signature contained in the manifest against a registered device public key.


## Section 21. Have you conducted novelty/inventiveness search for your invention? If yes, what are the databases /references used by you? What are the search results?

Novelty and Inventiveness Search Summary:
A comprehensive prior art search was conducted across patent databases (USPTO, Google Patents, Espacenet, WIPO) and scientific repositories (IEEE Xplore, ACM Digital Library, PubMed, ScienceDirect) using keyword strings:
  - ('blockchain' OR 'distributed ledger') AND ('EHR' OR 'patient record') AND ('IoT' OR 'sensor') AND ('provenance' OR 'authentication') AND ('dual-integrity' OR 'metadata binding')

Findings: Existing patents and papers address blockchain-based access control (e.g., MedRec, Ancile, US20180096110A1) or off-chain cloud storage pointers. None disclose or suggest an architecture where: (1) edge IoT sensors cryptographically authenticate raw physiological packets with session-UUID binding; (2) backend freshness gating filters out replay attacks before compilation; (3) the resulting clinical report is byte-bound to the acquisition manifest; and (4) retrieval enforces dual-integrity validation verifying both file integrity and sensor silicon provenance.


## Section 22. Do you feel that a person of “average” skill (not-extraordinary skill) in your area of technology would have arrived at your invention with existing knowledge in public domain? If no, what could be the reasons for the same?

Non-Obviousness to a Person of Ordinary Skill in the Art (POSITA):
No, the invention would NOT be obvious to a person of ordinary skill in the art.

A POSITA in healthcare IT typically works with application-layer software, HL7/FHIR messaging, and cloud databases, treating medical files as given inputs. Conversely, a POSITA in embedded systems focuses purely on sensor sampling and local bus protocols (I2C, SPI), with no expertise in Merkle DAG content-addressing or blockchain consensus. The non-obvious inventive step lies in unifying these divergent domains to solve the cyber-physical trust boundary: realizing that decentralized storage integrity is meaningless without hardware-rooted acquisition binding, and inventing the dual-integrity retrieval protocol to enforce end-to-end provenance.


## Section 23. Kindly provide broad workable ranges for all parameters involved in the invention, including the working parameters and ranges applicable to each component utilized in the system.

Workable Technical Parameter Ranges:
1. Sensor Sampling Frequencies: 25 Hz to 1,000 Hz (Optimal for PPG/ECG: 100 Hz to 250 Hz).
2. Packet Transmission Interval: 100 ms to 5,000 ms (Optimal: 1,000 ms telemetry packet bursts).
3. Temporal Freshness Tolerance Window (Delta_t): 5 seconds to 300 seconds (Optimal: <= 120 seconds for cellular/Wi-Fi latency jitter).
4. Ingestion Gating Physiological Bounds:
   - Heart Rate: 30 BPM to 240 BPM (rejecting static constants).
   - Blood Oxygen (SpO2): 70% to 100%.
   - Biopotential ECG Amplitude: 0.1 mV to 5.0 mV (dynamic differential).
5. Archival Payload Size: 10 KB to 5 MB (Empirical limit: 1 MB optimal threshold to prevent international gateway timeouts).
6. Symmetric Encryption: AES-256-GCM (256-bit key, 96-bit IV, 128-bit authentication tag).
7. On-Chain Seal Size: 96 bytes to 160 bytes (Optimal: 128 bytes containing bytes32 fileHash, string ipfsCid, bytes32 sessionDigest, address owner).
8. Smart Contract Gas Consumption: 65,000 to 95,000 gas per notarization transaction (Observed mean: 75,214 gas).


## Section 24. Commercialization Data (at least a minimum of 2 companies must be provided and preferably up to 5)

Kindly give the names and complete addresses of five different companies which might be interested in the commercial manufacture of this technology.

1.
2.
3.
4.
5.
1. Philips Healthcare (Royal Philips)
   Address: Philips Center, Amstelplein 2, 1096 BC Amsterdam, Netherlands.
   Relevance: Market leader in hospital patient monitoring (IntelliVue) and remote ambulatory monitoring systems.

2. Medtronic plc
   Address: 20 Lower Hatch Street, Dublin 2, Ireland (U.S. HQ: 710 Medtronic Parkway, Minneapolis, MN 55432, USA).
   Relevance: Global leader in implantable and wearable cardiac telemetry (CareLink network) requiring tamper-proof data provenance.

3. GE HealthCare Technologies Inc.
   Address: 500 W Monroe St, Chicago, IL 60661, USA.
   Relevance: Major manufacturer of clinical monitoring, telemetry, and diagnostic cardiology infrastructure.

4. Epic Systems Corporation
   Address: 1979 Milky Way, Verona, WI 53593, USA.
   Relevance: Largest electronic health record (EHR) provider in the United States, managing records for over 250 million patients.

5. Oracle Health (Cerner Corporation)
   Address: 2300 Oracle Way, Austin, TX 78741, USA.
   Relevance: Major enterprise healthcare platform provider actively modernizing hospital cloud infrastructure and data interoperability.

Kindly also enclose a short marketing profile of the technology highlighting the advantages vis-à-vis the prior-art technologies in this area



Marketing Profile of the Technology:
DPRMS provides the world's first hardware-rooted, zero-trust clinical record provenance platform for remote patient monitoring (RPM) and decentralized clinical trials. While traditional cloud EHR systems cost millions in proprietary database licensing and remain vulnerable to insider tampering and silent data corruption, DPRMS eliminates data falsification at the sensor edge. By coupling low-cost IoT hardware authentication with decentralized IPFS storage and lightweight Ethereum notarization, the technology reduces archival infrastructure costs by 99.998% while providing cryptographic certainty required by FDA IoMT cybersecurity regulations, HIPAA, and medical malpractice liability underwriters.


## Section 25. Provide available data or information on market potential/size, adoption trends, industry analysis, and projected growth.

Market Potential, Industry Analysis, and Growth Projections:
1. Global Internet of Medical Things (IoMT) Market:
   - Valued at $50.2 Billion in 2024 and projected to reach $187.6 Billion by 2030, expanding at a Compound Annual Growth Rate (CAGR) of 24.5% (Grand View Research / MarketsandMarkets).
   - Key Driver: Exponential adoption of wearable remote cardiac monitors, pulse oximeters, and home telemetry kits post-pandemic.

2. Global Electronic Health Records (EHR) Market:
   - Valued at $31.5 Billion in 2024, projected to reach $47.2 Billion by 2030 (CAGR 6.9%).

3. Blockchain in Healthcare Market:
   - Valued at $3.1 Billion in 2024 and forecasted to surge to $25.6 Billion by 2030 (CAGR 42.1%).

4. Regulatory and Industry Drivers:
   - Strict FDA Cybersecurity Guidelines for Medical Devices (Section 524B of the FD&C Act) mandating proof of software/telemetry integrity.
   - Escalating healthcare cyberattacks (ransomware attacks up 140% in healthcare), creating urgent enterprise demand for decentralized, immutable, tamper-evident archival.


## Section 26. Please provide the names of the inventors involved in the Invention

Inventors Involved in the Invention:
1. Inventor 1:
   - Name: Abhinav S P
   - Register Number: 25BCE5381
   - Department: School of Computer Science and Engineering (SCOPE)
   - Institution: Vellore Institute of Technology (VIT), Chennai Campus, Tamil Nadu - 600127, India.
   - Email: abhinav.digitalworks@gmail.com / abhinav.sp2025@vitstudent.ac.in

2. Inventor 2:
   - Name: G Prathish Rajan
   - Register Number: 25BCE5367
   - Department: School of Computer Science and Engineering (SCOPE)
   - Institution: Vellore Institute of Technology (VIT), Chennai Campus, Tamil Nadu - 600127, India.

[Note: If any Faculty Guide / Supervisor from VIT Chennai is to be included as a co-inventor or mentor, their name and designation can be added here upon confirmation.]


## Section 27. User Information


### a. Who all are the potential users of the technology?

1. Hospitals, multi-specialty healthcare networks, and intensive care units (ICUs).
2. Remote patient monitoring (RPM) clinics managing chronic cardiac and pulmonary patients.
3. Clinical Research Organizations (CROs) and pharmaceutical companies conducting clinical drug trials.
4. Medical malpractice insurance underwriters and forensic medical audit agencies.
5. Individual patients requiring sovereign, tamper-proof ownership of lifetime diagnostic history.


### b. Age group of the user?

All age groups (pediatric to geriatric: 0 to 100 years). Specifically optimized for elderly patients requiring continuous at-home telemetry monitoring for cardiovascular disease.


### c. Expected benefits to the user?

1. Complete protection against diagnostic record tampering, alteration, or accidental loss.
2. 100% assurance that remote vitals reflect real physical sensor measurements rather than sensor malfunctions or fabricated values.
3. Seamless interoperability: patient can share cryptographically certified records with any specialist globally without institutional permission barriers.
4. Elimination of hospital lock-in: patients retain sovereign decentralized custody of health data.


### d. Cost advantage when compared to available solutions
1. 99.998% reduction in blockchain transaction costs compared to pure on-chain archival ($0.08 vs $3,500+ per megabyte record).
2. Drastic reduction in cloud storage and egress licensing fees by utilizing decentralized IPFS peer-to-peer storage.
3. Lower hardware cost: standard consumer-grade IoT microcontrollers (ESP32 at ~$4/unit) provide enterprise-grade cryptographic signing, eliminating expensive specialized hospital telemetry hubs ($5,000+ per unit).


## Section 28. What is Technology readiness level of your invention? (Tick the appropriate TRL)


## Section 29. Any additional notes or remarks.

Additional Technical and Legal Remarks:
1. Architectural Disclaimer Regarding Smart Contract Permissions:
It is explicitly clarified that the blockchain smart contract ('PatientRecord.sol') functions as an immutable, tamper-evident notarization registry and verifiable event log. Granular access permissions (e.g., patient-doctor consent grants, clinical role verification) are actively evaluated and enforced by the application/backend layer via cryptographically signed JWT tokens and database access policies. This design avoids unsustainable on-chain gas overhead for routine query operations while maintaining absolute cryptographic verifiability.

2. Ingestion Truthfulness Assurance:
The system strictly prohibits and rejects synthetic fallback placeholders (such as static 74 BPM pulse rate, 98% SpO2, or mathematical sine-wave P-Q-R-S-T approximations) from being recorded as authentic sensor measurements. Only hardware-authenticated telemetry passing strict freshness and physiological dynamic checks is accepted for archival.

3. Readiness for Patent Prosecution:
The experimental data, mathematical formulation, and architecture described herein represent an operational implementation ready for Indian Patent Office (IPO) and Patent Cooperation Treaty (PCT) filing.
