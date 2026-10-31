"""
Unit tests for data generator components, jobs, lineage, and fault maps.
"""

from data_generator.faults import FAULTS_MAP
from data_generator.metadata_generator import JOBS_DEF, LINEAGE_EDGES_DATA
from data_generator.workload_generator import calculate_query_cost, QUERY_TEMPLATES


def test_faults_map_completeness():
    expected_faults = {
        "late_load",
        "row_drop",
        "schema_change",
        "duplicates",
        "revenue_mismatch",
        "stale_feed",
        "job_failure",
        "reset",
    }
    assert set(FAULTS_MAP.keys()) == expected_faults


def test_jobs_definitions():
    assert len(JOBS_DEF) == 6
    job_ids = [j["id"] for j in JOBS_DEF]
    assert "load_orders" in job_ids
    assert "load_lineitem" in job_ids
    assert "load_energy" in job_ids
    assert "load_weather" in job_ids
    assert "build_revenue_mart" in job_ids
    assert "publish_dashboards" in job_ids

    for job in JOBS_DEF:
        assert job["runtime_sec"] > 0
        assert len(job["stages"]) >= 3


def test_lineage_edges():
    assert len(LINEAGE_EDGES_DATA) >= 20
    node_types = {e[1] for e in LINEAGE_EDGES_DATA} | {e[4] for e in LINEAGE_EDGES_DATA}
    assert "FEED" in node_types
    assert "JOB" in node_types
    assert "TABLE" in node_types
    assert "MART" in node_types
    assert "DASHBOARD" in node_types


def test_workload_cost_calculation():
    cost = calculate_query_cost(cpu_sec=100.0, ram_mb=200.0, duration_sec=10.0)
    assert cost > 0
    # $0.0006 * 100 + $0.000002 * 2000 + $0.0001 = 0.06 + 0.004 + 0.0001 = 0.0641
    assert round(cost, 4) == 0.0641


def test_query_templates_targets():
    all_targets = [t["target_tables"] for t in QUERY_TEMPLATES]
    targets_str = " ".join(all_targets)
    assert "OPSLENS.ORDERS" in targets_str
    assert "OPSLENS.LINEITEM" in targets_str
    assert "OPSLENS.ENERGY_READINGS" in targets_str
    # ENERGY_METERS is intentionally omitted so Cost Radar can detect it as unused
    assert "OPSLENS.ENERGY_METERS" not in targets_str
