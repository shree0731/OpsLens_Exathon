"""
OpsLens FastAPI Application Entrypoint
Exathon 2026 Track 04
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db import get_connection, get_db_config

app = FastAPI(
    title="OpsLens API",
    description="Operational Intelligence, Observability, and Telemetry on Exasol Personal",
    version="0.1.0",
)

# Enable CORS for React frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "project": "OpsLens",
        "description": "Exathon 2026 Track 04 - Operational Intelligence on Exasol",
        "status": "online",
    }


@app.get("/api/health")
def health_check():
    config = get_db_config()
    db_status = "unknown"
    error_detail = None

    try:
        conn = get_connection(schema="", connection_timeout=5)
        stmt = conn.execute("SELECT 1")
        val = stmt.fetchall()
        db_status = "connected" if val and val[0][0] == 1 else "unexpected_result"
        conn.close()
    except Exception as exc:
        db_status = "disconnected"
        error_detail = str(exc)

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": {
            "status": db_status,
            "host": config["host"],
            "port": config["port"],
            "verify_cert": config["verify_cert"],
            "error": error_detail,
        },
    }
