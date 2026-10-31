# OpsLens — Problem Statement

**Exathon 2026 | Track 04: Operational Intelligence & Query Observability**  
**Team 404**: Shreepurnaa V  
**Repository**: [https://github.com/shree0731/OpsLens_Exathon](https://github.com/shree0731/OpsLens_Exathon)  
**Pitch Deck**: [Google Slides / PPT](https://docs.google.com/presentation/d/1VBVs-IdfjDUDN7AQu7Hzh_8jVjnHdRqL/edit?usp=sharing&ouid=110330912071145646436&rtpof=true&sd=true) | [docs/OpsLens_Pitch_Deck.pdf](OpsLens_Pitch_Deck.pdf)  
**Demo Video**: [Google Drive](https://drive.google.com/file/d/1V59pWLqsvTiOrrAqUBy4HY0FyUB-to8r/view?usp=sharing)

---

## 1. Who Has the Problem?

Modern data-driven enterprises rely on complex, multi-stage data pipelines feeding analytical marts and executive dashboards. This operational environment involves four key stakeholders who suffer when data pipelines break silently:

1. **Data Engineers:** Suffer from nocturnal pipeline breaks, ambiguous failures, cryptic SQL exceptions, and lack of automated alerts until business stakeholders complain.
2. **Analytics Engineers & BI Analysts:** Face broken reports, unexpected schema drift, or silent reconciliation gaps (e.g., order totals diverging from line-item transaction sums) without knowing whether upstream extracts failed.
3. **Finance, Operations, and Business Executives:** Make high-stakes strategic decisions on delayed or corrupted numbers, eroding confidence in internal data infrastructure.
4. **Data Platform Owners & FinOps Leads:** Battle cloudy, opaque data warehouse bills, uncontrolled repetitive queries, and unqueried "zombie" tables consuming memory and storage.

---

## 2. The Four Track 04 Pain Points

### Pain Point 1: Silent Pipeline Failures & Stale Dashboards
* **The Reality:** Data pipelines often experience silent dropouts: smart meter feeds lag behind by hundreds of hours, upstream ERP syncs drop 40% of transaction rows, or nightly transformation jobs fail during intermediate stages.
* **The Impact:** Dashboards continue rendering outdated or partial data with zero indication of staleness. Business teams make operational decisions based on incomplete metrics without realizing the data is corrupted.

### Pain Point 2: Lack of Continuous Quality Sentinel & Alert Fatigue
* **The Reality:** Most monitoring relies either on static schema assertions or deluge-heavy alert notifications that wake engineers for trivial variances while missing critical volume drops and duplicate primary keys.
* **The Impact:** Engineers either mute monitoring channels (alert fatigue) or discover data discrepancies days or weeks after corrupted data has permeated downstream marts.

### Pain Point 3: Blast Radius Blindness & Upstream Root-Cause Obscurity
* **The Reality:** When an executive dashboard turns red, tracing the root cause requires hours of manually inspecting DAG files, dbt logs, and database tables. Conversely, when an ingestion feed stales, operators cannot immediately tell which specific downstream marts and dashboards are affected and which remain safe.
* **The Impact:** Extended Mean Time to Detection (MTTD) and Mean Time to Resolution (MTTR). Critical dashboards are distrusted, while incident triaging demands cross-functional firefighting.

### Pain Point 4: Cloud Data Warehouse Cost Opacity & Inefficient Queries
* **The Reality:** Analytical warehouses execute thousands of ad-hoc queries, automated refreshes, and un-optimized joins. Without query-level fingerprinting, teams cannot attribute compute expenses to specific teams or identify repetitive heavy queries.
* **The Impact:** Runaway compute expenditure, wasted cluster memory on cold, unqueried tables, and lack of accountability across departments.

---

## 3. How OpsLens Solves Each Pain Point

OpsLens delivers an end-to-end operational intelligence and query observability dashboard natively powered by **Exasol Personal Edition**:

| Track 04 Pain Point | OpsLens Solution | Observed Outcome |
|---|---|---|
| **1. Silent Failures & Stale Data** | **Pipeline Sentinel & Reference Clock** | Continuous 21-point automated checks evaluating row counts, freshness watermarks against fixed historical reference clocks, null rates, and financial reconciliation. |
| **2. Alert Fatigue & Distrust** | **Multi-Dimensional Trust Score Engine** | Mathematical trust index (0–100%) weighting Freshness (30%), Completeness (20%), Uniqueness (20%), and Consistency (30%), combined with automated alert resolution. |
| **3. Blast Radius Blindness** | **Interactive Lineage DAG & Blast Radius Traversal** | Directed acyclic graph with topological traversal identifying exact downstream impacted marts, dashboards, and scheduled jobs, while proving isolation for unaffected pipelines. |
| **4. Cost Opacity & Waste** | **Workload Cost Radar & Savings Engine** | Query fingerprinting, team-level cost attribution, automated cold-table scanning, and concrete savings recommendations backed by Exasol system performance. |

---

## 4. Why Exasol Personal Edition?

Exasol's in-memory columnar database engine provides sub-second multi-table analytical joins and real-time aggregation across hundreds of thousands of records. OpsLens harnesses Exasol's native analytical speed to run continuous Sentinel checks and compute topological blast radii dynamically without adding infrastructure overhead or degrading operational query performance.
