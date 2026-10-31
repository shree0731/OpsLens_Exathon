# AGENTS.md — OpsLens Rules and Guidelines

Welcome to **OpsLens** for **Exathon 2026 Track 04**.
OpsLens is an operational intelligence, query observability, and workload analytics dashboard built on **Exasol Personal Edition**.

---

## 1. Project Directory Layout

The repository must follow this clean structure:

```
OpsLens/
├── backend/            # FastAPI application, database helpers, API routers, background workers
├── frontend/           # Modern React Single Page Application (dashboard UI)
├── data_generator/     # Synthetic workload, query simulators, and telemetry generators
├── sql/                # DDL scripts, schema migrations, views, and stored procedures for OPSLENS
├── docs/               # Architecture docs, data discovery notes, and design references
│   ├── design/         # UI wireframes and reference designs (e.g. reference.png)
│   └── data_discovery.md
├── deploy/             # Docker, docker-compose, and environment deployment manifests
├── tests/              # Backend, API, and integration tests (pytest)
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules for credentials, caches, node_modules, etc.
├── Makefile            # Project automation tasks
├── requirements.txt    # Python dependencies
└── AGENTS.md           # Agent rules and architecture specification
```

> **Note:** The frontend is strictly built with **React** (SPA). Do not use Streamlit.

---

## 2. Exasol Platform & Schema Rules

1. **Mandatory Platform**: Exasol Personal Edition is the primary and mandatory analytics database.
2. **Immutable Sample Schemas**:
   - `ENERGY`, `SCHED`, `TPCH`, `WEATHER` are pre-existing reference schemas.
   - **NEVER** insert, update, delete, or alter any objects inside these schemas. They are strictly read-only.
3. **Application Schema**:
   - All OpsLens application tables, views, telemetry logs, and incident records **MUST** be placed in schema **`OPSLENS`**.
   - Create schema `OPSLENS` if it does not already exist.

---

## 3. Configuration & Credential Management

- All credentials, hosts, and secrets **MUST** be loaded exclusively from `.env`. Never commit secrets to version control.
- Configuration variables:
  - `EXA_HOST`: Exasol host (e.g., `localhost` or remote IP/hostname)
  - `EXA_PORT`: Exasol port (default: `8563`)
  - `EXA_USER`: Database username (default: `sys` or custom user)
  - `EXA_PASSWORD`: Database password
  - `EXA_SCHEMA`: Default schema (`OPSLENS`)
  - `EXA_VERIFY_CERT`: Certificate verification flag (`false` for local dev self-signed certificates, `true` in production)
  - `EXA_ENCRYPTION`: Connection encryption flag (`true` by default)
  - `LLM_PROVIDER`: Optional LLM service (`gemini`, `claude`, `openai`).
  - `LLM_API_KEY`: API key for the chosen LLM.
  - `SLACK_WEBHOOK_URL`: Optional webhook for incident alerts (console logging is the default fallback).

---

## 4. Coding & Tooling Standards

- **Backend**: Python 3.10+ with `FastAPI`, `uvicorn`, `pyexasol`, `pandas`, `python-dotenv`, `pytest`, `requests`.
- **Database Access**: All connections must be managed via `backend/db.py` using `pyexasol`.
- **Frontend**: React with modern tooling (Vite / React Router / Tailwind / Recharts or Chart.js).
- **Cross-Platform Compatibility**: Scripts and paths must support Windows (PowerShell/cmd) and POSIX environments.
- **Accuracy & Honesty**: Never hallucinate database columns, table contents, or system views. If an Exasol view or query fails, capture and report the exact error message.
