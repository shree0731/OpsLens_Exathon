# OpsLens Deployment & Run Guide

Comprehensive instructions for deploying and running **OpsLens** on local development machines, cloud virtual machines, or container environments.

---

## 1. Prerequisites

Before starting, ensure your host meets the following requirements:

* **Operating System:** Windows 10/11 (PowerShell), macOS (12+), or Linux (Ubuntu 20.04+)
* **Python:** Version 3.10 or higher (`python --version`)
* **Node.js:** Version 18.0 or higher (`node --version`) and `npm`
* **Exasol Database:** Exasol Personal Edition 2026.x or Exasol Docker container running on port `8563`
* **Git:** Version 2.30+

---

## 2. Exasol Database Setup

### Local Installation (Windows via Exasol Launcher)
1. Verify Exasol deployment status:
   ```powershell
   exasol deployment list
   # or inspect default deployment:
   exasol deployment status default
   ```
2. Verify port connectivity to Exasol:
   ```powershell
   Test-NetConnection 127.0.0.1 -Port 8563
   ```
   *(Ensure `TcpTestSucceeded : True`)*

### Docker / Linux / macOS Alternative
If running Exasol via Docker:
```bash
docker run --name exasoldb -p 8563:8563 -d exasol/docker-db:latest
```

---

## 3. Environment Configuration (`.env`)

OpsLens strictly requires database credentials to reside in `.env`. Never commit `.env` to version control.

1. Copy the template:
   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env

   # POSIX (macOS / Linux)
   cp .env.example .env
   ```

2. Open `.env` and configure your cluster credentials:
   ```ini
   # Exasol Personal Edition Connection
   EXA_HOST=127.0.0.1
   EXA_PORT=8563
   EXA_USER=sys
   EXA_PASSWORD=<your_exasol_sys_password>
   EXA_SCHEMA=OPSLENS
   EXA_VERIFY_CERT=false
   EXA_ENCRYPTION=true

   # Optional Integrations
   LLM_PROVIDER=gemini
   LLM_API_KEY=
   SLACK_WEBHOOK_URL=
   ```

3. Verify `.env` is ignored by Git:
   ```bash
   git status --ignored
   # Should list '!! .env' under Ignored files
   ```

---

## 4. Step-by-Step Execution (Windows Primary)

### Step 4.1: Install Backend Dependencies
```powershell
# From the repository root
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 4.2: Verify Connectivity
Run the connectivity diagnostic to confirm credentials and Exasol responsiveness:
```powershell
python -m backend.connectivity_test
```
*Expected Output:*
```
============================================================
 STATUS: SUCCESS - Exasol is fully responsive.
============================================================
```

### Step 4.3: Initialize Schema & Ingest Baseline Workload
Run the idempotent data generator to create schema `OPSLENS`, copy reference records, and seed initial baselines:
```powershell
python -m data_generator.main
```
*(This loads 30,000 orders, 120,515 lineitems, 108,000 hourly energy readings, 10,960 weather records, marts, and 60 days of simulated nightly pipeline execution logs into `OPSLENS` without modifying reference schemas).*

### Step 4.4: Launch the Backend API
Start FastAPI on port `8000`:
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
* Interactive API documentation is available at: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Step 4.5: Launch the React Frontend SPA
In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
* Access the OpsLens Dashboard at: [http://localhost:5173](http://localhost:5173)

---

## 5. Simulating Faults and Automated Remediation

You can inject faults and trigger remediation directly through the Web UI or via the API:

### Via Web UI
* Navigate to [http://localhost:5173/lineage](http://localhost:5173/lineage).
* In the floating **Fault Toolbar**, select a fault from the dropdown (e.g. `Stale Feed` or `Row Drop`) and click **Inject Fault**.
* Observe the lineage graph update in real time with degraded status rings and blast radius impact.
* Click **Reset** (🔄) to clear the fault, restore clean data, auto-resolve alerts, and restore 100% Green trust scores.

### Via Command Line / API
```powershell
# Inject Stale Feed
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/faults/stale_feed

# Check Lineage Status
(Invoke-RestMethod -Method Get -Uri http://localhost:8000/api/lineage).nodes | Select-Object id, label, status

# Restore Clean State
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/faults/reset
```

---

## 6. Running the Test Suite

OpsLens provides a dual test suite:

### Fast Test Suite (Unit, Lineage, API, Security Guardrails)
Runs in $\approx 16$ seconds:
```powershell
python -m pytest -m "not slow" -v
```

### Slow Test Suite (End-to-End Fault Cycles & Anomaly Matrix)
Executes all 7 fault injection and recovery cycles:
```powershell
python -m pytest -m slow -v
```

---

## 7. Troubleshooting Guide

| Issue | Cause | Solution |
|---|---|---|
| **`ConnectionRefusedError` (port 8563)** | Exasol Personal service is stopped. | Verify with `exasol deployment status default` or restart using `exasol.exe`. Test via `Test-NetConnection 127.0.0.1 -Port 8563`. |
| **`SSL: CERTIFICATE_VERIFY_FAILED`** | Local self-signed SSL certificate. | Ensure `EXA_VERIFY_CERT=false` is set in your `.env` file. |
| **Port 8000 or 5173 already in use** | A prior uvicorn or node process is hung. | Check with `Get-NetTCPConnection -LocalPort 8000` and stop using `Stop-Process -Id <PID>`. |
| **`PermissionError: [WinError 10013]`** | Windows socket permissions or sandbox block. | Ensure terminal has administrative network execution rights. |
| **`ModuleNotFoundError: No module named 'backend'`** | Running script from subfolder. | Always execute commands from the repository root (e.g., `python -m backend.connectivity_test`). |
