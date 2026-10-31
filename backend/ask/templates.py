"""
OpsLens Ask-the-Warehouse Template Questions and Hand-crafted SQL
Provides instant zero-shot query resolution and deterministic fallbacks.
"""

from typing import List, Dict, Any

TEMPLATE_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "revenue_by_month",
        "question": "What is our monthly revenue trend?",
        "summary": "Monthly aggregated order volume and total revenue from OPSLENS.ORDERS.",
        "sql": """SELECT 
    SUBSTR(CAST(O_ORDERDATE AS VARCHAR(32)), 1, 7) AS ORDER_MONTH,
    COUNT(*) AS TOTAL_ORDERS,
    ROUND(SUM(O_TOTALPRICE), 2) AS TOTAL_REVENUE,
    ROUND(AVG(O_TOTALPRICE), 2) AS AVG_ORDER_VALUE
FROM OPSLENS.ORDERS
GROUP BY 1
ORDER BY 1 DESC
LIMIT 100""",
    },
    {
        "id": "top_customers",
        "question": "Who are our top 10 customers by total spend?",
        "summary": "Top 10 customer accounts ranked by aggregate order expenditure.",
        "sql": """SELECT 
    C.C_CUSTKEY AS CUSTOMER_ID,
    C.C_NAME AS CUSTOMER_NAME,
    C.C_MKTSEGMENT AS SEGMENT,
    COUNT(O.O_ORDERKEY) AS ORDER_COUNT,
    ROUND(SUM(O.O_TOTALPRICE), 2) AS TOTAL_SPENT
FROM OPSLENS.CUSTOMER C
JOIN OPSLENS.ORDERS O ON C.C_CUSTKEY = O.O_CUSTKEY
GROUP BY C.C_CUSTKEY, C.C_NAME, C.C_MKTSEGMENT
ORDER BY TOTAL_SPENT DESC
LIMIT 10""",
    },
    {
        "id": "daily_orders",
        "question": "What is the daily order volume and average order value?",
        "summary": "Daily order transaction volume and average ticket size.",
        "sql": """SELECT 
    CAST(O_ORDERDATE AS VARCHAR(10)) AS ORDER_DATE,
    COUNT(*) AS ORDERS_PLACED,
    ROUND(SUM(O_TOTALPRICE), 2) AS DAILY_REVENUE,
    ROUND(AVG(O_TOTALPRICE), 2) AS AVG_BASKET_SIZE
FROM OPSLENS.ORDERS
GROUP BY 1
ORDER BY 1 DESC
LIMIT 30""",
    },
    {
        "id": "energy_by_meter",
        "question": "Which meters have the highest cumulative energy consumption?",
        "summary": "Aggregated power consumption per physical smart meter.",
        "sql": """SELECT 
    METER_ID,
    COUNT(*) AS TELEMETRY_SAMPLES,
    ROUND(SUM(KWH), 2) AS TOTAL_CONSUMPTION_KWH,
    ROUND(AVG(KWH), 2) AS AVG_HOURLY_KWH
FROM OPSLENS.ENERGY_READINGS
GROUP BY METER_ID
ORDER BY TOTAL_CONSUMPTION_KWH DESC
LIMIT 15""",
    },
    {
        "id": "latest_readings",
        "question": "Show the latest smart meter telemetry readings",
        "summary": "Most recent time-series telemetry events from ENERGY_READINGS.",
        "sql": """SELECT 
    METER_ID,
    CAST(READING_TS AS VARCHAR(32)) AS READING_TIMESTAMP,
    ROUND(KWH, 3) AS HOURLY_KWH
FROM OPSLENS.ENERGY_READINGS
ORDER BY READING_TS DESC
LIMIT 50""",
    },
    {
        "id": "trust_scores",
        "question": "What are the current data trust scores across assets?",
        "summary": "Multidimensional trust metrics across all production tables and marts.",
        "sql": """SELECT 
    OBJECT_NAME,
    OBJECT_TYPE,
    TRUST_SCORE,
    FRESHNESS_SCORE,
    COMPLETENESS_SCORE,
    UNIQUENESS_SCORE,
    CONSISTENCY_SCORE,
    STATUS
FROM OPSLENS.TRUST_SCORES
WHERE COMPUTED_AT = (SELECT MAX(COMPUTED_AT) FROM OPSLENS.TRUST_SCORES)
ORDER BY TRUST_SCORE ASC
LIMIT 20""",
    },
    {
        "id": "open_alerts",
        "question": "What active alerts require immediate attention?",
        "summary": "Active observability incidents detected by automated Sentinel checks.",
        "sql": """SELECT 
    ALERT_ID,
    INCIDENT_TYPE,
    SEVERITY,
    TARGET_OBJECT,
    SUMMARY,
    STATUS,
    CAST(FIRST_SEEN AS VARCHAR(32)) AS FIRST_SEEN
FROM OPSLENS.ALERTS
WHERE STATUS = 'OPEN'
ORDER BY CASE SEVERITY WHEN 'CRITICAL' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END, LAST_SEEN DESC
LIMIT 25""",
    },
    {
        "id": "slowest_jobs",
        "question": "Which pipeline job stages took the longest to run?",
        "summary": "Execution runtime outliers across pipeline jobs.",
        "sql": """SELECT 
    RUN_ID,
    JOB_ID,
    STAGE,
    DURATION_SEC,
    STATUS,
    ROWS_LOADED,
    CAST(START_TIME AS VARCHAR(32)) AS START_TIME
FROM OPSLENS.PIPELINE_RUN_LOG
ORDER BY DURATION_SEC DESC
LIMIT 20""",
    },
]


def match_template_question(user_question: str) -> Dict[str, Any]:
    """Finds the best matching template question by keyword similarity."""
    q_lower = user_question.lower()
    
    # Priority keyword matching
    if any(k in q_lower for k in ["monthly", "month", "revenue trend"]):
        return TEMPLATE_QUESTIONS[0]
    if any(k in q_lower for k in ["customer", "spend", "top 10"]):
        return TEMPLATE_QUESTIONS[1]
    if any(k in q_lower for k in ["daily", "order volume", "basket"]):
        return TEMPLATE_QUESTIONS[2]
    if any(k in q_lower for k in ["meter", "consumption", "kwh", "highest cumulative"]):
        return TEMPLATE_QUESTIONS[3]
    if any(k in q_lower for k in ["telemetry", "latest reading", "smart meter"]):
        return TEMPLATE_QUESTIONS[4]
    if any(k in q_lower for k in ["trust", "trust score", "health"]):
        return TEMPLATE_QUESTIONS[5]
    if any(k in q_lower for k in ["alert", "incident", "attention"]):
        return TEMPLATE_QUESTIONS[6]
    if any(k in q_lower for k in ["slow", "job", "duration", "longest"]):
        return TEMPLATE_QUESTIONS[7]

    # Default fallback
    return TEMPLATE_QUESTIONS[0]
