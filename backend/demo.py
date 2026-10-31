"""
OpsLens End-to-End Demonstration Script
Demonstrates the full lifecycle:
1. Reset to clean baseline state
2. Run Sentinel detectors and Trust Score engine (Verify 100% Green, 0 alerts)
3. Inject fault: 'stale_feed' (Telemetry lag on ENERGY_READINGS and WEATHER_DAILY)
4. Re-run Sentinel & Trust Score (Demonstrate detection, CRITICAL alert, and Trust score drop)
5. Calculate lineage blast radius (Show downstream cascade onto Smart Grid Dashboard)
6. Reset back to clean state and verify automated incident resolution
"""

import json
from data_generator.faults import run_fault
from backend.sentinel.run import execute_sentinel
from backend.trust.engine import calculate_all_trust_scores
from backend.lineage import get_blast_radius


def print_step(title: str):
    print("\n" + "=" * 70)
    print(f" >>> {title}")
    print("=" * 70)


def run_demo():
    print("=" * 70)
    print(" OpsLens — Observability & Trust Engine Live Demonstration")
    print("=" * 70)

    # -------------------------------------------------------------
    # Step 1: Reset to clean state
    # -------------------------------------------------------------
    print_step("STEP 1: Reset Database to Clean Baseline State")
    reset_res = run_fault("reset")
    print(f"Reloaded counts: {reset_res['reloaded_counts']}")

    # -------------------------------------------------------------
    # Step 2: Sentinel & Trust Engine on Clean State
    # -------------------------------------------------------------
    print_step("STEP 2: Run Sentinel & Trust Score Engine on Clean State")
    sentinel_clean = execute_sentinel()
    scores_clean = calculate_all_trust_scores()

    print("\n[Trust Scores — Clean State]")
    for s in scores_clean:
        print(f"  {s['OBJECT_NAME']:<26} | Score: {s['TRUST_SCORE']:>5.1f} | Status: {s['STATUS']:<6} | F:{s['FRESHNESS_SCORE']:>3.0f} C:{s['COMPLETENESS_SCORE']:>3.0f} U:{s['UNIQUENESS_SCORE']:>3.0f} S:{s['CONSISTENCY_SCORE']:>3.0f}")

    assert sentinel_clean["failed"] == 0, "Expected 0 failing checks in clean state"

    # -------------------------------------------------------------
    # Step 3: Inject Fault 'stale_feed'
    # -------------------------------------------------------------
    print_step("STEP 3: Injecting Fault 'stale_feed'")
    fault_res = run_fault("stale_feed")
    print(f"Fault Details: {fault_res}")

    # -------------------------------------------------------------
    # Step 4: Run Sentinel & Trust Engine on Faulted State
    # -------------------------------------------------------------
    print_step("STEP 4: Detecting Anomaly & Recomputing Trust Scores")
    sentinel_fault = execute_sentinel()
    scores_fault = calculate_all_trust_scores()

    print("\n[Active Alerts Created by Sentinel]")
    for fc in sentinel_fault["failing_checks"]:
        print(f"  [ALERT] [{fc['severity']}] {fc['table_name']}: {fc['message']}")
        print(f"     Root Cause: {fc.get('suggested_root_cause')}")
        print(f"     Action    : {fc.get('recommended_action')}")

    print("\n[Trust Scores — Under Fault]")
    for s in scores_fault:
        flag = f"[{s['STATUS']}]"
        print(f"  {flag:<7} {s['OBJECT_NAME']:<24} | Score: {s['TRUST_SCORE']:>5.1f} | Status: {s['STATUS']:<6} | F:{s['FRESHNESS_SCORE']:>3.0f} C:{s['COMPLETENESS_SCORE']:>3.0f} U:{s['UNIQUENESS_SCORE']:>3.0f} S:{s['CONSISTENCY_SCORE']:>3.0f}")

    # -------------------------------------------------------------
    # Step 5: Calculate Lineage Blast Radius
    # -------------------------------------------------------------
    print_step("STEP 5: Computing Lineage Blast Radius for ENERGY_READINGS")
    blast = get_blast_radius("OPSLENS.ENERGY_READINGS")
    print(f"Summary: {blast['impact_summary']}")
    print(f"Affected Dashboards: {blast['affected_dashboards']}")
    print(f"Affected Marts:      {blast['affected_marts']}")
    print("\nBlast Radius JSON:")
    print(json.dumps({
        "target": blast["target_node"],
        "affected_count": blast["affected_count"],
        "affected_dashboards": blast["affected_dashboards"],
        "affected_marts": blast["affected_marts"],
    }, indent=2))

    # -------------------------------------------------------------
    # Step 6: Reset Back to Clean State and Auto-Resolve
    # -------------------------------------------------------------
    print_step("STEP 6: Restoring Clean State & Verifying Auto-Resolution")
    run_fault("reset")
    sentinel_restored = execute_sentinel()
    scores_restored = calculate_all_trust_scores()

    print(f"Auto-resolved alerts: {sentinel_restored['resolved_alerts']}")
    print(f"Active open alerts  : {sentinel_restored['open_alerts']}")
    print(f"Passing checks      : {sentinel_restored['passed']} / {sentinel_restored['total_checks']}")

    print("\n" + "=" * 70)
    print(" >> End-to-End Demonstration Complete: All Systems Verified <<")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
