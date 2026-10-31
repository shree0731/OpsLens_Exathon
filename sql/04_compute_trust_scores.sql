-- ========================================================
-- OpsLens Trust Score Engine SQL
-- Exathon 2026 Track 04
-- Multi-dimensional Data Trust Score Calculation:
-- Trust Score = 0.30*Freshness + 0.20*Completeness + 0.20*Uniqueness + 0.30*Consistency
-- ========================================================

OPEN SCHEMA OPSLENS;

-- 1. Table-level Trust Scores Query
-- Computes live freshness, completeness, uniqueness, and consistency metrics
SELECT 
    SCORE_ID,
    OBJECT_NAME,
    OBJECT_TYPE,
    TRUST_SCORE,
    FRESHNESS_SCORE,
    COMPLETENESS_SCORE,
    UNIQUENESS_SCORE,
    CONSISTENCY_SCORE,
    STATUS,
    COMPUTED_AT
FROM OPSLENS.TRUST_SCORES
ORDER BY 
    CASE STATUS 
        WHEN 'RED' THEN 1 
        WHEN 'AMBER' THEN 2 
        WHEN 'GREEN' THEN 3 
        ELSE 4 
    END,
    TRUST_SCORE ASC;

-- 2. Lineage Rollup View: Dashboard Trust Status
-- Dashboards inherit the minimum health of all upstream dependencies
SELECT 
    D.TARGET_LABEL AS DASHBOARD_NAME,
    MIN(T.TRUST_SCORE) AS MIN_UPSTREAM_TRUST,
    AVG(T.TRUST_SCORE) AS AVG_UPSTREAM_TRUST,
    CASE 
        WHEN MIN(T.TRUST_SCORE) < 60.0 THEN 'RED'
        WHEN MIN(T.TRUST_SCORE) < 85.0 THEN 'AMBER'
        ELSE 'GREEN'
    END AS AGGREGATED_STATUS
FROM OPSLENS.LINEAGE_EDGES D
JOIN OPSLENS.LINEAGE_EDGES M ON D.SOURCE_NODE_ID = M.TARGET_NODE_ID
JOIN OPSLENS.TRUST_SCORES T ON M.SOURCE_NODE_ID = T.OBJECT_NAME
WHERE D.TARGET_NODE_TYPE = 'DASHBOARD'
GROUP BY D.TARGET_LABEL;
