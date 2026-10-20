# DPRMS Real-World Performance Benchmark Suite

This benchmark suite measures the real-world, end-to-end performance and reliability of the Decentralized Patient Record Management System (DPRMS) by automating real Chromium browser instances via Playwright under authentic network conditions.

It provides an empirical comparison between:
- **Site A ("Supabase Storage")**: Traditional centralized cloud object storage deployed on Railway with PostgreSQL.
- **Site B ("IPFS via Pinata")**: Decentralized off-chain content-addressed storage (AES-256-GCM encrypted) with Sepolia blockchain hash anchoring deployed on Vercel + Render with Neon PostgreSQL.

---

## 1. Directory Structure

```text
benchmark/
├── .env.example             # Template for test environment variables
├── .env                     # Local credentials (git-ignored)
├── dummy_files/             # Generated synthetic dummy files (100KB, 1MB, 5MB)
│   ├── synthetic_100kb.pdf
│   ├── synthetic_1mb.pdf
│   └── synthetic_5mb.pdf
├── run_browser_benchmark.py # Automated browser execution script (Playwright)
├── make_graphs.py           # Matplotlib visualization and summary generator
├── results.csv              # Raw run-by-run experimental observations
├── summary_table.csv        # Aggregated statistics (median, mean, p95, failure rate)
├── report_output/           # Generated 200 DPI PNG publication graphs
├── REPORT_SUMMARY.md        # Comprehensive findings and comparative evaluation
└── README.md                # Usage and reproduction guide (this document)
```

---

## 2. Prerequisites & Setup

### A. Python Environment
Python 3.11+ is recommended. Install required packages and Chromium browser binaries:

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install playwright matplotlib pandas numpy python-dotenv

# 3. Install Playwright Chromium browser
playwright install chromium
```

### B. Configure Environment Variables
Copy `.env.example` to `.env` in the `benchmark/` folder:

```bash
cp benchmark/.env.example benchmark/.env
```

Ensure the variables match your deployed targets:
```env
SITE_A_URL=https://dprms.up.railway.app
SITE_A_BACKEND_URL=https://backend-production-386b.up.railway.app
SITE_A_EMAIL=benchmark_patient_a@synthmed.org
SITE_A_PASSWORD=YourPasswordHere

SITE_B_URL=https://dprmss.vercel.app
SITE_B_BACKEND_URL=https://dprms-backend.onrender.com
SITE_B_EMAIL=benchmark_patient_b@synthmed.org
SITE_B_PASSWORD=YourPasswordHere

# Optional run count override (default: 10)
BENCHMARK_RUNS=10
```

---

## 3. Running the Benchmark

### Step 1: Run Automated Real Browser Tests
The benchmark alternates sites run-by-run (`A, B, B, A, ...`), tests across file sizes (100 KB, 1 MB, 5 MB), and emulates network profiles via Chrome DevTools Protocol (`No throttling` and `Fast 4G`).

```bash
python3 benchmark/run_browser_benchmark.py
```

*Results are streamed directly to `benchmark/results.csv` row-by-row.*

### Step 2: Generate Graphs and Summary Tables
Process the real measurements into high-resolution charts and aggregated CSV tables:

```bash
python3 benchmark/make_graphs.py
```

Outputs generated:
- `benchmark/summary_table.csv`
- `benchmark/report_output/upload_time_no_throttling.png`
- `benchmark/report_output/upload_time_fast_4g.png`
- `benchmark/report_output/retrieval_cold_warm_no_throttling.png`
- `benchmark/report_output/retrieval_cold_warm_fast_4g.png`
- `benchmark/report_output/page_load_comparison.png`
- `benchmark/report_output/time_vs_size_lines_no_throttling.png`
- `benchmark/report_output/time_vs_size_lines_fast_4g.png`
- `benchmark/report_output/upload_consistency_boxplot.png`
- `benchmark/report_output/failure_rate_comparison.png`
- `benchmark/report_output/backend_cold_start.png`

---

## 4. Manual Measurement Mode (`?debug=1`)

To test performance interactively from mobile devices or laptops:
1. Append `?debug=1` to any deployed URL:
   - `https://dprmss.vercel.app/patient?debug=1`
   - `https://dprms.up.railway.app/login?debug=1`
2. A floating, real-time **DPRMS Timing Debug** overlay appears in the bottom right corner showing:
   - DNS, TCP, and TTFB latencies
   - Navigation timings (FCP, LCP, total page load)
   - Real-time client-measured Upload & Download durations
3. All metrics are also structured and emitted to the browser developer console (`console.table`).
