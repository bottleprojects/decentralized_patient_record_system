# DPRMS EXPERIMENTAL VALIDATION PLAN
## Protocols for Biomedical Sensor, Cryptographic, and Distributed Storage Evaluation

### 1. Purpose and Scope
This experimental validation plan establishes standardized, reproducible test protocols to evaluate the accuracy, latency, security, and gas economics of the Decentralized Patient Record Management System (DPRMS).

---

### 2. Experimental Protocols

#### Protocol A: Physical Biomedical Sensor Verification
- **Equipment Required:** Fluke ProSim 8 Vital Signs Simulator, Tektronix TBS1104B Digital Storage Oscilloscope, ESP32 DevKit V1, MAX30102 sensor breakout, AD8232 ECG breakout.
- **Procedure:**
  1. Connect Fluke ProSim 8 ECG output to AD8232 chest lead terminals (RA, LA, RL).
  2. Configure simulator for 60, 80, 100, 120, and 160 BPM normal sinus rhythm.
  3. Measure ESP32 ADC1 sampling jitter using hardware timer interrupts.
  4. Compare simulator output against ESP32 buffered waveforms.
  5. Repeat with Fluke optical finger simulator for SpO2 calibration (80%, 90%, 95%, 98%, 100%).
- **Acceptance Criteria:**
  - Heart Rate error <= +- 2 BPM.
  - SpO2 error <= +- 1.5%.
  - Zero dropped samples over 8-second bounded capture window (4000 samples +- 0).

#### Protocol B: Cryptographic Anti-Replay & Freshness Validation
- **Procedure:**
  1. Generate 1,000 valid telemetry packets with monotonic sequence counters.
  2. Inject 100 duplicate packets with sequence_number <= last_seen.
  3. Inject 100 stale packets with timestamp drift > 10.0 seconds.
  4. Inject 100 packets with modified payload bytes (tampered SpO2 or HR).
- **Acceptance Criteria:**
  - 100% of duplicate packets rejected with HTTP 400.
  - 100% of stale packets rejected with HTTP 400.
  - 100% of tampered packets rejected with HTTP 401 Unauthorized.

#### Protocol C: Distributed Storage & Blockchain Gas Economics
- **Procedure:**
  1. Upload clinical records across payload size tiers: 100 KB, 500 KB, 1 MB, 2.5 MB, and 5 MB.
  2. Measure time-to-first-byte (TTFB), total upload duration, and IPFS gateway resolution latency across unthrottled and Fast 4G conditions.
  3. Record exact Ethereum EVM gas usage for `storeIPFSRecordWithProvenance`.
- **Acceptance Criteria:**
  - Smart contract gas consumption <= 95,000 gas per transaction.
  - Zero on-chain storage of plaintext protected health information (PHI).
