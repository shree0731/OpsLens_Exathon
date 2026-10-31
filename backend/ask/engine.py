"""
OpsLens Ask-the-Warehouse Execution Engine
Connects natural language to safe, guardrailed Exasol SQL queries.
Supports LLM provider generation with automatic fallback to curated templates.
"""

import os
import time
import uuid
import hashlib
import json
import requests
from typing import Dict, Any, Optional, List, Tuple
from backend.db import get_connection
from backend.ask.guardrails import validate_guardrails
from backend.ask.templates import TEMPLATE_QUESTIONS, match_template_question


def introspect_opslens_schema(conn) -> str:
    """Introspects current OPSLENS schema table and column definitions for the prompt."""
    try:
        query = """
            SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
            FROM SYS.EXA_ALL_COLUMNS
            WHERE COLUMN_SCHEMA = 'OPSLENS'
            ORDER BY TABLE_NAME, COLUMN_ORDINAL_POSITION
        """
        rows = conn.execute(query).fetchall()
        tables: Dict[str, List[str]] = {}
        for r in rows:
            tbl, col, ctype = r[0], r[1], r[2]
            if tbl not in tables:
                tables[tbl] = []
            tables[tbl].append(f"{col} ({ctype})")

        lines = ["SCHEMA: OPSLENS", "TABLES & COLUMNS:"]
        for tbl, cols in tables.items():
            lines.append(f"- OPSLENS.{tbl}: {', '.join(cols)}")
        return "\n".join(lines)
    except Exception:
        # Static fallback if catalog view restricted
        return """SCHEMA: OPSLENS
TABLES:
- OPSLENS.ORDERS: O_ORDERKEY, O_CUSTKEY, O_ORDERSTATUS, O_TOTALPRICE, O_ORDERDATE, O_ORDERPRIORITY
- OPSLENS.LINEITEM: L_ORDERKEY, L_PARTKEY, L_SUPPKEY, L_LINENUMBER, L_QUANTITY, L_EXTENDEDPRICE, L_DISCOUNT, L_TAX
- OPSLENS.CUSTOMER: C_CUSTKEY, C_NAME, C_ADDRESS, C_PHONE, C_ACCTBAL, C_MKTSEGMENT
- OPSLENS.ENERGY_READINGS: METER_ID, READING_TS, KWH
- OPSLENS.ENERGY_METERS: METER_ID, HOUSEHOLD, CITY, TARIFF, BASE_LOAD_KWH
- OPSLENS.WEATHER_DAILY: CITY_ID, W_DATE, TEMP_AVG_C, TEMP_MIN_C, TEMP_MAX_C, PRECIP_MM, WIND_KMH
- OPSLENS.REVENUE_MART: ORDER_MONTH, TOTAL_REVENUE, ORDERS_COUNT, AVG_ORDER_VALUE
- OPSLENS.GRID_OPS_MART: READING_DATE, TOTAL_CONSUMPTION_KWH, ACTIVE_METERS, ANOMALY_COUNT
- OPSLENS.TRUST_SCORES: OBJECT_NAME, OBJECT_TYPE, TRUST_SCORE, STATUS
- OPSLENS.ALERTS: ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, STATUS
- OPSLENS.PIPELINE_RUN_LOG: RUN_ID, JOB_ID, STAGE, DURATION_SEC, STATUS, ROWS_LOADED"""


def call_llm_for_sql(question: str, schema_context: str) -> Optional[str]:
    """Invokes LLM provider if configured in environment."""
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()

    if not api_key:
        return None

    system_prompt = f"""You are OpsLens Ask-the-Warehouse, an expert SQL generator for Exasol Personal Edition.
Generate ONLY valid, read-only SELECT SQL targeting schema OPSLENS.
Do NOT generate any DDL, DML, or administrative commands.
Always enforce LIMIT 1000 or lower.
Return ONLY raw SQL without markdown code blocks, explanation or preamble.

Database Schema:
{schema_context}
"""

    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_prompt}\n\nQuestion: {question}\n\nSQL:"}
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 600},
            }
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                raw_sql = data["candidates"][0]["content"]["parts"][0]["text"]
                return _clean_sql_markdown(raw_sql)

        elif provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.1,
                "max_tokens": 600,
            }
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                raw_sql = data["choices"][0]["message"]["content"]
                return _clean_sql_markdown(raw_sql)

    except Exception:
        # Silent fallback to template
        return None

    return None


def _clean_sql_markdown(text: str) -> str:
    """Strips markdown code fences (```sql ... ```) from LLM output."""
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    return clean


def generate_ask_sql(question: str, conn=None) -> Dict[str, Any]:
    """Generates SQL from natural language question with LLM provider and template fallback."""
    should_close = False
    if conn is None:
        conn = get_connection(schema="OPSLENS")
        should_close = True

    try:
        schema_context = introspect_opslens_schema(conn)
        llm_sql = call_llm_for_sql(question, schema_context)

        provider_used = "llm" if llm_sql else "template_catalog"
        is_template = llm_sql is None

        if llm_sql:
            final_sql = llm_sql
            matched_template = None
        else:
            matched_template = match_template_question(question)
            final_sql = matched_template["sql"]

        # Ensure LIMIT is present
        if "LIMIT" not in final_sql.upper():
            final_sql = final_sql.rstrip(";") + " LIMIT 1000"

        # Validate with guardrails
        guardrail_result = validate_guardrails(final_sql, conn=conn)

        return {
            "question": question,
            "sql": final_sql,
            "provider": provider_used,
            "is_template": is_template,
            "template_info": matched_template,
            "guardrails": guardrail_result,
        }
    finally:
        if should_close and conn:
            conn.close()


def execute_ask_sql(sql: str, question: Optional[str] = None, conn=None) -> Dict[str, Any]:
    """Validates and executes user/generated SQL on Exasol, recording results in OPSLENS.QUERY_STATS."""
    should_close = False
    if conn is None:
        conn = get_connection(schema="OPSLENS")
        should_close = True

    try:
        # 1. Enforce guardrails
        guardrail_res = validate_guardrails(sql, conn=conn)
        if not guardrail_res["is_safe"]:
            return {
                "success": False,
                "error": guardrail_res["summary"],
                "guardrails": guardrail_res,
                "row_count": 0,
                "duration_sec": 0.0,
                "columns": [],
                "rows": [],
            }

        # 2. Execute on Exasol
        clean_sql = sql.strip().rstrip(";")
        t0 = time.perf_counter()
        stmt = conn.execute(clean_sql)
        raw_rows = stmt.fetchall()
        duration_sec = round(time.perf_counter() - t0, 3)

        cols = list(stmt.columns().keys()) if hasattr(stmt, "columns") else [f"col_{i}" for i in range(len(raw_rows[0]) if raw_rows else 0)]
        
        # Format rows as JSON-serializable list of dicts or values
        formatted_rows = []
        for r in raw_rows[:1000]:
            row_dict = {}
            for i, c in enumerate(cols):
                val = r[i]
                if hasattr(val, "isoformat"):
                    val = str(val)
                row_dict[c] = val
            formatted_rows.append(row_dict)

        row_count = len(raw_rows)

        # 3. Save to OPSLENS.QUERY_STATS
        query_id = f"ask_{uuid.uuid4().hex[:8]}"
        q_hash = hashlib.md5(clean_sql.encode("utf-8")).hexdigest()[:16]
        est_cost = round(max(0.001, (duration_sec * 0.05) + (row_count * 0.0001)), 4)
        cpu_sec = round(max(0.01, duration_sec * 0.8), 2)

        conn.execute(f"""
            INSERT INTO OPSLENS.QUERY_STATS
            (QUERY_ID, USER_NAME, TEAM, QUERY_HASH, QUERY_TEXT, TARGET_TABLES, 
             START_TIME, DURATION_SEC, CPU_SECONDS, RAM_PEAK_MB, ROWS_RETURNED, 
             ESTIMATED_COST_USD, EXECUTION_MODE, IS_SIMULATED, CREATED_AT)
            VALUES
            ('{query_id}', 'ask_analyst', 'Analytics', '{q_hash}', 
             '{clean_sql.replace("'", "''")}', 'OPSLENS', 
             CURRENT_TIMESTAMP, {duration_sec}, {cpu_sec}, 64.0, {row_count}, 
             {est_cost}, 'INTERACTIVE_WIZARD', FALSE, CURRENT_TIMESTAMP)
        """)

        return {
            "success": True,
            "query_id": query_id,
            "sql": clean_sql,
            "row_count": row_count,
            "duration_sec": duration_sec,
            "columns": cols,
            "rows": formatted_rows,
            "guardrails": guardrail_res,
            "saved_to_query_stats": True,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "guardrails": validate_guardrails(sql, conn=conn),
            "row_count": 0,
            "duration_sec": 0.0,
            "columns": [],
            "rows": [],
        }
    finally:
        if should_close and conn:
            conn.close()
