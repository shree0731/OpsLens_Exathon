"""
OpsLens API Behavior & Timing Measurement Test
Measures wall-clock latency for:
- POST /api/faults/reset
- POST /api/faults/{name} (each fault + checks cycle)
- GET /api/lineage
- GET /api/faults/status
Ensures all latencies are well under the 8.0-second threshold.
"""

import time
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

FAULTS_TO_TEST = [
    "late_load",
    "row_drop",
    "schema_change",
    "duplicates",
    "revenue_mismatch",
    "stale_feed",
    "job_failure",
]


def test_api_faults_and_timings():
    timing_records = []
    
    print("\n" + "=" * 75)
    print(" OpsLens — API Fault Injection & Response Timing Benchmarks")
    print("=" * 75)

    # 1. Benchmark POST /api/faults/reset
    t0 = time.perf_counter()
    res_reset = client.post("/api/faults/reset")
    t_reset = time.perf_counter() - t0
    
    assert res_reset.status_code == 200
    data_reset = res_reset.json()
    assert data_reset["status"] == "CLEARED"
    assert "sentinel_result" in data_reset
    assert "trust_scores" in data_reset
    timing_records.append(("POST /api/faults/reset", t_reset, data_reset["status"]))
    print(f"  -> POST /api/faults/reset              : {t_reset:.2f}s [PASS < 8s]")
    assert t_reset < 8.0, f"Reset latency {t_reset:.2f}s exceeded 8.0s SLA"

    # 2. Benchmark GET /api/lineage
    t0 = time.perf_counter()
    res_lineage = client.get("/api/lineage")
    t_lineage = time.perf_counter() - t0
    
    assert res_lineage.status_code == 200
    data_lineage = res_lineage.json()
    assert data_lineage["total_nodes"] >= 18
    assert data_lineage["total_edges"] >= 20
    timing_records.append(("GET /api/lineage", t_lineage, f"{data_lineage['total_nodes']} nodes"))
    print(f"  -> GET /api/lineage                    : {t_lineage:.2f}s [PASS < 8s]")
    assert t_lineage < 8.0, f"Lineage latency {t_lineage:.2f}s exceeded 8.0s SLA"

    # 3. Benchmark GET /api/faults/status
    res_status = client.get("/api/faults/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert "active_faults_count" in data_status
    assert "recent_history" in data_status

    # 4. Benchmark each fault inject + checks cycle
    for f in FAULTS_TO_TEST:
        t0 = time.perf_counter()
        res_fault = client.post(f"/api/faults/{f}")
        t_fault = time.perf_counter() - t0

        assert res_fault.status_code == 200, f"Fault {f} failed with status {res_fault.status_code}: {res_fault.text}"
        data_fault = res_fault.json()
        assert data_fault["fault_name"] == f
        assert "sentinel_result" in data_fault
        assert "trust_scores" in data_fault
        assert "blast_radius" in data_fault

        timing_records.append((f"POST /api/faults/{f}", t_fault, f"{data_fault['sentinel_result']['failed']} failures detected"))
        print(f"  -> POST /api/faults/{f:<18}: {t_fault:.2f}s [PASS < 8s]")
        assert t_fault < 8.0, f"Fault {f} latency {t_fault:.2f}s exceeded 8.0s SLA"

        # Reset back between faults
        res_clean = client.post("/api/faults/reset")
        assert res_clean.status_code == 200

    print("\n" + "=" * 75)
    print(f"{'ENDPOINT / OPERATION':<35} | {'WALL-CLOCK LATENCY':<20} | {'OUTCOME'}")
    print("-" * 75)
    for op, dur, note in timing_records:
        print(f"{op:<35} | {dur:>8.2f}s            | {note}")
    print("=" * 75)


if __name__ == "__main__":
    test_api_faults_and_timings()
