# OpsLens Data Generator

The Data Generator populates the `OPSLENS` schema with production replicas, synthetic pipeline metadata, lineage graphs, and query workloads, while ensuring source schemas (`TPCH`, `ENERGY`, `WEATHER`, `SCHED`, `STARTER_KIT`) remain strictly read-only.

---

## 1. Modules

* `setup_data.py`: Idempotently creates schema `OPSLENS` and copies production tables (`ORDERS`, `LINEITEM`, `CUSTOMER`, `ENERGY_READINGS`, `ENERGY_METERS`, `WEATHER_DAILY`) and analytical data marts (`REVENUE_MART`, `GRID_OPS_MART`).
* `metadata_generator.py`: Generates 60 days of simulated nightly pipeline runs across 6 jobs (`load_orders`, `load_lineitem`, `load_energy`, `load_weather`, `build_revenue_mart`, `publish_dashboards`) with sequential stages, realistic variances, and historical blips, plus hand-crafted lineage graph edges (`LINEAGE_EDGES`), check results, alerts, trust scores, and baselines.
* `workload_generator.py`: Generates query telemetry in `QUERY_STATS` across teams (`finance`, `ops`, `analytics`), including repeated heavy scans and unused table tracking for Cost Radar.
* `faults.py`: CLI Fault Injector to simulate data incidents and test observability rules without corrupting source data.

---

## 2. Running Data Generation

```bash
# Run complete setup and workload generation
python -m data_generator.main
```

---

## 3. Fault Injector CLI

Inject data quality anomalies and pipeline failures:

```bash
# Ingest delay SLA breach
python -m data_generator.faults late_load

# Drop 40% of rows from OPSLENS.ORDERS
python -m data_generator.faults row_drop

# Add unexpected column to OPSLENS.ORDERS
python -m data_generator.faults schema_change

# Insert duplicate records into OPSLENS.LINEITEM
python -m data_generator.faults duplicates

# Mutate prices creating financial discrepancy between ORDERS and LINEITEM
python -m data_generator.faults revenue_mismatch

# Truncate recent 14 days of telemetry to freeze feed advancement
python -m data_generator.faults stale_feed

# Simulate OOM hash join failure during mart build
python -m data_generator.faults job_failure

# Reload all production tables from source schemas and clear all faults
python -m data_generator.faults reset
```
