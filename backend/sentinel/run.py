"""
OpsLens Pipeline Sentinel — Runner & Alert Manager
Executes detectors, records check results in OPSLENS.CHECK_RESULTS,
and manages alert lifecycles (OPEN, UPDATED, AUTO-RESOLVED) in OPSLENS.ALERTS.
Supports Slack webhook alerting and local file logging.

Usage:
  python -m backend.sentinel.run --once
"""

import sys
import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

from backend.db import get_connection
from backend.sentinel.detectors import run_all_detectors


def send_slack_notification(webhook_url: str, alert: Dict[str, Any]):
    """Sends an incident notification to a Slack webhook if configured."""
    if not webhook_url or not webhook_url.startswith("http"):
        return

    color = "#E01E5A" if alert["SEVERITY"] == "CRITICAL" else "#ECB22E"
    payload = {
        "text": f"🚨 *[OpsLens Sentinel]* {alert['SEVERITY']} Alert: {alert['INCIDENT_TYPE']}",
        "attachments": [
            {
                "color": color,
                "title": alert["SUMMARY"],
                "fields": [
                    {"title": "Target Object", "value": alert["TARGET_OBJECT"], "short": True},
                    {"title": "Severity", "value": alert["SEVERITY"], "short": True},
                    {"title": "Suggested Root Cause", "value": alert.get("SUGGESTED_ROOT_CAUSE", "N/A"), "short": False},
                    {"title": "Recommended Action", "value": alert.get("RECOMMENDED_ACTION", "N/A"), "short": False},
                ],
                "footer": "OpsLens Sentinel Anomaly Engine",
                "ts": int(datetime.now().timestamp()),
            }
        ],
    }
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as exc:
        print(f"  [WARN] Failed to dispatch Slack notification: {exc}")


def log_alert_to_file(alert: Dict[str, Any]):
    """Appends alert entry to logs/alerts.log."""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "alerts.log")
        ts = datetime.now().isoformat()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{alert['SEVERITY']}] [{alert['STATUS']}] {alert['INCIDENT_TYPE']} | {alert['TARGET_OBJECT']} | {alert['SUMMARY']}\n")
    except Exception:
        pass


def execute_sentinel(conn=None) -> Dict[str, Any]:
    """
    Executes a complete Sentinel cycle:
    1. Runs all detectors
    2. Writes results to OPSLENS.CHECK_RESULTS
    3. Upserts active alerts and auto-resolves recovered incidents in OPSLENS.ALERTS
    4. Triggers Slack / log notifications
    """
    should_close = False
    if conn is None:
        conn = get_connection(schema="OPSLENS")
        should_close = True

    try:
        print("\n" + "=" * 65)
        print(f" OpsLens Sentinel — Executing Detection Cycle ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print("=" * 65)

        # 1. Run all detectors
        check_results = run_all_detectors(conn)
        
        # 2. Persist to CHECK_RESULTS (truncate existing or overwrite)
        conn.execute("TRUNCATE TABLE OPSLENS.CHECK_RESULTS")
        if check_results:
            val_clauses = []
            for chk in check_results:
                msg = chk["message"].replace("'", "''")[:950]
                exp_val = str(chk.get("expected_value", "")).replace("'", "''")[:250]
                act_val = str(chk.get("actual_value", "")).replace("'", "''")[:250]
                chk_name = chk["check_name"].replace("'", "''")[:120]
                tbl_name = chk["table_name"][:60]
                val_clauses.append(
                    f"('{chk['check_id']}', '{chk_name}', '{tbl_name}', '{chk['check_type']}', "
                    f"'{chk['severity']}', '{chk['status']}', '{exp_val}', '{act_val}', '{msg}', CURRENT_TIMESTAMP, TRUE)"
                )
            insert_chk_sql = f"""
                INSERT INTO OPSLENS.CHECK_RESULTS 
                (CHECK_ID, CHECK_NAME, TABLE_NAME, CHECK_TYPE, SEVERITY, STATUS, EXPECTED_VALUE, ACTUAL_VALUE, MESSAGE, EXECUTED_AT, IS_SIMULATED)
                VALUES {', '.join(val_clauses)}
            """
            conn.execute(insert_chk_sql)

        # 3. Retrieve current OPEN alerts
        open_alerts_rows = conn.execute("""
            SELECT ALERT_ID, INCIDENT_TYPE, TARGET_OBJECT, SEVERITY, STATUS 
            FROM OPSLENS.ALERTS 
            WHERE STATUS = 'OPEN'
        """).fetchall()
        open_alerts_map = {(r[1], r[2]): r[0] for r in open_alerts_rows}

        failed_checks = [c for c in check_results if c["status"] == "FAIL"]
        passed_checks = [c for c in check_results if c["status"] == "PASS"]

        slack_url = os.getenv("SLACK_WEBHOOK_URL", "")

        active_incidents = set()
        new_alerts = []
        updated_alerts = []

        # Process Failures -> Upsert Alerts
        for fc in failed_checks:
            inc_type = fc.get("incident_type") or fc["check_type"]
            target_obj = fc["table_name"]
            key = (inc_type, target_obj)
            active_incidents.add(key)

            summary = fc["message"].replace("'", "''")[:480]
            details = f"Expected: {fc.get('expected_value', 'N/A')} | Actual: {fc.get('actual_value', 'N/A')}".replace("'", "''")[:1950]
            root_cause = (fc.get("suggested_root_cause") or "System anomaly detected.").replace("'", "''")[:950]
            rec_action = (fc.get("recommended_action") or "Investigate table logs.").replace("'", "''")[:950]

            if key in open_alerts_map:
                # Update existing OPEN alert
                alert_id = open_alerts_map[key]
                conn.execute(f"""
                    UPDATE OPSLENS.ALERTS 
                    SET LAST_SEEN = CURRENT_TIMESTAMP,
                        SUMMARY = '{summary}',
                        DETAILS = '{details}',
                        SUGGESTED_ROOT_CAUSE = '{root_cause}',
                        RECOMMENDED_ACTION = '{rec_action}'
                    WHERE ALERT_ID = '{alert_id}'
                """)
                updated_alerts.append(alert_id)
            else:
                # Insert new OPEN alert
                new_id = f"alt_{uuid.uuid4().hex[:12]}"
                conn.execute(f"""
                    INSERT INTO OPSLENS.ALERTS 
                    (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, 
                     SUGGESTED_ROOT_CAUSE, RECOMMENDED_ACTION, STATUS, FIRST_SEEN, LAST_SEEN, IS_SIMULATED)
                    VALUES 
                    ('{new_id}', '{inc_type}', '{fc["severity"]}', '{target_obj}', '{summary}', '{details}', 
                     '{root_cause}', '{rec_action}', 'OPEN', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE)
                """)
                alert_dict = {
                    "ALERT_ID": new_id,
                    "INCIDENT_TYPE": inc_type,
                    "SEVERITY": fc["severity"],
                    "TARGET_OBJECT": target_obj,
                    "SUMMARY": fc["message"][:480],
                    "SUGGESTED_ROOT_CAUSE": root_cause,
                    "RECOMMENDED_ACTION": rec_action,
                    "STATUS": "OPEN",
                }
                new_alerts.append(alert_dict)
                send_slack_notification(slack_url, alert_dict)
                log_alert_to_file(alert_dict)

        # Auto-resolve alerts that are no longer failing
        resolved_count = 0
        for (inc_type, target_obj), alert_id in open_alerts_map.items():
            if (inc_type, target_obj) not in active_incidents:
                conn.execute(f"""
                    UPDATE OPSLENS.ALERTS 
                    SET STATUS = 'RESOLVED', RESOLVED_AT = CURRENT_TIMESTAMP 
                    WHERE ALERT_ID = '{alert_id}'
                """)
                resolved_count += 1
                res_alert = {
                    "ALERT_ID": alert_id,
                    "INCIDENT_TYPE": inc_type,
                    "SEVERITY": "INFO",
                    "TARGET_OBJECT": target_obj,
                    "SUMMARY": f"Incident {inc_type} auto-resolved. Target object is healthy.",
                    "STATUS": "RESOLVED"
                }
                log_alert_to_file(res_alert)

        # Summary output
        pass_count = len(passed_checks)
        fail_count = len(failed_checks)
        print(f"\n>> Sentinel Execution Summary:")
        print(f"   Total Checks Executed : {len(check_results)}")
        print(f"   Passing Checks        : {pass_count}")
        print(f"   Failing Checks        : {fail_count}")
        print(f"   New Alerts Opened     : {len(new_alerts)}")
        print(f"   Existing Alerts Active: {len(updated_alerts)}")
        print(f"   Alerts Auto-Resolved  : {resolved_count}")

        if fail_count > 0:
            print("\n>> Active Incidents Detected:")
            for fc in failed_checks:
                print(f"   [{fc['severity']}] {fc['table_name']}: {fc['message']}")

        return {
            "total_checks": len(check_results),
            "passed": pass_count,
            "failed": fail_count,
            "new_alerts": len(new_alerts),
            "open_alerts": len(updated_alerts) + len(new_alerts),
            "resolved_alerts": resolved_count,
            "failing_checks": failed_checks,
        }

    finally:
        if should_close and conn:
            conn.close()


def main():
    once = "--once" in sys.argv or len(sys.argv) == 1
    execute_sentinel()


if __name__ == "__main__":
    main()
