# OpsLens — Operational Intelligence & Data Observability on Exasol

> **Exathon 2026 — Track 04: Workload & Pipeline Observability**  
> Operational intelligence, query observability, fault injection simulator, and multi-dimensional data trust engine built natively on **Exasol Personal Edition**.

---

## 1. Architecture Overview

OpsLens is an enterprise data observability platform designed for Exasol. It monitors data pipeline integrity, measures continuous table and dashboard reliability, detects anomalies using statistical baselines, and traces downstream impact across an end-to-end lineage graph.

```
OpsLens/
├── backend/            # FastAPI REST API, db connection pool, Sentinel engine, Trust engine
│   ├── sentinel/       # Anomaly detectors, alert lifecycle manager, Slack webhook integration
│   ├── trust/          # Multi-dimensional trust score engine and lineage rollup
│   ├── baselines.py    # Statistical baseline computation (median, MAD, z-score, schema contracts)
│   ├── lineage.py      # Directed graph traversal, blast radius impact, root cause analysis
│   └── main.py         # FastAPI application entrypoint with full Swagger documentation
├── data_generator/     # Idempotent setup, metadata generator, simulated workload & fault injector
│   ├── setup_data.py   # Production copies into OPSLENS schema (ORDERS, LINEITEM, ENERGY, WEATHER)
│   ├── metadata_generator.py # 60 days of 5-stage pipeline run logs, job definitions, lineage edges
│   ├── workload_generator.py # 1,500 simulated query execution records for Cost Radar
│   └── faults.py       # Deterministic fault injector CLI (8 fault scenarios + reset)
├── sql/                # DDL scripts, metadata tables, analytical views, and stored queries
├── docs/               # Data discovery report and Trust Engine documentation
├── tests/              # Pytest test suite covering Sentinel, Trust, Lineage, API, and DB
└── README.md
```

---

## 2. Platform & Schema Rules

1. **Database Engine**: Exasol Personal Edition (`Exasol 2026.2.0-nano.3`) via WebSocket protocol (`pyexasol`).
2. **Immutable Source Schemas**: `ENERGY`, `SCHED`, `TPCH`, `WEATHER`, and `STARTER_KIT` are reference sample schemas and are **strictly read-only**.
3. **Application Schema**: All OpsLens tables, production copies, marts, metadata, run logs, baselines, and fault injections reside exclusively in schema **`OPSLENS`**.

---

## 3. How Detection Works

### A. Detection Integrity
OpsLens enforces absolute detection integrity:
- The fault injector (`data_generator/faults.py`) **ONLY** mutates production data or `PIPELINE_RUN_LOG` and records an audit row in `OPSLENS.FAULT_LOG`.
- It **NEVER** directly writes to `ALERTS`, `CHECK_RESULTS`, or `TRUST_SCORES`.
- Those tables are populated strictly by the **Pipeline Sentinel** and **Trust Engine** observing real database state changes.

### B. Reference Clock (`OPSLENS.CONFIG`)
Because sample datasets represent specific historical windows (e.g. Energy readings through March 2025, Weather through December 2025), OpsLens uses a configurable reference clock in `OPSLENS.CONFIG`:
- `reference_now`: `2025-04-01 00:00:00`
- `expected_latest_energy`: `2025-03-31 23:00:00`
- `expected_latest_weather`: `2025-12-31 00:00:00`

Freshness detectors compare current table timestamps against these watermarks. When `stale_feed` deletes 14 days of telemetry, the lag increases from $\le 1$ hour to 336 hours, immediately triggering alerts.

### C. The 7 SQL-Driven Sentinel Detectors
1. **`check_late_or_failed_jobs`**: Scans `PIPELINE_RUN_LOG` for fatal stage failures (`STATUS = 'FAILED'`) and runtime SLA breaches (>15m delay or `STATUS = 'WARNING'`).
2. **`check_row_count_anomalies`**: Compares live row counts against 14-day rolling medians in `OPSLENS.BASELINES`. Flags volume drops $> 25\%$ or $|z\text{-score}| > 3.0$.
3. **`check_runtime_anomalies`**: Flags stage runtimes exceeding $+3\sigma$ from baseline mean duration.
4. **`check_schema_drift`**: Compares `SYS.EXA_ALL_COLUMNS` against `SCHEMA_SNAPSHOT` baselines to detect unauthorized column additions (e.g. `UNEXPECTED_TAX_SURCHARGE`), column drops, or data type alterations.
5. **`check_stale_feeds`**: Measures max telemetry arrival timestamps against reference watermarks. Flags feeds lagging by $> 24$ hours.
6. **`check_duplicate_keys`**: Validates primary key uniqueness on `ORDERS (O_ORDERKEY)` and composite uniqueness on `LINEITEM (L_ORDERKEY, L_LINENUMBER)`.
7. **`check_reconciliation`**: Executes a high-performance per-order SQL join comparing `ORDERS.O_TOTALPRICE` against child `LINEITEM` calculated sums (`ROUND(SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT) * (1 + L_TAX)), 2)`). Calibrated to a $0.10 tolerance: clean state has **0.00% mismatch**; `revenue_mismatch` fault causes an immediate 33.33% divergence.

### D. Automated Alert Lifecycle
- When a detector fails, an incident is opened or updated in `OPSLENS.ALERTS` with severity (`WARNING` / `CRITICAL`), suggested root cause, and recommended action.
- Real-time notifications are dispatched to Slack (if `SLACK_WEBHOOK_URL` is set) and appended to `logs/alerts.log`.
- When the underlying issue is resolved (e.g. via `POST /api/faults/reset`), Sentinel automatically marks the alert as `RESOLVED` with `RESOLVED_AT = CURRENT_TIMESTAMP`.

---

## 4. Multi-Dimensional Trust Score Engine

OpsLens calculates a continuous reliability score from **0.0 to 100.0** across 4 pillars:

$$\text{Trust Score} = 0.30 \times \text{Freshness} + 0.20 \times \text{Completeness} + 0.20 \times \text{Uniqueness} + 0.30 \times \text{Consistency}$$

| Status | Range | Meaning |
| :---: | :---: | :--- |
| 🟢 **GREEN** | $\ge 85.0$ | Healthy, certified production dataset |
| 🟡 **AMBER** | $60.0 - 84.9$ | Degraded dataset; warning for downstream users |
| 🔴 **RED** | $< 60.0$ | Severe anomaly; dashboards compromised |

### Lineage Rollup Rule
Marts and dashboards inherit the **minimum health of their upstream dependencies**:
$$\text{Trust}(\text{Dashboard}) = \min_{t \in \text{Upstream}}(\text{Trust}(t))$$

---

## 5. Fault Simulator CLI

OpsLens includes a fault injector touching only `OPSLENS` copies:

```bash
# Inject 40% row drop
python -m data_generator.faults row_drop

# Inject telemetry freeze (14-day lag)
python -m data_generator.faults stale_feed

# Inject price mutations causing reconciliation failure
python -m data_generator.faults revenue_mismatch

# Inject duplicate line items
python -m data_generator.faults duplicates

# Inject schema drift (unexpected tax column)
python -m data_generator.faults schema_change

# Inject stage pipeline failure (OOM simulation)
python -m data_generator.faults job_failure

# Inject late-running load (SLA breach)
python -m data_generator.faults late_load

# Reset all tables and clear faults
python -m data_generator.faults reset
```

---

## 6. API Reference

Start the API server:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

### Core Endpoints
- `GET /api/health` — Database status, Exasol version, reference clock, open alerts.
- `GET /api/runs?days=7` — Pipeline run history across 5 canonical stages.
- `GET /api/alerts?status=OPEN` — Active observability incidents with root cause analysis.
- `GET /api/trust` — Real-time trust scores across tables, marts, and dashboards.
- `GET /api/trust/history` — 14-day historical trend per object.
- `GET /api/lineage` — Full directed dependency graph (sources, jobs, tables, marts, dashboards).
- `GET /api/lineage/blast-radius?node_id=ORDERS` — Downstream affected dashboards and upstream root causes.
- `GET /api/timeline` — Unified chronological timeline of runs, faults, checks, and alerts.
- `GET /api/cost-radar` — Query cost telemetry, team cost attribution, and unused cold tables.
- `POST /api/checks/run` — On-demand Sentinel detector and Trust score cycle.
- `POST /api/faults/{name}` — Injects fault, executes detection, and returns blast radius.
- `POST /api/faults/reset` — Resets tables, clears active faults, and restores 100% trust scores.

---

## 7. Frontend Application (React SPA)

The OpsLens UI is a Vite + React + TypeScript single-page application built with Tailwind CSS, `@xyflow/react` interactive DAG canvas, and TanStack Query.

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server on port 5173
npm run dev

# Build for production
npm run build
```
Accessible at [http://localhost:5173](http://localhost:5173).

---

## 8. Running Tests & Demo

```bash
# Run fast test suite (excludes slow matrix & timing benchmarks):
pytest -m "not slow" -v

# Run slow fault matrix and latency SLA benchmarks:
pytest -m slow -v

# Run entire test suite:
pytest -v

# Run live end-to-end demonstration sequence
python -m backend.demo
```
