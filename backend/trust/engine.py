"""
OpsLens Trust Score Calculation Engine
Computes multidimensional trust scores across 4 pillars:
- Freshness (30%)
- Completeness (20%)
- Uniqueness (20%)
- Consistency (30%)

Propagates trust through lineage to marts and dashboards.
Status thresholds:
- Green: >= 85.0
- Amber: 60.0 - 84.9
- Red: < 60.0
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

from backend.db import get_connection

WEIGHT_FRESHNESS = 0.30
WEIGHT_COMPLETENESS = 0.20
WEIGHT_UNIQUENESS = 0.20
WEIGHT_CONSISTENCY = 0.30

STATUS_GREEN_MIN = 85.0
STATUS_AMBER_MIN = 60.0


def get_status(score: float) -> str:
    """Returns GREEN, AMBER, or RED based on score value."""
    if score >= STATUS_GREEN_MIN:
        return "GREEN"
    elif score >= STATUS_AMBER_MIN:
        return "AMBER"
    return "RED"


def compute_freshness_scores(conn) -> Dict[str, float]:
    """Computes freshness score (0-100) per table."""
    freshness = {
        "ORDERS": 100.0,
        "LINEITEM": 100.0,
        "CUSTOMER": 100.0,
        "ENERGY_READINGS": 100.0,
        "ENERGY_METERS": 100.0,
        "WEATHER_DAILY": 100.0,
    }

    # Reference clock and expectations
    cfg_rows = conn.execute("SELECT PARAM_KEY, PARAM_VALUE FROM OPSLENS.CONFIG").fetchall()
    cfg = {r[0]: r[1] for r in cfg_rows}

    exp_energy_str = cfg.get("expected_latest_energy", "2025-03-31 23:00:00")
    exp_weather_str = cfg.get("expected_latest_weather", "2025-12-31 00:00:00")
    exp_energy = datetime.fromisoformat(exp_energy_str.replace(" ", "T"))
    exp_weather = datetime.fromisoformat(exp_weather_str.replace(" ", "T"))

    # 1. ENERGY_READINGS
    e_res = conn.execute("SELECT MAX(READING_TS) FROM OPSLENS.ENERGY_READINGS").fetchall()
    max_energy = e_res[0][0]
    if isinstance(max_energy, str):
        max_energy = datetime.fromisoformat(max_energy.replace(" ", "T"))
    elif hasattr(max_energy, "to_pydatetime"):
        max_energy = max_energy.to_pydatetime()

    if max_energy:
        lag_hours = max(0.0, (exp_energy - max_energy).total_seconds() / 3600.0)
        if lag_hours <= 1.0:
            freshness["ENERGY_READINGS"] = 100.0
        else:
            # Penalize: 24h lag drops by 20pts; > 168h (7d) drops to 0
            freshness["ENERGY_READINGS"] = max(0.0, round(100.0 - (lag_hours / 168.0) * 100.0, 2))

    # 2. WEATHER_DAILY
    w_res = conn.execute("SELECT MAX(W_DATE) FROM OPSLENS.WEATHER_DAILY").fetchall()
    max_weather = w_res[0][0]
    if isinstance(max_weather, str):
        max_weather = datetime.fromisoformat(max_weather.replace(" ", "T"))
    elif hasattr(max_weather, "to_pydatetime"):
        max_weather = max_weather.to_pydatetime()
    elif hasattr(max_weather, "year"):
        max_weather = datetime(max_weather.year, max_weather.month, max_weather.day)

    if max_weather:
        lag_days = max(0, (exp_weather - max_weather).days)
        if lag_days <= 1:
            freshness["WEATHER_DAILY"] = 100.0
        else:
            # Penalize: 7d lag drops to 0
            freshness["WEATHER_DAILY"] = max(0.0, round(100.0 - (lag_days / 7.0) * 100.0, 2))

    # 3. Check for late load on ORDERS in run log
    late_chk = conn.execute("""
        SELECT COUNT(*) 
        FROM OPSLENS.PIPELINE_RUN_LOG 
        WHERE JOB_ID = 'load_orders' 
          AND STATUS IN ('WARNING', 'FAILED')
          AND RUN_ID = (SELECT MAX(RUN_ID) FROM OPSLENS.PIPELINE_RUN_LOG WHERE JOB_ID = 'load_orders')
    """).fetchall()
    if late_chk and late_chk[0][0] > 0:
        freshness["ORDERS"] = 40.0

    return freshness


def compute_completeness_scores(conn) -> Dict[str, float]:
    """Computes completeness score (0-100) based on volume drop against baseline."""
    completeness = {}
    
    b_rows = conn.execute("""
        SELECT OBJECT_NAME, BASELINE_MEAN 
        FROM OPSLENS.BASELINES 
        WHERE METRIC_NAME = 'ROW_COUNT'
    """).fetchall()

    for b in b_rows:
        tbl = b[0].replace("OPSLENS.", "").strip()
        mean_cnt = float(b[1])
        
        cnt_res = conn.execute(f"SELECT COUNT(*) FROM OPSLENS.{tbl}").fetchall()
        live_cnt = float(cnt_res[0][0]) if cnt_res else 0.0

        if live_cnt >= mean_cnt or mean_cnt == 0:
            score = 100.0
        else:
            drop_pct = ((mean_cnt - live_cnt) / mean_cnt) * 100.0
            if drop_pct <= 1.0:
                score = 100.0
            else:
                score = max(0.0, round(100.0 - (drop_pct * 2.0), 2))
        completeness[tbl] = score

    return completeness


def compute_uniqueness_scores(conn) -> Dict[str, float]:
    """Computes uniqueness score (0-100) based on duplicate key checks."""
    uniqueness = {
        "ORDERS": 100.0,
        "LINEITEM": 100.0,
        "CUSTOMER": 100.0,
        "ENERGY_READINGS": 100.0,
        "ENERGY_METERS": 100.0,
        "WEATHER_DAILY": 100.0,
        "REVENUE_MART": 100.0,
        "GRID_OPS_MART": 100.0,
    }

    # ORDERS primary key
    ord_res = conn.execute("SELECT COUNT(*) - COUNT(DISTINCT O_ORDERKEY) FROM OPSLENS.ORDERS").fetchall()
    ord_dups = int(ord_res[0][0]) if ord_res else 0
    if ord_dups > 0:
        uniqueness["ORDERS"] = 15.0

    # LINEITEM composite key
    li_res = conn.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT CAST(L_ORDERKEY AS VARCHAR(32)) || '-' || CAST(L_LINENUMBER AS VARCHAR(32))) 
        FROM OPSLENS.LINEITEM
    """).fetchall()
    li_dups = int(li_res[0][0]) if li_res else 0
    if li_dups > 0:
        uniqueness["LINEITEM"] = 15.0

    return uniqueness


def compute_consistency_scores(conn) -> Dict[str, float]:
    """Computes consistency score (0-100) based on reconciliation & schema drift."""
    consistency = {
        "ORDERS": 100.0,
        "LINEITEM": 100.0,
        "CUSTOMER": 100.0,
        "ENERGY_READINGS": 100.0,
        "ENERGY_METERS": 100.0,
        "WEATHER_DAILY": 100.0,
        "REVENUE_MART": 100.0,
        "GRID_OPS_MART": 100.0,
    }

    # 1. Reconciliation Check (ORDERS vs LINEITEM)
    recon_query = """
    SELECT 
        COUNT(*) as total_orders,
        SUM(CASE WHEN ABS(O.O_TOTALPRICE - L.CALC_TOTAL) > 0.10 THEN 1 ELSE 0 END) as mismatched_orders
    FROM OPSLENS.ORDERS O
    JOIN (
        SELECT L_ORDERKEY, ROUND(SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT) * (1 + L_TAX)), 2) AS CALC_TOTAL
        FROM OPSLENS.LINEITEM
        GROUP BY L_ORDERKEY
    ) L ON O.O_ORDERKEY = L.L_ORDERKEY
    """
    recon_res = conn.execute(recon_query).fetchall()
    tot_orders = int(recon_res[0][0]) if recon_res else 0
    mism_orders = int(recon_res[0][1] or 0) if recon_res else 0

    if tot_orders > 0 and mism_orders > 0:
        mism_ratio = mism_orders / tot_orders
        recon_score = max(0.0, round(100.0 - (mism_ratio * 200.0), 2))
        consistency["ORDERS"] = min(consistency["ORDERS"], recon_score)
        consistency["LINEITEM"] = min(consistency["LINEITEM"], recon_score)
        consistency["REVENUE_MART"] = min(consistency["REVENUE_MART"], recon_score)

    # 2. Schema Drift Penalty (Check if schema drift detected on table)
    drift_alerts = conn.execute("""
        SELECT TARGET_OBJECT 
        FROM OPSLENS.ALERTS 
        WHERE INCIDENT_TYPE = 'SCHEMA_DRIFT_DETECTED' AND STATUS = 'OPEN'
    """).fetchall()
    for d in drift_alerts:
        tbl = d[0].replace("OPSLENS.", "").strip()
        if tbl in consistency:
            consistency[tbl] = max(0.0, consistency[tbl] - 35.0)

    # Also check directly if unexpected columns exist on ORDERS
    cols = [r[0] for r in conn.execute("SELECT COLUMN_NAME FROM SYS.EXA_ALL_COLUMNS WHERE COLUMN_SCHEMA='OPSLENS' AND COLUMN_TABLE='ORDERS'").fetchall()]
    if "UNEXPECTED_TAX_SURCHARGE" in cols:
        consistency["ORDERS"] = max(0.0, consistency["ORDERS"] - 35.0)

    # 3. Job failure penalty (if build_revenue_mart failed)
    fail_chk = conn.execute("""
        SELECT COUNT(*) 
        FROM OPSLENS.PIPELINE_RUN_LOG 
        WHERE JOB_ID = 'build_revenue_mart' AND STATUS = 'FAILED'
    """).fetchall()
    if fail_chk and fail_chk[0][0] > 0:
        consistency["REVENUE_MART"] = 25.0

    return consistency


def calculate_all_trust_scores(conn=None) -> List[Dict[str, Any]]:
    """
    Computes complete trust scores for tables, marts, and dashboards.
    Persists results into OPSLENS.TRUST_SCORES.
    """
    should_close = False
    if conn is None:
        conn = get_connection(schema="OPSLENS")
        should_close = True

    try:
        freshness_map = compute_freshness_scores(conn)
        completeness_map = compute_completeness_scores(conn)
        uniqueness_map = compute_uniqueness_scores(conn)
        consistency_map = compute_consistency_scores(conn)

        base_tables = [
            "ORDERS",
            "LINEITEM",
            "CUSTOMER",
            "ENERGY_READINGS",
            "ENERGY_METERS",
            "WEATHER_DAILY",
        ]

        scores_list = []

        # 1. Base Tables
        for tbl in base_tables:
            f = freshness_map.get(tbl, 100.0)
            c = completeness_map.get(tbl, 100.0)
            u = uniqueness_map.get(tbl, 100.0)
            s = consistency_map.get(tbl, 100.0)
            total = round(WEIGHT_FRESHNESS * f + WEIGHT_COMPLETENESS * c + WEIGHT_UNIQUENESS * u + WEIGHT_CONSISTENCY * s, 2)
            
            scores_list.append({
                "OBJECT_NAME": tbl,
                "OBJECT_TYPE": "TABLE",
                "TRUST_SCORE": total,
                "FRESHNESS_SCORE": f,
                "COMPLETENESS_SCORE": c,
                "UNIQUENESS_SCORE": u,
                "CONSISTENCY_SCORE": s,
                "STATUS": get_status(total),
            })

        tbl_scores = {s["OBJECT_NAME"]: s for s in scores_list}

        # 2. Marts (Rollup upstream dependencies)
        # REVENUE_MART depends on ORDERS, LINEITEM, CUSTOMER
        rev_upstream = [tbl_scores["ORDERS"], tbl_scores["LINEITEM"], tbl_scores["CUSTOMER"]]
        rev_f = min(x["FRESHNESS_SCORE"] for x in rev_upstream)
        rev_c = min(x["COMPLETENESS_SCORE"] for x in rev_upstream)
        rev_u = min(x["UNIQUENESS_SCORE"] for x in rev_upstream)
        rev_s = min(min(x["CONSISTENCY_SCORE"] for x in rev_upstream), consistency_map.get("REVENUE_MART", 100.0))
        rev_total = round(WEIGHT_FRESHNESS * rev_f + WEIGHT_COMPLETENESS * rev_c + WEIGHT_UNIQUENESS * rev_u + WEIGHT_CONSISTENCY * rev_s, 2)

        scores_list.append({
            "OBJECT_NAME": "REVENUE_MART",
            "OBJECT_TYPE": "MART",
            "TRUST_SCORE": rev_total,
            "FRESHNESS_SCORE": rev_f,
            "COMPLETENESS_SCORE": rev_c,
            "UNIQUENESS_SCORE": rev_u,
            "CONSISTENCY_SCORE": rev_s,
            "STATUS": get_status(rev_total),
        })

        # GRID_OPS_MART depends on ENERGY_READINGS, WEATHER_DAILY, ENERGY_METERS
        grid_upstream = [tbl_scores["ENERGY_READINGS"], tbl_scores["WEATHER_DAILY"], tbl_scores["ENERGY_METERS"]]
        grid_f = min(x["FRESHNESS_SCORE"] for x in grid_upstream)
        grid_c = min(x["COMPLETENESS_SCORE"] for x in grid_upstream)
        grid_u = min(x["UNIQUENESS_SCORE"] for x in grid_upstream)
        grid_s = min(min(x["CONSISTENCY_SCORE"] for x in grid_upstream), consistency_map.get("GRID_OPS_MART", 100.0))
        grid_total = round(WEIGHT_FRESHNESS * grid_f + WEIGHT_COMPLETENESS * grid_c + WEIGHT_UNIQUENESS * grid_u + WEIGHT_CONSISTENCY * grid_s, 2)

        scores_list.append({
            "OBJECT_NAME": "GRID_OPS_MART",
            "OBJECT_TYPE": "MART",
            "TRUST_SCORE": grid_total,
            "FRESHNESS_SCORE": grid_f,
            "COMPLETENESS_SCORE": grid_c,
            "UNIQUENESS_SCORE": grid_u,
            "CONSISTENCY_SCORE": grid_s,
            "STATUS": get_status(grid_total),
        })

        all_obj_scores = {s["OBJECT_NAME"]: s for s in scores_list}

        # 3. Dashboards (Inherits minimum trust of underlying marts)
        dashboards = [
            ("Revenue Dashboard", ["REVENUE_MART"]),
            ("Grid Ops Dashboard", ["GRID_OPS_MART"]),
            ("Executive Ops Dashboard", ["REVENUE_MART", "GRID_OPS_MART"]),
        ]

        for dash_name, up_marts in dashboards:
            m_scores = [all_obj_scores[m] for m in up_marts]
            dash_f = min(x["FRESHNESS_SCORE"] for x in m_scores)
            dash_c = min(x["COMPLETENESS_SCORE"] for x in m_scores)
            dash_u = min(x["UNIQUENESS_SCORE"] for x in m_scores)
            dash_s = min(x["CONSISTENCY_SCORE"] for x in m_scores)
            dash_total = round(min(x["TRUST_SCORE"] for x in m_scores), 2)

            scores_list.append({
                "OBJECT_NAME": dash_name,
                "OBJECT_TYPE": "DASHBOARD",
                "TRUST_SCORE": dash_total,
                "FRESHNESS_SCORE": dash_f,
                "COMPLETENESS_SCORE": dash_c,
                "UNIQUENESS_SCORE": dash_u,
                "CONSISTENCY_SCORE": dash_s,
                "STATUS": get_status(dash_total),
            })

        # 4. Persist to OPSLENS.TRUST_SCORES
        conn.execute("TRUNCATE TABLE OPSLENS.TRUST_SCORES")
        for sc in scores_list:
            sc_id = f"trs_{uuid.uuid4().hex[:12]}"
            conn.execute(f"""
                INSERT INTO OPSLENS.TRUST_SCORES 
                (SCORE_ID, OBJECT_NAME, OBJECT_TYPE, TRUST_SCORE, FRESHNESS_SCORE, 
                 COMPLETENESS_SCORE, UNIQUENESS_SCORE, CONSISTENCY_SCORE, STATUS, COMPUTED_AT, IS_SIMULATED)
                VALUES 
                ('{sc_id}', '{sc["OBJECT_NAME"]}', '{sc["OBJECT_TYPE"]}', 
                 {sc["TRUST_SCORE"]}, {sc["FRESHNESS_SCORE"]}, {sc["COMPLETENESS_SCORE"]}, 
                 {sc["UNIQUENESS_SCORE"]}, {sc["CONSISTENCY_SCORE"]}, '{sc["STATUS"]}', CURRENT_TIMESTAMP, TRUE)
            """)

        return scores_list

    finally:
        if should_close and conn:
            conn.close()
