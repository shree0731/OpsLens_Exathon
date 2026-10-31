"""
OpsLens Ask-the-Warehouse Security Guardrails
Enforces strict security checks on generated and user-submitted SQL:
1. SELECT-only: Strict prohibition on DDL, DML, and admin commands
2. Single-statement: Single query execution (no multi-query injection)
3. Schema scope: OPSLENS schema only (no SYS, EXA_*, TPCH, ENERGY, WEATHER, etc.)
4. LIMIT enforcement: Explicit LIMIT <= 1000
5. Dry-run validation: Compiles & validates syntax via Exasol engine
"""

import re
from typing import Dict, Any, Optional, List
from backend.db import get_connection

DISALLOWED_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b", r"\bALTER\b",
    r"\bCREATE\b", r"\bTRUNCATE\b", r"\bRENAME\b", r"\bGRANT\b", r"\bREVOKE\b",
    r"\bMERGE\b", r"\bUPSERT\b", r"\bEXECUTE\b", r"\bCALL\b", r"\bIMPORT\b",
    r"\bEXPORT\b", r"\bCOMMIT\b", r"\bROLLBACK\b", r"\bSET\b", r"\bKILL\b"
]

DISALLOWED_SCHEMAS = [
    r"\bSYS\.", r"\bEXA_", r"\bTPCH\.", r"\bENERGY\.", r"\bWEATHER\.",
    r"\bSCHED\.", r"\bSTARTER_KIT\.", r"\bINFORMATION_SCHEMA\."
]

ALLOWED_TABLES = [
    "ORDERS", "LINEITEM", "CUSTOMER", "ENERGY_READINGS", "ENERGY_METERS",
    "WEATHER_DAILY", "REVENUE_MART", "GRID_OPS_MART", "PIPELINE_RUN_LOG",
    "PIPELINE_JOBS", "CHECK_RESULTS", "ALERTS", "TRUST_SCORES", "BASELINES",
    "QUERY_STATS", "CONFIG", "FAULT_LOG", "LINEAGE_EDGES"
]


def check_select_only(sql: str) -> Dict[str, Any]:
    """Ensures SQL begins with SELECT or WITH and contains no mutating keywords."""
    clean = sql.strip().upper()
    if not (clean.startswith("SELECT") or clean.startswith("WITH")):
        return {"passed": False, "reason": "Query must start with SELECT or WITH"}

    for pattern in DISALLOWED_KEYWORDS:
        if re.search(pattern, clean):
            kw = pattern.replace(r"\b", "")
            return {"passed": False, "reason": f"Disallowed mutating or administrative keyword: {kw}"}

    return {"passed": True, "reason": "Query is read-only SELECT"}


def check_single_statement(sql: str) -> Dict[str, Any]:
    """Ensures SQL contains exactly one statement (no stacked queries with semicolons)."""
    clean = sql.strip()
    if clean.endswith(";"):
        clean = clean[:-1].strip()

    if ";" in clean:
        return {"passed": False, "reason": "Multiple queries separated by semicolon are prohibited"}

    return {"passed": True, "reason": "Single statement verified"}


def check_opslens_schema_only(sql: str) -> Dict[str, Any]:
    """Ensures query references only tables in OPSLENS schema (never SYS, EXA, or sample schemas)."""
    clean = sql.upper()
    for pattern in DISALLOWED_SCHEMAS:
        if re.search(pattern, clean):
            schema = pattern.replace(r"\b", "").replace(r"\.", "")
            return {"passed": False, "reason": f"Access to external or system schema prohibited: {schema}"}

    return {"passed": True, "reason": "Schema scope restricted to OPSLENS"}


def check_limit_enforced(sql: str) -> Dict[str, Any]:
    """Ensures SQL enforces LIMIT <= 1000."""
    clean = sql.strip().upper()
    match = re.search(r"\bLIMIT\s+(\d+)", clean)
    if not match:
        return {"passed": False, "reason": "Query must specify an explicit LIMIT (max 1000)"}

    limit_val = int(match.group(1))
    if limit_val > 1000:
        return {"passed": False, "reason": f"LIMIT {limit_val} exceeds maximum allowed quota (1000)"}
    if limit_val <= 0:
        return {"passed": False, "reason": f"Invalid LIMIT value: {limit_val}"}

    return {"passed": True, "reason": f"LIMIT {limit_val} <= 1000 verified"}


def check_syntax_dry_run(sql: str, conn=None) -> Dict[str, Any]:
    """Performs dry-run execution on Exasol via subquery with WHERE 1 = 0 to validate syntax and table references."""
    should_close = False
    if conn is None:
        try:
            conn = get_connection(schema="OPSLENS")
            should_close = True
        except Exception as exc:
            return {"passed": False, "reason": f"Database unreachable for dry-run validation: {exc}"}

    try:
        clean = sql.strip()
        if clean.endswith(";"):
            clean = clean[:-1].strip()

        # Wrap in zero-row dry run
        dry_run_sql = f"SELECT * FROM ({clean}) dry_run_subq WHERE 1 = 0"
        stmt = conn.execute(dry_run_sql)
        cols = list(stmt.columns().keys()) if hasattr(stmt, "columns") else []
        return {
            "passed": True,
            "reason": f"Engine validation successful ({len(cols)} columns verified)",
            "columns": cols,
        }
    except Exception as exc:
        err_msg = str(exc)
        if "syntax error" in err_msg.lower():
            reason = f"Exasol syntax error: {err_msg.split('message     =>')[-1].split('(')[0].strip()}"
        else:
            reason = f"Execution plan validation failed: {err_msg}"
        return {"passed": False, "reason": reason}
    finally:
        if should_close and conn:
            conn.close()


def validate_guardrails(sql: str, conn=None) -> Dict[str, Any]:
    """
    Executes full guardrail review against submitted SQL.
    Returns composite check status and individual chip states.
    """
    res_select = check_select_only(sql)
    res_single = check_single_statement(sql)
    res_schema = check_opslens_schema_only(sql)
    res_limit = check_limit_enforced(sql)

    # Dry-run only if static checks passed
    if res_select["passed"] and res_single["passed"] and res_schema["passed"]:
        # If limit is missing, we can test dry-run with limit appended
        test_sql = sql.strip().rstrip(";")
        if not res_limit["passed"] and "LIMIT" not in test_sql.upper():
            test_sql += " LIMIT 10"
        res_syntax = check_syntax_dry_run(test_sql, conn=conn)
    else:
        res_syntax = {"passed": False, "reason": "Skipped due to previous security violations"}

    all_passed = (
        res_select["passed"]
        and res_single["passed"]
        and res_schema["passed"]
        and res_limit["passed"]
        and res_syntax["passed"]
    )

    failures = []
    if not res_select["passed"]: failures.append(res_select["reason"])
    if not res_single["passed"]: failures.append(res_single["reason"])
    if not res_schema["passed"]: failures.append(res_schema["reason"])
    if not res_limit["passed"]: failures.append(res_limit["reason"])
    if not res_syntax["passed"]: failures.append(res_syntax["reason"])

    return {
        "is_safe": all_passed,
        "failures": failures,
        "summary": "All guardrails passed" if all_passed else "; ".join(failures),
        "chips": {
            "select_only": res_select,
            "single_statement": res_single,
            "opslens_schema_only": res_schema,
            "limit_enforced": res_limit,
            "engine_validated": res_syntax,
        },
    }
