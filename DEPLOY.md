# Production Deployment Guide: Decentralized Patient Record System (DPRMS)

This guide provides click-by-click instructions to deploy the DPRMS full-stack application for 24/7 public cloud operation. Once deployed, the entire system runs independently in the cloud with zero dependence on your local machine.

---

## Architecture Overview

- **Frontend**: React + TypeScript (Vite) hosted on **Vercel** or **Render Static Site**.
- **Backend**: FastAPI (Python 3.11) hosted as a Web Service on **Render**.
- **Database**: Hosted PostgreSQL on **Neon**, **Render Postgres**, or **Supabase**.
- **File Storage**: Encrypted (AES-256-GCM) off-chain file storage via **Pinata IPFS**.
- **Blockchain**: Smart contract (`PatientRecord.sol`) deployed on **Ethereum Sepolia Testnet** for anchoring IPFS CIDs and SHA-256 integrity hashes.

---

## Required Environment Variables (Names Only)

### Backend (Render Web Service)
| Variable Name | Description |
|---|---|
| `ENVIRONMENT` | Must be set to `production`. Rejects SQLite fallback and missing critical configs. |
| `DATABASE_URL` | Hosted PostgreSQL connection URI (e.g. `postgresql://...`). |
| `JWT_SECRET_KEY` | Secret key for signing authentication JWT tokens (min 16 characters). |
| `ENCRYPTION_KEY` | 32-byte Base64-encoded key for AES-256-GCM client file encryption. |
| `SEPOLIA_RPC_URL` | Ethereum Sepolia testnet RPC URL (e.g. from Alchemy or Infura). |
| `PRIVATE_KEY` | Throwaway Ethereum wallet private key (hex) funded with Sepolia ETH. |
| `CONTRACT_ADDRESS` | Deployed `PatientRecord.sol` address on Sepolia. |
| `PINATA_API_KEY` | Pinata IPFS API Key. |
| `PINATA_API_SECRET` | Pinata IPFS API Secret. |
| `PINATA_GATEWAY` | Pinata Gateway URL (default: `https://gateway.pinata.cloud`). |
| `FRONTEND_URL` | Public URL of the deployed frontend (e.g. `https://your-app.vercel.app`). No wildcard `*`. |
| `ADMIN_EMAIL` | (Optional) Automated administrator email bootstrap (e.g. `admin@yourdomain.com`). |
| `ADMIN_PASSWORD` | (Optional) Strong password for the administrator account to access `/admin`. |
| `MAX_DAILY_TRANSACTIONS` | (Optional) Cap on daily on-chain anchoring transactions (default: `50`). |


### Frontend (Vercel or Render Static Site)
| Variable Name | Description |
|---|---|
| `VITE_API_URL` | Public base URL of the deployed Render backend (e.g. `https://dprms-backend.onrender.com`). |

---

## Step 0: Deploy Smart Contract to Sepolia (If Starting from Scratch)

If you are setting up a fresh deployment or deploying a new smart contract instance:

1. Navigate to the `blockchain/` directory:
   ```bash
   cd blockchain
   npm install
   ```
2. Ensure `blockchain/.env` contains your funded Sepolia wallet private key and RPC URL:
   ```env
   SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
   PRIVATE_KEY=your_throwaway_wallet_private_key_hex
   ```
   *(Note: The wallet must have a small amount of Sepolia ETH from a faucet, e.g. https://sepoliafaucet.com or Alchemy Faucet).*

3. Compile the Solidity contract:
   ```bash
   npx hardhat compile
   ```
4. Deploy the contract to Sepolia:
   ```bash
   npx hardhat run scripts/deploy.js --network sepolia
   ```
5. Note the deployment output. It will display:
   ```
   Deploying PatientRecord contract to sepolia...
   Deployer address: 0x541509676ad712d4C4FBbe8638F710567D87998F
   Deployment transaction hash: 0x41de643c63fef9c966a1782bb42959c1a8c0c5be1842fd572d759c2852b0e8b8
   PatientRecord deployed to: 0xabaE36eaC3367310a393bdE2fe26690C65bB5f02
   Verify on Etherscan: https://sepolia.etherscan.io/address/0xabaE36eaC3367310a393bdE2fe26690C65bB5f02
   ```
6. Copy the deployed contract address and set it as `CONTRACT_ADDRESS` in your backend configuration.

---

## Step 1: Provision Hosted PostgreSQL Database

You can use **Neon.tech** (recommended for serverless Postgres with connection pooling) or **Render PostgreSQL**.

### Option A: Neon.tech (Recommended)
1. Go to [https://neon.tech](https://neon.tech) and log in or create an account.
2. Click **Create Project**.
3. Name your project (e.g., `dprms-production`).
4. **IMPORTANT**: Select the cloud region **AWS ap-southeast-1 (Singapore)** to match your Render backend region and minimize latency.
5. Ensure the database is a **FRESH Neon project** or an emptied one with zero test rows.
6. On the project dashboard, locate the **Connection Details** card.
7. Ensure the dropdown is set to **Pooled connection** and **Postgres**.
8. Copy the connection string. It will look like:
   `postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
   *(Save this URI for the backend `DATABASE_URL`)*.

---

## Step 2: Deploy Backend on Render

1. Log in to [https://render.com](https://render.com).
2. Click **New +** in the top navigation and select **Web Service**.
3. Connect your GitHub repository (`decentralized_patient_record_system`).
4. Select the branch: `feature/ipfs-storage` (or `main` if merged).
5. Fill in the service configuration details:
   - **Name**: `dprms-backend`
   - **Region**: **Singapore** *(matches your Neon database AWS ap-southeast-1 region)*
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
6. Click **Advanced** and set:
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: `Yes`
7. In the **Environment Variables** section, add each key:
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: *(Paste your fresh production Neon pooled connection URI)*
   - `JWT_SECRET_KEY`: *(Generate a NEW secret using the command below)*
   - `ENCRYPTION_KEY`: *(Generate a NEW 32-byte key using the command below)*
   - `ADMIN_EMAIL`: *(Your production system administrator email, e.g. `admin@yourdomain.com`)*
   - `ADMIN_PASSWORD`: *(Generate a NEW strong password for production admin dashboard)*
   - `SEPOLIA_RPC_URL`: *(Your Alchemy or Infura Sepolia endpoint)*
   - `PRIVATE_KEY`: *(Your throwaway Sepolia wallet private key funded with testnet ETH)*
   - `CONTRACT_ADDRESS`: *(Your deployed PatientRecord contract address)*
   - `PINATA_API_KEY`: *(Your Pinata API Key)*
   - `PINATA_API_SECRET`: *(Your Pinata API Secret)*
   - `PINATA_GATEWAY`: `https://gateway.pinata.cloud`
   - `MAX_DAILY_TRANSACTIONS`: `50`
   - `FRONTEND_URL`: *(Temporarily enter `http://localhost:5173` or your planned Vercel URL, then update in Step 4)*
8. Click **Deploy Web Service**.
9. Wait 2-3 minutes for Render to build and start the service. Once deployed, note your backend public URL:
   `https://dprms-backend.onrender.com`
10. Test health by opening: `https://dprms-backend.onrender.com/health` in your browser. Both database and Pinata should report connected.

> **Helper Commands to Generate Production Secrets (Run in Terminal):**
>
> *Security Note: `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_PASSWORD`, and `DATABASE_URL` in production MUST all be NEW values that have never been used in development or testing. Ensure `ENCRYPTION_KEY` is securely backed up; if this key is lost, all previously encrypted files pinned to IPFS cannot be decrypted.*
>
> ```bash
> # Generate JWT_SECRET_KEY (32-byte hex)
> python3 -c "import secrets; print(secrets.token_hex(32))"
>
> # Generate ENCRYPTION_KEY (32-byte base64)
> python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
>
> # Generate ADMIN_PASSWORD (secure 16-character string)
> python3 -c "import secrets; print(secrets.token_urlsafe(16))"
> ```


---

## Step 3: Deploy Frontend

You can deploy the Vite React frontend on **Vercel** (recommended) or as a **Render Static Site**.

### Option A: Deploy on Vercel (Recommended)
1. Log in to [https://vercel.com](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository (`decentralized_patient_record_system`).
4. Configure project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Expand **Environment Variables**:
   - Key: `VITE_API_URL`
   - Value: `https://dprms-backend.onrender.com` *(Replace with your actual Render backend URL without trailing slash)*
6. Click **Deploy**.
7. Once deployed, copy your public Vercel production URL:
   `https://your-project.vercel.app`

### Option B: Deploy on Render Static Site
1. In your Render Dashboard, click **New +** → **Static Site**.
2. Connect your GitHub repository.
3. Configure settings:
   - **Name**: `dprms-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Under **Environment Variables**:
   - `VITE_API_URL`: `https://dprms-backend.onrender.com`
5. Under **Redirects/Rewrites**:
   - Add Rewrite: `/*` -> `/index.html` (Status: `Rewrite`) to support SPA client routing.
6. Click **Create Static Site**.

---

## Step 4: Finalize CORS on Render Backend

1. Return to your Render Dashboard and open `dprms-backend`.
2. Go to **Environment** tab.
3. Update `FRONTEND_URL` with your exact frontend URL (e.g. `https://your-project.vercel.app`).
4. Click **Save Changes**. Render will automatically trigger a zero-downtime redeploy.

---

## Post-Deploy Validation Checklist

Perform this verification from a phone or non-local device (with your Mac closed/asleep):

- [ ] **1. Public Accessibility**: Open the frontend URL on a smartphone using mobile cellular data (Wi-Fi off). Confirm the page loads instantly with SSL.
- [ ] **2. Demo Disclaimer Banner**: Confirm the yellow banner displays prominently:
  *"Demo project on a test network. Do not upload real patient data."*
- [ ] **3. Service Health**: In a separate browser tab, navigate to `https://<backend-url>/health`. Confirm:
  ```json
  {
    "status": "healthy",
    "database": { "connected": true, "detail": "connected" },
    "pinata": { "configured": true, "authenticated": true, "status_code": 200, "message": "Connected" },
    "database_active": true,
    "ipfs_active": true
  }
  ```
- [ ] **4. Registration**: Register a new patient account (e.g. `patient_live@example.com`). Confirm identity is created in PostgreSQL and auto-logs in.
- [ ] **5. Upload Medical Record**:
  - Upload a test medical report, prescription, or image file (PDF, PNG, JPG).
  - Verify that upload completes and the record appears in the list.
  - Check that an IPFS CID (starts with `Qm` or `bafy`) and a Sepolia transaction hash (`0x...`) are present on the record card.
- [ ] **6. Download with Integrity Verification**:
  - Click **Download** on the newly created record.
  - Confirm the decrypted file downloads properly to your phone/browser.
  - Verify the green **Integrity Verified** badge displays, confirming that the decrypted file's SHA-256 hash matches the on-chain hash anchored on Sepolia.
- [ ] **7. Statelessness / Persistence Verification**:
  - In the Render dashboard, click **Manual Deploy** → **Deploy latest commit** (or restart the service). This restarts the container with a clean, empty disk.
  - Refresh the patient dashboard on your phone.
  - Confirm the user session, patient records, IPFS CIDs, and blockchain hashes are still completely intact.
- [ ] **8. Doctor Verification Workflow**:
  - Register a new doctor account on the frontend.
  - Notice the doctor account initially starts in `pending` status and cannot access or upload records.
  - Log in as the administrator using `ADMIN_EMAIL` and `ADMIN_PASSWORD` at `/admin`.
  - Navigate to the Doctor Verification tab, review the pending doctor registration, and click **Verify Doctor**.
  - Log back in as the verified doctor and confirm access to patient records and IPFS uploads.

