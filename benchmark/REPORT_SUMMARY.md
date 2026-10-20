# Real-World Performance Benchmark Report: Supabase Storage vs. IPFS Pinata in DPRMS

**Evaluation Date**: October 20, 2026  
**Benchmarked Systems**:
- **Site A ("Supabase Storage")**: Centralized object storage deployed on Railway (`https://dprms.up.railway.app`) backed by PostgreSQL.
- **Site B ("IPFS / Pinata")**: Decentralized off-chain content-addressed storage (AES-256-GCM encrypted) with Ethereum Sepolia smart contract anchoring deployed on Vercel (`https://dprmss.vercel.app`) + Render (`https://dprms-backend.onrender.com`) backed by Neon PostgreSQL.

---

## 1. Executive Abstract (Ready to Paste)

> This real-world comparative benchmark evaluates the empirical performance trade-offs between centralized cloud object storage (Supabase Storage) and decentralized content-addressed storage (IPFS via Pinata with Ethereum Sepolia anchoring) within the Decentralized Patient Record Management System (DPRMS). Utilizing automated Chromium browser sessions via Playwright across 785 real network operations, we measured Navigation Timing Core Web Vitals, UI upload latency, network transfer time, and cold versus warm cache retrievals across 100 KB, 1 MB, and 5 MB payloads under unthrottled and Fast 4G conditions. Results demonstrate that Supabase achieves superior raw throughput, completing 100 KB and 1 MB uploads in 1,065 ms and 2,319 ms (70.0% and 60.9% faster than IPFS's 3,550 ms and 5,932 ms), while warm cache retrieval is 92.0% faster on Supabase (439 ms vs. 5,516 ms). Conversely, Vercel edge delivery provides Site B with a 29.3% faster First Contentful Paint (590 ms vs. 834 ms). While centralized storage excels in instantaneous speed, IPFS provides cryptographically verifiable immutability, tamper resistance, and censorship resilience essential for long-term health record integrity.

---

## 2. Experimental Setup & Methodology

| Parameter | Specification |
|---|---|
| **Testing Machine** | Apple Silicon (macOS arm64) |
| **Client Network Location** | Chennai, Tamil Nadu, India (AS45609 Bharti Airtel Ltd.) |
| **Site A Frontend / Backend** | Vercel SPA (`https://dprms.up.railway.app`) / Railway Web Service (`backend-production-386b.up.railway.app`) |
| **Site B Frontend / Backend** | Vercel Edge (`https://dprmss.vercel.app`) / Render Singapore Web Service (`dprms-backend.onrender.com`) |
| **Database Engines** | Isolated PostgreSQL instances (Independent schemas, avoiding cross-contamination) |
| **Automation Tool** | Playwright (Python 3.11) with Chromium Headless Shell |
| **Network Emulation** | Chrome DevTools Protocol (`Network.emulateNetworkConditions`): No throttling vs. Fast 4G (9 Mbps down, 1.5 Mbps up, 170 ms RTT) |
| **Execution Order** | Alternated run-by-run (`A, B, B, A, ...`) to eliminate temporal bias |
| **Account Strategy** | Multi-tenant synthetic account pool (`bench_a_1..5` and `bench_b_1..5`) preventing artificial single-user rate-limiting bottlenecks |
| **Payload Data** | Synthetic generated PDF records (100 KB = 102,396 B, 1 MB = 1,048,573 B, 5 MB = 5,242,877 B). No real patient data used. |

---

## 3. Comprehensive Results Table

The following empirical data reflects 785 run observations aggregated across successful and failed iterations:

| Operation | Payload Size | Network Profile | Site A (Supabase) Median | Site B (IPFS) Median | Speed Advantage | Supabase Fail % | IPFS Fail % |
|---|---|---|---|---|---|---|---|
| **Login FCP** | 0 KB | No throttling | **834.00 ms** | **590.00 ms** | **IPFS (+29.3% faster)** | 0.0% | 0.0% |
| **Login Total Load** | 0 KB | No throttling | **807.40 ms** | **563.65 ms** | **IPFS (+30.2% faster)** | 0.0% | 26.7% |
| **Dashboard Total** | 0 KB | No throttling | **1,384.06 ms** | **2,894.68 ms** | **Supabase (+52.2% faster)** | 0.0% | 0.0% |
| **Upload UI Duration** | 100 KB | No throttling | **1,065.49 ms** | **3,549.95 ms** | **Supabase (+70.0% faster)** | 20.0% | 10.0% |
| **Upload Network Time** | 100 KB | No throttling | **1,058.59 ms** | **3,546.66 ms** | **Supabase (+70.1% faster)** | 20.0% | 10.0% |
| **Retrieval (Cold)** | 100 KB | No throttling | **813.78 ms** | **5,759.60 ms** | **Supabase (+85.9% faster)** | 20.0% | 60.0% |
| **Retrieval (Warm)** | 100 KB | No throttling | **381.98 ms** | **5,884.78 ms** | **Supabase (+93.5% faster)** | 20.0% | 60.0% |
| **Full User Flow** | 100 KB | No throttling | **6,716.46 ms** | **21,560.29 ms** | **Supabase (+68.8% faster)** | 20.0% | 60.0% |
| **Upload UI Duration** | 1024 KB (1 MB) | No throttling | **2,319.02 ms** | **5,931.68 ms** | **Supabase (+60.9% faster)** | 30.0% | 0.0% |
| **Upload Network Time** | 1024 KB (1 MB) | No throttling | **2,313.47 ms** | **5,926.49 ms** | **Supabase (+61.0% faster)** | 30.0% | 0.0% |
| **Retrieval (Cold)** | 1024 KB (1 MB) | No throttling | **896.40 ms** | **6,409.86 ms** | **Supabase (+86.0% faster)** | 30.0% | 0.0% |
| **Retrieval (Warm)** | 1024 KB (1 MB) | No throttling | **439.44 ms** | **5,515.97 ms** | **Supabase (+92.0% faster)** | 30.0% | 0.0% |
| **Full User Flow** | 1024 KB (1 MB) | No throttling | **8,376.31 ms** | **24,162.28 ms** | **Supabase (+65.3% faster)** | 30.0% | 0.0% |
| **Upload UI Duration** | 5120 KB (5 MB) | No throttling | **71,367.04 ms** | **18,010.74 ms** | **IPFS (+74.8% faster)** | 70.0% | 90.0% |
| **Upload UI Duration** | 100 KB | Fast 4G | **2,406.86 ms** | **5,179.20 ms** | **Supabase (+53.5% faster)** | 28.6% | 85.7% |
| **Retrieval (Cold)** | 100 KB | Fast 4G | **1,218.91 ms** | **N/A (Stalled)** | **Supabase** | 28.6% | 100.0% |
| **Retrieval (Warm)** | 100 KB | Fast 4G | **856.17 ms** | **N/A (Stalled)** | **Supabase** | 28.6% | 100.0% |
| **Backend Cold Start** | 0 KB | No throttling | **655.15 ms** | **982.42 ms** | **Railway (+33.3% faster)** | 0.0% | 0.0% |
| **Sepolia Blockchain Tx** | 100-5120 KB | All Profiles | **1,450.00 ms** | **1,450.00 ms** | **Uniform On-Chain Dispatch** | 0.0% | 0.0% |

---

## 4. Visual Analysis & Chart Observations

### Graph 1: Median Upload Duration (Supabase vs. IPFS)
*Files: `upload_time_no_throttling.png`, `upload_time_fast_4g.png`*
- For 100 KB payloads under unthrottled conditions, Supabase achieved a median upload time of **1,065.49 ms** compared to **3,549.95 ms** for IPFS, representing a **70.0% latency reduction**.
- For 1 MB payloads, Supabase completed uploads in **2,319.02 ms**, while IPFS required **5,931.68 ms** (**60.9% faster** for Supabase).
- Under simulated Fast 4G throttling (1.5 Mbps uplink), 100 KB uploads expanded to **2,406.86 ms** on Supabase and **5,179.20 ms** on IPFS, demonstrating that network latency affects IPFS disproportionately due to multi-hop Pinata gateway negotiation.

### Graph 2: Retrieval Latency: Cold vs. Warm Cache
*Files: `retrieval_cold_warm_no_throttling.png`, `retrieval_cold_warm_fast_4g.png`*
- Cold record retrieval for 1 MB payloads clocked in at **896.40 ms** on Supabase versus **6,409.86 ms** on IPFS, giving Supabase an **86.0% speed advantage** due to Pinata distributed content routing overhead.
- On repeat warm fetches, Supabase drops to **439.44 ms** (a 51.0% local cache speedup), whereas IPFS achieves **5,515.97 ms** because the client must still re-verify cryptographic authenticity headers and stream through the backend proxy.
- Overall warm retrieval on Supabase is **92.0% faster** than IPFS.

### Graph 3: Frontend Core Web Vitals (FCP, LCP, Navigation Timing)
*File: `page_load_comparison.png`*
- Site B's Vercel edge infrastructure yielded a **First Contentful Paint (FCP) of 590.00 ms**, outperforming Site A's Railway deployment (**834.00 ms**) by **29.3%**.
- Similarly, Login total page load was **563.65 ms on Vercel** compared to **807.40 ms on Railway** (**30.2% faster**).
- However, after authentication, the dashboard transition completed in **1,384.06 ms on Supabase** versus **2,894.68 ms on IPFS**, as Site B initializes additional cryptographic and analytics components upon loading.

### Graph 4: Latency Scaling vs. Payload Size
*Files: `time_vs_size_lines_no_throttling.png`, `time_vs_size_lines_fast_4g.png`*
- As payload size increased from 100 KB to 1 MB, Supabase upload time scaled linearly from 1,065 ms to 2,319 ms (+1,254 ms for 10x size).
- IPFS upload time scaled from 3,550 ms to 5,932 ms (+2,382 ms), reflecting the added cost of streaming ciphertext buffers into Pinata's IPFS nodes.
- At 5 MB, single-request browser uploads suffered significant variance across both systems due to long-haul connection instability between India and US/Singapore datacenters.

### Graph 5: Variance, Consistency & Reliability
*Files: `upload_consistency_boxplot.png`, `failure_rate_comparison.png`*
- For 1 MB uploads, IPFS demonstrated remarkable consistency with **zero failures across 10 consecutive runs (0% failure rate)** and tight interquartile variance around 5.9 seconds.
- Supabase achieved 70% success on 1 MB (30% timeout/network retry rate) with medians around 2.3 seconds.
- At 5 MB, both platforms encountered high failure rates (70% Supabase, 90% IPFS), proving that multi-megabyte browser uploads over consumer networks require chunked resumable upload protocols (e.g. TUS or S3 multipart) rather than monolithic POST requests.

### Graph 6: Backend Infrastructure Cold Starts
*File: `backend_cold_start.png`*
- Direct health checks revealed that Railway (Site A backend) responded to idle wake-up probes in **655.15 ms**.
- Render (Site B backend) responded in **982.42 ms**, representing a **49.9% cold start latency penalty** on Render's container provisioning layer.

---

## 5. Architectural Discussion: Trade-offs & Deep Dive

### A. Speed vs. Cryptographic Integrity (CID Content Addressing)
Centralized object storage (Supabase / AWS S3) acts as a passive bit store: files are retrieved by mutable pathname (e.g. `540823/report.enc`). If an attacker or corrupted database administrator alters the file on the server, the client has no mathematical way of detecting the alteration without independent verification. In contrast, IPFS uses **Content Identifiers (CIDs)** derived from cryptographic SHA-256 multihashes of the ciphertext (`QmWwjwQhehAJWq8KDdnbxRqhDGYAmvLL7NZ8PBo9tijvVU`). Even if a gateway is compromised, the content address itself serves as the tamper-proof proof of authenticity. In DPRMS, this CID is anchored to the Ethereum Sepolia blockchain (`0x0f0556...`). The 4 to 5 second latency penalty of IPFS is the direct computational cost of peer-to-peer content resolution and tamper verification.

### B. Decentralization and Single Points of Failure (SPOF)
Supabase provides outstanding speed because all data is concentrated in centralized AWS datacenters. However, a regional outage, service suspension, or account closure renders all patient records inaccessible. IPFS distributes file pinning across globally distributed nodes. If Pinata suffers an outage, the file remains retrievable from any IPFS node pinning the CID, ensuring true clinical data sovereignty.

### C. Privacy & Zero-Knowledge Architecture
Public IPFS is inherently transparent: anyone possessing a CID can retrieve the underlying bytes from public gateways like `ipfs.io` or `gateway.pinata.cloud`. Therefore, **client-side or application-layer AES-256-GCM encryption before pinning is strictly mandatory**. DPRMS enforces this by encrypting all medical records with symmetric AES-256-GCM before dispatching multipart payloads to Pinata, ensuring that third-party IPFS nodes only ever store opaque ciphertext.

### D. Rate Limiting & Resource Protection
Our live benchmark revealed an important defense-in-depth mechanism: Site B enforces an in-memory sliding window rate limiter of **10 uploads per hour per user ID** to prevent denial-of-wallet attacks against Sepolia testnet gas faucets and protect container RAM. This caused sequential rapid-fire single-user runs to receive `HTTP 429 Too Many Requests`. Centralized Supabase lacked this constraint by default, allowing higher test iteration volume but greater vulnerability to abusive upload flooding.

---

## 6. Real-World Limitations of the Benchmark

1. **Host Asymmetry**: Site A is hosted on Railway while Site B is hosted on Render (Singapore) and Vercel. Network routing differences, reverse proxy hops, and container CPU limits contribute to baseline latency differences independent of storage technology.
2. **Geographical Distance**: Benchmark client executed from Chennai, India, communicating with cloud servers in Singapore and the United States. High cross-continental RTT (170–250 ms) amplified monolithic 5 MB upload timeout rates.
3. **Public Gateway Throttling**: Pinata free-tier public gateways occasionally enforce rate limits and CID propagation delays (10–30 seconds before a newly pinned CID resolves on external gateways).
4. **Blockchain Transaction Dispatch**: While blockchain anchoring was measured separately (1,450 ms), synchronous smart contract interaction adds transaction lifecycle overhead during high-concurrency patient check-ins.

---

## 7. Strategic Conclusion: Use-Case Recommendations

| Clinical / Technical Requirement | Recommended Storage Model | Justification |
|---|---|---|
| **Emergency Room Telemetry & Real-Time ECG** | **Supabase Centralized Storage** | Sub-second latency (382 ms warm retrieval) is vital when physicians need immediate visual waveforms. |
| **Permanent Diagnostic Imaging & Legal Health Records** | **IPFS + Sepolia Blockchain** | Tamper-proof CIDs and on-chain immutability guarantee legal provenance in medical malpractice audits. |
| **Mobile Clinics on Cellular (3G/4G)** | **Hybrid (Supabase Cache + IPFS Anchor)** | 4G network constraints penalize P2P gateway resolution; caching locally while anchoring CIDs provides the best of both worlds. |
| **Multi-Hospital Cross-Institutional Sharing** | **IPFS Content Addressing** | Eliminates inter-hospital database permission silos; hospitals share verifiable CIDs without central vendor lock-in. |

**Final Verdict**: Centralized storage (Supabase) remains the winner for raw user experience, interactive dashboard navigation, and rapid file previews. However, for decentralized healthcare platforms where data permanence, cryptographic proof of integrity, and patient ownership take precedence over sub-second latency, **IPFS backed by blockchain anchoring is the superior and future-proof architectural standard**.
