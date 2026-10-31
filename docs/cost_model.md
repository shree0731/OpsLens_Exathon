# OpsLens Cloud Compute Cost Model

**Exathon 2026 Track 04**  
Operational Intelligence and Workload Analytics on Exasol Personal Edition.

---

## 1. Overview

The OpsLens Cost Radar provides resource attribution and expenditure modeling for analytical workloads executing on Exasol. The cost formula translates query runtime execution metrics (CPU consumption, RAM footprint, and wall-clock duration) into normalized cloud data warehouse cost units (USD).

---

## 2. Mathematical Cost Formulation

For any executed or simulated query $q$:

$$\text{Query Cost} = (\text{CPU\_Seconds} \times C_{\text{cpu}}) + (\text{RAM\_Peak\_MB} \times \text{Duration\_Sec} \times C_{\text{ram}}) + C_{\text{base}}$$

Where the calibrated coefficients represent typical enterprise cloud compute pricing:
- **$C_{\text{cpu}} = \$0.0006$ per CPU-second** (derived from standard 16-vCPU analytical cluster tier).
- **$C_{\text{ram}} = \$0.000002$ per MB-second** ($\$0.002$ per GB-second of active memory usage).
- **$C_{\text{base}} = \$0.0001$ query transaction overhead** (connection initiation, compiler optimization, and catalog lookups).

---

## 3. Team Cost Attribution

Every query recorded in `OPSLENS.QUERY_STATS` carries the submitting team attribution:
- **Finance**: Monthly revenue rollups, cross-table order and lineitem reconciliation, audit queries.
- **Operations (Ops)**: Smart grid meter aggregations, hourly telemetry ingestion checks, grid stability reports.
- **Analytics**: Ad-hoc discovery, customer 360 slicing, and executive dashboard queries.

---

## 4. Telemetry Source Prioritization

OpsLens checks Exasol system statistics views before falling back to simulated historical records:
1. **Real Telemetry**:
   - `EXA_STATISTICS.EXA_SQL_DAILY`: Aggregated historical commands, CPU, RAM peak, and HDD throughput.
   - `EXA_STATISTICS.EXA_USAGE_DAILY`: Hourly and daily cluster concurrent query volume and idle capacity.
2. **Simulated Workload**:
   - `OPSLENS.QUERY_STATS`: Seeded with 1,500 historical queries across 30 days (`IS_SIMULATED = TRUE`) to demonstrate long-term cost trends, repeated heavy query identification, and unused table detection.
   - User questions executed via **Ask-the-Warehouse** (`/ask`) are dynamically inserted with `IS_SIMULATED = FALSE`.
