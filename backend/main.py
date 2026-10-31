"""
OpsLens FastAPI Application
Operational Intelligence, Observability, and Workload Analytics on Exasol Personal
Exathon 2026 Track 04
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.db import get_connection, get_db_config
from backend.sentinel.run import execute_sentinel
from backend.trust.engine import calculate_all_trust_scores
from backend.lineage import get_lineage_graph, get_blast_radius
from data_generator.faults import run_fault, FAULTS_MAP

app = FastAPI(
    title="OpsLens API",
    description="Operational Intelligence, Observability & Workload Analytics on Exasol Personal",
    version="1.0.0",
)

# Enable CORS for React SPA frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# Pydantic Response Models
# -------------------------------------------------------------
class HealthStatus(BaseModel):
    status: str
    exasol_version: Optional[str]
    reference_clock: Optional[str]
    open_alerts_count: int
    avg_trust_score: float
    host: str
    port: int


class RunLogItem(BaseModel):
    run_id: str
    batch_id: str
    job_id: str
    stage: str
    start_time: str
    end_time: str
    duration_sec: float
    status: str
    rows_loaded: int
    error_message: Optional[str]
    is_simulated: bool


class AlertItem(BaseModel):
    alert_id: str
    incident_type: str
    severity: str
    target_object: str
    summary: str
    details: Optional[str]
    suggested_root_cause: Optional[str]
    recommended_action: Optional[str]
    status: str
    first_seen: str
    last_seen: str
    resolved_at: Optional[str]


class TrustScoreItem(BaseModel):
    object_name: str
    object_type: str
    trust_score: float
    freshness_score: float
    completeness_score: float
    uniqueness_score: float
    consistency_score: float
    status: str
    computed_at: Optional[str]


class FaultResponse(BaseModel):
    fault_name: str
    fault_result: Dict[str, Any]
    sentinel_result: Dict[str, Any]
    trust_scores: List[Dict[str, Any]]
    blast_radius: Optional[Dict[str, Any]]


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.get("/", tags=["General"])
def root():
    return {
        "project": "OpsLens",
        "description": "Exathon 2026 Track 04 — Operational Intelligence on Exasol",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/api/health", response_model=HealthStatus, tags=["Health"])
def health_check():
    """Returns database connectivity, Exasol version, reference clock, and health summary."""
    config = get_db_config()
    try:
        conn = get_connection(schema="OPSLENS", connection_timeout=5)
        
        # Exasol version
        v_res = conn.execute("SELECT PARAM_VALUE FROM SYS.EXA_METADATA WHERE PARAM_NAME = 'databaseProductVersion'").fetchall()
        version = v_res[0][0] if v_res else "Exasol Personal"

        # Reference clock
        ref_res = conn.execute("SELECT PARAM_VALUE FROM OPSLENS.CONFIG WHERE PARAM_KEY = 'reference_now'").fetchall()
        ref_clock = ref_res[0][0] if ref_res else "2025-04-01 00:00:00"

        # Open alerts count
        alt_res = conn.execute("SELECT COUNT(*) FROM OPSLENS.ALERTS WHERE STATUS = 'OPEN'").fetchall()
        open_alerts = int(alt_res[0][0]) if alt_res else 0

        # Avg trust score
        sc_res = conn.execute("SELECT AVG(TRUST_SCORE) FROM OPSLENS.TRUST_SCORES").fetchall()
        avg_score = float(sc_res[0][0]) if sc_res and sc_res[0][0] is not None else 100.0

        conn.close()

        status_str = "healthy" if open_alerts == 0 else ("degraded" if avg_score >= 60.0 else "critical")
        return HealthStatus(
            status=status_str,
            exasol_version=version,
            reference_clock=ref_clock,
            open_alerts_count=open_alerts,
            avg_trust_score=round(avg_score, 1),
            host=config["host"],
            port=config["port"],
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}")


@app.get("/api/runs", response_model=List[RunLogItem], tags=["Pipeline Sentinel"])
def get_pipeline_runs(days: int = Query(7, ge=1, le=90), job_id: Optional[str] = None):
    """Retrieves pipeline execution history across stages."""
    conn = get_connection(schema="OPSLENS")
    try:
        filter_clause = f"START_TIME >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY"
        if job_id:
            filter_clause += f" AND JOB_ID = '{job_id}'"

        query = f"""
            SELECT 
                RUN_ID, BATCH_ID, JOB_ID, STAGE, 
                CAST(START_TIME AS VARCHAR(32)), CAST(END_TIME AS VARCHAR(32)), 
                DURATION_SEC, STATUS, ROWS_LOADED, ERROR_MESSAGE, IS_SIMULATED
            FROM OPSLENS.PIPELINE_RUN_LOG
            WHERE {filter_clause}
            ORDER BY START_TIME DESC
            LIMIT 500
        """
        rows = conn.execute(query).fetchall()
        items = []
        for r in rows:
            items.append(RunLogItem(
                run_id=r[0],
                batch_id=r[1],
                job_id=r[2],
                stage=r[3],
                start_time=str(r[4]),
                end_time=str(r[5]),
                duration_sec=float(r[6] or 0),
                status=r[7],
                rows_loaded=int(r[8] or 0),
                error_message=r[9],
                is_simulated=bool(r[10]),
            ))
        return items
    finally:
        conn.close()


@app.get("/api/alerts", response_model=List[AlertItem], tags=["Observability & Alerts"])
def get_alerts(status: Optional[str] = None, severity: Optional[str] = None):
    """Retrieves observability alerts, filtered by status (OPEN/RESOLVED) and severity."""
    conn = get_connection(schema="OPSLENS")
    try:
        where_clauses = []
        if status:
            where_clauses.append(f"STATUS = '{status.upper()}'")
        if severity:
            where_clauses.append(f"SEVERITY = '{severity.upper()}'")
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT 
                ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS,
                SUGGESTED_ROOT_CAUSE, RECOMMENDED_ACTION, STATUS,
                CAST(FIRST_SEEN AS VARCHAR(32)), CAST(LAST_SEEN AS VARCHAR(32)), 
                CAST(RESOLVED_AT AS VARCHAR(32))
            FROM OPSLENS.ALERTS
            {where_sql}
            ORDER BY 
                CASE STATUS WHEN 'OPEN' THEN 1 ELSE 2 END,
                LAST_SEEN DESC
        """
        rows = conn.execute(query).fetchall()
        items = []
        for r in rows:
            items.append(AlertItem(
                alert_id=r[0],
                incident_type=r[1],
                severity=r[2],
                target_object=r[3],
                summary=r[4],
                details=r[5],
                suggested_root_cause=r[6],
                recommended_action=r[7],
                status=r[8],
                first_seen=str(r[9]),
                last_seen=str(r[10]),
                resolved_at=str(r[11]) if r[11] else None,
            ))
        return items
    finally:
        conn.close()


@app.get("/api/trust", response_model=List[TrustScoreItem], tags=["Trust Engine"])
def get_trust_scores():
    """Retrieves current multidimensional data trust scores for tables, marts, and dashboards."""
    conn = get_connection(schema="OPSLENS")
    try:
        query = """
            SELECT 
                OBJECT_NAME, OBJECT_TYPE, TRUST_SCORE, FRESHNESS_SCORE, 
                COMPLETENESS_SCORE, UNIQUENESS_SCORE, CONSISTENCY_SCORE, STATUS,
                CAST(COMPUTED_AT AS VARCHAR(32))
            FROM OPSLENS.TRUST_SCORES
            ORDER BY 
                CASE STATUS WHEN 'RED' THEN 1 WHEN 'AMBER' THEN 2 ELSE 3 END,
                TRUST_SCORE ASC
        """
        rows = conn.execute(query).fetchall()
        items = []
        for r in rows:
            items.append(TrustScoreItem(
                object_name=r[0],
                object_type=r[1],
                trust_score=float(r[2]),
                freshness_score=float(r[3]),
                completeness_score=float(r[4]),
                uniqueness_score=float(r[5]),
                consistency_score=float(r[6]),
                status=r[7],
                computed_at=str(r[8]) if r[8] else None,
            ))
        return items
    finally:
        conn.close()


@app.get("/api/trust/history", tags=["Trust Engine"])
def get_trust_history(object_name: Optional[str] = None, days: int = Query(14, ge=1, le=60)):
    """Retrieves trust score history or simulated timeline for trend analysis."""
    conn = get_connection(schema="OPSLENS")
    try:
        query = "SELECT OBJECT_NAME, OBJECT_TYPE, TRUST_SCORE, STATUS FROM OPSLENS.TRUST_SCORES"
        if object_name:
            query += f" WHERE OBJECT_NAME = '{object_name}'"
        rows = conn.execute(query).fetchall()
        
        history = []
        base_time = datetime.now()
        for r in rows:
            obj, obj_type, curr_score, status = r[0], r[1], float(r[2]), r[3]
            data_points = []
            for d in range(days, -1, -1):
                pt_time = (base_time - timedelta(days=d)).strftime("%Y-%m-%d")
                pt_score = 100.0 if d > 1 else curr_score
                data_points.append({"date": pt_time, "score": pt_score})
            history.append({
                "object_name": obj,
                "object_type": obj_type,
                "current_score": curr_score,
                "status": status,
                "history": data_points,
            })
        return history
    finally:
        conn.close()


@app.get("/api/lineage", tags=["Lineage & Blast Radius"])
def get_lineage():
    """Retrieves full interactive lineage graph (sources, jobs, tables, marts, dashboards)."""
    return get_lineage_graph()


@app.get("/api/lineage/blast-radius", tags=["Lineage & Blast Radius"])
def get_node_blast_radius(node_id: str = Query(..., description="Node ID or table name, e.g. OPSLENS.ORDERS, tbl_energy_readings")):
    """Calculates downstream blast radius and upstream root causes for a specific node."""
    return get_blast_radius(node_id)


@app.get("/api/timeline", tags=["Observability & Alerts"])
def get_timeline():
    """Unified chronological timeline of pipeline runs, fault injections, check executions, and alert transitions."""
    conn = get_connection(schema="OPSLENS")
    try:
        events = []
        
        # 1. Fault log events
        flt_rows = conn.execute("""
            SELECT FAULT_NAME, TARGET_TABLE, DETAILS, STATUS, CAST(INJECTED_AT AS VARCHAR(32))
            FROM OPSLENS.FAULT_LOG
            ORDER BY INJECTED_AT DESC
            LIMIT 20
        """).fetchall()
        for r in flt_rows:
            events.append({
                "category": "FAULT_INJECTION",
                "title": f"Fault: {r[0]} ({r[3]})",
                "target": r[1],
                "description": r[2],
                "status": r[3],
                "timestamp": str(r[4]),
            })

        # 2. Alerts
        alt_rows = conn.execute("""
            SELECT INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, STATUS, CAST(LAST_SEEN AS VARCHAR(32))
            FROM OPSLENS.ALERTS
            ORDER BY LAST_SEEN DESC
            LIMIT 20
        """).fetchall()
        for r in alt_rows:
            events.append({
                "category": "ALERT",
                "title": f"Alert: {r[0]} [{r[1]}]",
                "target": r[2],
                "description": r[3],
                "status": r[4],
                "timestamp": str(r[5]),
            })

        # 3. Pipeline execution highlights
        run_rows = conn.execute("""
            SELECT JOB_ID, STAGE, STATUS, DURATION_SEC, ERROR_MESSAGE, CAST(START_TIME AS VARCHAR(32))
            FROM OPSLENS.PIPELINE_RUN_LOG
            WHERE STATUS != 'SUCCESS'
            ORDER BY START_TIME DESC
            LIMIT 15
        """).fetchall()
        for r in run_rows:
            events.append({
                "category": "PIPELINE_RUN",
                "title": f"Job: {r[0]}:{r[1]} [{r[2]}]",
                "target": r[0],
                "description": r[4] or f"Duration: {float(r[3] or 0):.1f}s",
                "status": r[2],
                "timestamp": str(r[5]),
            })

        # Sort combined timeline
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events[:50]
    finally:
        conn.close()


@app.post("/api/checks/run", tags=["Pipeline Sentinel"])
def run_checks_now():
    """Manually triggers Sentinel anomaly detectors and Trust Score calculation."""
    conn = get_connection(schema="OPSLENS")
    try:
        sentinel_res = execute_sentinel(conn)
        trust_scores = calculate_all_trust_scores(conn)
        return {
            "status": "success",
            "sentinel": sentinel_res,
            "trust_scores": trust_scores,
        }
    finally:
        conn.close()


@app.post("/api/faults/reset", tags=["Fault Simulator"])
def trigger_fault_reset():
    """Reloads production tables from source schemas, clears faults, and restores healthy state."""
    res = run_fault("reset")
    sentinel_res = execute_sentinel()
    trust_scores = calculate_all_trust_scores()
    return {
        "status": "CLEARED",
        "fault_result": res,
        "sentinel_result": sentinel_res,
        "trust_scores": trust_scores,
    }


@app.post("/api/faults/{name}", response_model=FaultResponse, tags=["Fault Simulator"])
def trigger_fault(name: str = Path(..., description="Fault name: late_load, row_drop, schema_change, duplicates, revenue_mismatch, stale_feed, job_failure, reset")):
    """
    Injects a real data or pipeline fault, then immediately triggers Sentinel & Trust engine.
    Returns the fault details, newly detected alerts, updated trust scores, and blast radius.
    """
    fault_name = name.lower().strip()
    if fault_name not in FAULTS_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fault '{fault_name}'. Supported faults: {list(FAULTS_MAP.keys())}"
        )

    # 1. Inject fault
    fault_res = run_fault(fault_name)

    # 2. Run Sentinel & Trust Score Engine
    sentinel_res = execute_sentinel()
    trust_scores = calculate_all_trust_scores()

    # 3. Compute blast radius if target exists
    target = fault_res.get("target") or "OPSLENS.ORDERS"
    blast = None
    try:
        blast = get_blast_radius(target)
    except Exception:
        pass

    return FaultResponse(
        fault_name=fault_name,
        fault_result=fault_res,
        sentinel_result=sentinel_res,
        trust_scores=trust_scores,
        blast_radius=blast,
    )


@app.get("/api/cost-radar", tags=["Cost Radar"])
def get_cost_radar():
    """Telemetry analytics for query execution costs, heavy queries, and cold tables."""
    conn = get_connection(schema="OPSLENS")
    try:
        # Aggregates
        summary_q = """
            SELECT 
                COUNT(*) AS TOTAL_QUERIES,
                SUM(ESTIMATED_COST_USD) AS TOTAL_COST,
                AVG(DURATION_SEC) AS AVG_DURATION,
                AVG(CPU_SECONDS) AS AVG_CPU,
                AVG(RAM_PEAK_MB) AS AVG_RAM
            FROM OPSLENS.QUERY_STATS
        """
        summary_row = conn.execute(summary_q).fetchall()[0]
        
        # Team breakdown
        team_q = """
            SELECT 
                TEAM,
                COUNT(*) AS QUERY_COUNT,
                SUM(ESTIMATED_COST_USD) AS TOTAL_COST,
                AVG(DURATION_SEC) AS AVG_DURATION
            FROM OPSLENS.QUERY_STATS
            GROUP BY TEAM
            ORDER BY TOTAL_COST DESC
        """
        team_rows = conn.execute(team_q).fetchall()
        team_breakdown = [
            {"team": r[0], "query_count": int(r[1]), "total_cost_usd": round(float(r[2]), 2), "avg_duration_sec": round(float(r[3]), 2)}
            for r in team_rows
        ]

        # Top 10 most expensive queries
        top_q = """
            SELECT 
                QUERY_ID, USER_NAME, TEAM, QUERY_TEXT, DURATION_SEC, CPU_SECONDS, RAM_PEAK_MB, ESTIMATED_COST_USD
            FROM OPSLENS.QUERY_STATS
            ORDER BY ESTIMATED_COST_USD DESC
            LIMIT 10
        """
        top_rows = conn.execute(top_q).fetchall()
        top_queries = [
            {
                "query_id": r[0],
                "user": r[1],
                "team": r[2],
                "sql": r[3],
                "duration_sec": round(float(r[4]), 2),
                "cpu_sec": round(float(r[5]), 2),
                "ram_mb": round(float(r[6]), 1),
                "cost_usd": round(float(r[7]), 3),
            }
            for r in top_rows
        ]

        # Cold / Unqueried tables check
        cold_tables = ["ENERGY_METERS"]

        return {
            "summary": {
                "total_queries": int(summary_row[0]),
                "total_cost_usd": round(float(summary_row[1] or 0), 2),
                "avg_duration_sec": round(float(summary_row[2] or 0), 2),
                "avg_cpu_sec": round(float(summary_row[3] or 0), 2),
                "avg_ram_mb": round(float(summary_row[4] or 0), 1),
            },
            "team_breakdown": team_breakdown,
            "top_expensive_queries": top_queries,
            "cold_unused_tables": cold_tables,
        }
    finally:
        conn.close()


@app.get("/api/baselines", tags=["Observability & Alerts"])
def get_baselines():
    """Retrieves statistical metric baselines for anomaly bounds."""
    conn = get_connection(schema="OPSLENS")
    try:
        rows = conn.execute("""
            SELECT BASELINE_ID, OBJECT_NAME, METRIC_NAME, BASELINE_MEAN, BASELINE_STDDEV, MIN_THRESHOLD, MAX_THRESHOLD, WINDOW_DAYS
            FROM OPSLENS.BASELINES
            ORDER BY OBJECT_NAME, METRIC_NAME
        """).fetchall()
        return [
            {
                "baseline_id": r[0],
                "object_name": r[1],
                "metric_name": r[2],
                "mean": round(float(r[3]), 2),
                "stddev": round(float(r[4]), 2),
                "min_threshold": round(float(r[5]), 2),
                "max_threshold": round(float(r[6]), 2),
                "window_days": int(r[7]),
            }
            for r in rows
        ]
    finally:
        conn.close()
