# OpsLens — 3-Minute Demo Video Script & Shot List

**Exathon 2026 | Track 04: Operational Intelligence & Query Observability**  
**Demo Video URL**: [Google Drive Video](https://drive.google.com/file/d/1V59pWLqsvTiOrrAqUBy4HY0FyUB-to8r/view?usp=sharing)  
**Pitch Deck**: [Google Slides Presentation](https://docs.google.com/presentation/d/1VBVs-IdfjDUDN7AQu7Hzh_8jVjnHdRqL/edit?usp=sharing&ouid=110330912071145646436&rtpof=true&sd=true)
**Pages Used**: `/lineage`, `/timeline`, `/runs`  

---

## Shot List & Narration Plan

```
[00:00 - 00:30] Introduction, Architecture & Baseline Health (/lineage)
[00:30 - 01:10] Ingesting Stale Feed & Blast Radius Isolation (/lineage)
[01:10 - 01:45] Root Cause Deep-Dive & SidePanel Diagnostics (/lineage)
[01:45 - 02:15] Incident Timeline & Alert Auditing (/timeline)
[02:15 - 02:40] Overnight Pipeline Orchestration & Stage Failure (/runs)
[02:40 - 03:00] Autonomous Remediation & Exasol Summary (/lineage)
```

---

### Act 1: Introduction, Architecture & Baseline Health (00:00 – 00:30)
* **Screen:** Open browser at `http://localhost:5173/lineage`.
* **Action:** Show the full interactive DAG rendered with `@xyflow/react`. Point to the 20 nodes organized cleanly: Raw Feeds $\to$ Ingestion Jobs $\to$ Tables $\to$ Transformation Marts $\to$ Executive Dashboards.
* **Narration:**
  > *"Welcome to OpsLens, an operational intelligence and query observability dashboard built for Exathon Track 04, powered natively by Exasol Personal Edition.*  
  > *In production, data pipelines break silently—smart meters lag, transaction extracts drop rows, and downstream dashboards display misleading figures.*  
  > *OpsLens solves this. Here on our Lineage view, we see our entire data topology. All 20 assets are currently in a pristine state—each node displays a 100% green Trust Score, evaluated continuously across freshness, completeness, uniqueness, and consistency."*

---

### Act 2: Fault Injection & Blast Radius Isolation (00:30 – 01:10)
* **Screen:** Top floating fault toolbar on `/lineage`.
* **Action:** Select `Stale Feed` from the fault dropdown and click **Inject Fault**. Watch the DAG animate in under 2 seconds.
* **Visual Change:** `ENERGY_READINGS`, `GRID_OPS_MART`, and `Smart Grid Dashboard` degrade to **RED/AMBER**. Crucially, `ORDERS`, `REVENUE_MART`, and `Revenue Dashboard` remain **100% GREEN**.
* **Narration:**
  > *"Let's simulate a real-world disaster: an upstream IoT collector fails, and our smart meter feed lags behind by 336 hours.*  
  > *Instantly, our Sentinel engine detects the lag against our calibrated reference clock. Notice the intelligent blast radius isolation: the Energy readings, Grid Ops Mart, and Smart Grid Dashboard immediately degrade to Red.*  
  > *However, our financial pipeline—Orders, Lineitem, and the Executive Revenue Dashboard—remains completely untouched and Green. OpsLens eliminates alert panic by proving blast radius boundaries."*

---

### Act 3: SidePanel Root-Cause & Remediation (01:10 – 01:45)
* **Screen:** Click on the degraded `Smart Grid Dashboard` node.
* **Action:** The right-hand SlidePanel opens smoothly.
* **Visual Details:** Show the multi-dimensional breakdown: Freshness = 0%, Completeness = 68.9%, Uniqueness = 100%, Consistency = 100%. Highlight the **Inherited Alerts** section and the **Recommended Action**.
* **Narration:**
  > *"When an on-call engineer inspects the Smart Grid Dashboard, they don't have to guess why it's degraded. OpsLens provides instant multidimensional diagnostics: Freshness is at 0%.*  
  > *Under Inherited Alerts, OpsLens points directly upstream to the culprit: ENERGY_READINGS. It displays the exact discrepancy: expected latest timestamp March 31st versus observed March 17th, along with actionable remediation instructions to inspect the IoT gateway."*

---

### Act 4: Observability Timeline & Incident Lifecycle (01:45 – 02:15)
* **Screen:** Click on **Timeline** in the sidebar navigation (`/timeline`).
* **Action:** Show the chronologically sorted event feed with severity filters (Critical, Warning, Info). Filter by 'ALERT'.
* **Narration:**
  > *"Switching to the Observability Timeline, data teams get a real-time event log tracking every anomaly, alert firing, and resolution event.*  
  > *Each entry captures observed versus expected thresholds, z-score statistical variances, and affected table assets. This replaces chaotic Slack threads with an auditable incident ledger."*

---

### Act 5: Pipeline Runs & Calendar Heatmap (02:15 – 02:40)
* **Screen:** Click on **Pipeline Runs** in the sidebar navigation (`/runs`).
* **Action:** Hover over the 30-day calendar heatmap. Show the multi-stage pipeline breakdown (`extract` $\to$ `load` $\to$ `validate` $\to$ `transform` $\to$ `publish`). Click on a run to reveal the stage timing bar.
* **Narration:**
  > *"On the Pipeline Runs page, OpsLens monitors nightly batch workflows across 6 core pipeline jobs.*  
  > *The interactive stage bar visualizes durations and data volumes stage by stage. If a transform stage encounters an Out-Of-Memory failure or late load, downstream publishing is automatically halted to prevent corrupting executive marts."*

---

### Act 6: Autonomous Remediation & Exasol Engine Power (02:40 – 03:00)
* **Screen:** Return to `/lineage` and click the **Reset** (🔄) button.
* **Action:** Watch the lineage graph automatically re-run Sentinel checks and turn 100% Green across all 20 nodes.
* **Narration:**
  > *"When the incident is resolved, we click Reset. In under 5 seconds, OpsLens restores clean state, auto-resolves all open alerts, and recomputes trust scores back to 100% Green.*  
  > *All of this is made possible by Exasol Personal Edition: its in-memory columnar engine performs sub-second cross-table aggregations, enabling real-time observability at enterprise scale without adding infrastructure overhead.*  
  > *Thank you. This is OpsLens—bringing crystal-clear trust to your data pipelines."*
