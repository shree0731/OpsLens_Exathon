"""
OpsLens Workload Generator
Simulates realistic query telemetry and writes to OPSLENS.QUERY_STATS for Cost Radar.
Features:
- Realistic teams: finance, ops, analytics.
- Repeated heavy queries vs fast dashboard queries.
- Frequently queried tables (ORDERS, LINEITEM, ENERGY_READINGS) vs tables NEVER or rarely read (ENERGY_METERS).
- Accurate execution statistics (duration, CPU, RAM peak, estimated cloud cost).
- All records labeled as IS_SIMULATED = TRUE.
"""

import uuid
import hashlib
import random
from datetime import datetime, timedelta
import pandas as pd
from backend.db import get_connection

random.seed(1337)

USERS = [
    {"user": "alice_fin", "team": "finance"},
    {"user": "bob_fin", "team": "finance"},
    {"user": "carol_ops", "team": "ops"},
    {"user": "dan_ops", "team": "ops"},
    {"user": "eve_analytics", "team": "analytics"},
    {"user": "frank_ds", "team": "analytics"},
    {"user": "bi_dashboard_svc", "team": "analytics"},
]

QUERY_TEMPLATES = [
    # Heavy queries (Finance / Analytics)
    {
        "category": "heavy",
        "teams": ["finance", "analytics"],
        "target_tables": "OPSLENS.LINEITEM, OPSLENS.ORDERS",
        "text": "SELECT L_RETURNFLAG, L_LINESTATUS, COUNT(*), SUM(L_QUANTITY), SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) AS NET_SALES, AVG(L_DISCOUNT) FROM OPSLENS.LINEITEM L JOIN OPSLENS.ORDERS O ON L.L_ORDERKEY = O.O_ORDERKEY GROUP BY 1, 2",
        "base_dur": 48.0,
        "base_cpu": 192.0,
        "base_ram": 380.0,
        "rows": 4,
        "weight": 15,
    },
    {
        "category": "heavy",
        "teams": ["finance"],
        "target_tables": "OPSLENS.ORDERS",
        "text": "SELECT O_ORDERDATE, O_ORDERPRIORITY, COUNT(DISTINCT O_ORDERKEY) AS ORDERS, SUM(O_TOTALPRICE) AS TOTAL_VAL FROM OPSLENS.ORDERS WHERE O_ORDERDATE BETWEEN '1995-01-01' AND '1996-12-31' GROUP BY 1, 2 ORDER BY 1",
        "base_dur": 26.0,
        "base_cpu": 95.0,
        "base_ram": 140.0,
        "rows": 730,
        "weight": 20,
    },
    {
        "category": "heavy",
        "teams": ["ops"],
        "target_tables": "OPSLENS.ENERGY_READINGS",
        "text": "SELECT METER_ID, DATE_TRUNC('month', READING_TS) AS MTH, SUM(KWH) AS MONTH_KWH, AVG(KWH) AS AVG_LOAD, MAX(KWH) AS PEAK_LOAD FROM OPSLENS.ENERGY_READINGS GROUP BY 1, 2 ORDER BY 1, 2",
        "base_dur": 32.0,
        "base_cpu": 128.0,
        "base_ram": 210.0,
        "rows": 150,
        "weight": 18,
    },
    # Medium queries
    {
        "category": "medium",
        "teams": ["analytics"],
        "target_tables": "OPSLENS.REVENUE_MART",
        "text": "SELECT ORDER_DATE, SUM(TOTAL_ORDER_VALUE) AS REVENUE, SUM(TOTAL_ORDERS) AS CNT FROM OPSLENS.REVENUE_MART WHERE ORDER_DATE >= '1996-01-01' GROUP BY 1 ORDER BY 2 DESC LIMIT 100",
        "base_dur": 6.5,
        "base_cpu": 18.0,
        "base_ram": 64.0,
        "rows": 100,
        "weight": 35,
    },
    {
        "category": "medium",
        "teams": ["ops"],
        "target_tables": "OPSLENS.GRID_OPS_MART",
        "text": "SELECT CITY, TARIFF, SUM(TOTAL_KWH) AS CITY_KWH, AVG(AVG_TEMPERATURE) AS MEAN_TEMP FROM OPSLENS.GRID_OPS_MART GROUP BY 1, 2 ORDER BY 3 DESC",
        "base_dur": 4.2,
        "base_cpu": 12.0,
        "base_ram": 45.0,
        "rows": 30,
        "weight": 30,
    },
    # Fast dashboard / interactive queries
    {
        "category": "fast",
        "teams": ["analytics", "ops", "finance"],
        "target_tables": "OPSLENS.REVENUE_MART",
        "text": "SELECT SUM(TOTAL_ORDER_VALUE) AS CURRENT_MRR, COUNT(*) AS ACTIVE_DAYS FROM OPSLENS.REVENUE_MART",
        "base_dur": 0.45,
        "base_cpu": 0.9,
        "base_ram": 16.0,
        "rows": 1,
        "weight": 50,
    },
    {
        "category": "fast",
        "teams": ["ops"],
        "target_tables": "OPSLENS.ENERGY_READINGS",
        "text": "SELECT MAX(READING_TS) AS LATEST_INGESTION_TIMESTAMP FROM OPSLENS.ENERGY_READINGS",
        "base_dur": 0.25,
        "base_cpu": 0.5,
        "base_ram": 12.0,
        "rows": 1,
        "weight": 60,
    },
]

# NOTE: OPSLENS.ENERGY_METERS is intentionally absent from templates!
# This deliberately creates an "Unused / Stale Table" for Cost Radar to flag.


def calculate_query_cost(cpu_sec: float, ram_mb: float, duration_sec: float) -> float:
    """
    Cost formula based on cloud DW compute consumption:
    $0.0006 per CPU second + $0.000002 per MB-RAM second + $0.0001 base query overhead
    """
    cpu_cost = cpu_sec * 0.0006
    ram_cost = (ram_mb * duration_sec) * 0.000002
    base_cost = 0.0001
    return round(cpu_cost + ram_cost + base_cost, 6)


def generate_query_stats(conn, num_queries: int = 1500, days: int = 30):
    """Generates realistic query telemetry and imports into OPSLENS.QUERY_STATS."""
    print(f"  -> Generating {num_queries} simulated workload queries across {days} days...")
    conn.execute("TRUNCATE TABLE OPSLENS.QUERY_STATS")

    now = datetime.now()
    records = []

    weights = [t["weight"] for t in QUERY_TEMPLATES]

    for _ in range(num_queries):
        template = random.choices(QUERY_TEMPLATES, weights=weights, k=1)[0]
        
        eligible_users = [u for u in USERS if u["team"] in template["teams"]]
        user_info = random.choice(eligible_users)

        day_offset = random.randint(0, days)
        hour = random.choices(
            population=list(range(24)),
            weights=[1, 1, 1, 1, 1, 2, 4, 8, 12, 16, 18, 17, 14, 15, 16, 17, 14, 10, 6, 4, 3, 2, 1, 1],
            k=1
        )[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        query_start = (now - timedelta(days=day_offset)).replace(hour=hour, minute=minute, second=second)

        dur = max(0.1, random.gauss(template["base_dur"], template["base_dur"] * 0.2))
        cpu = max(0.1, random.gauss(template["base_cpu"], template["base_cpu"] * 0.2))
        ram = max(8.0, random.gauss(template["base_ram"], template["base_ram"] * 0.15))
        rows = max(1, int(random.gauss(template["rows"], template["rows"] * 0.1)))
        cost = calculate_query_cost(cpu, ram, dur)

        query_text = template["text"]
        query_hash = hashlib.md5(query_text.encode("utf-8")).hexdigest()[:16]
        query_id = f"qry_{uuid.uuid4().hex[:12]}"

        records.append({
            "QUERY_ID": query_id,
            "USER_NAME": user_info["user"],
            "TEAM": user_info["team"],
            "QUERY_HASH": query_hash,
            "QUERY_TEXT": query_text,
            "TARGET_TABLES": template["target_tables"],
            "START_TIME": query_start,
            "DURATION_SEC": round(dur, 3),
            "CPU_SECONDS": round(cpu, 3),
            "RAM_PEAK_MB": round(ram, 1),
            "ROWS_RETURNED": rows,
            "ESTIMATED_COST_USD": cost,
            "EXECUTION_MODE": "DIRECT",
            "IS_SIMULATED": True,
            "CREATED_AT": now,
        })

    df = pd.DataFrame(records)
    conn.import_from_pandas(df, ("OPSLENS", "QUERY_STATS"))
    print(f"     [OK] Inserted {len(records):,} query records into OPSLENS.QUERY_STATS")


def run_workload_generator():
    print("=" * 60)
    print(" OpsLens — Cost Radar Query Workload Generator")
    print("=" * 60)
    conn = get_connection(schema="OPSLENS")
    try:
        generate_query_stats(conn, num_queries=1500, days=30)
        print(">> Query workload generation completed successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    run_workload_generator()
