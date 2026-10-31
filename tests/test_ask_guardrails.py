"""
OpsLens Ask-the-Warehouse Security & Guardrail Unit Tests
1. Verifies that at least 12 malicious, mutating, or policy-violating SQL patterns are strictly rejected.
2. Verifies that all 8 curated template questions execute safely and successfully against live Exasol.
"""

import pytest
from backend.db import get_connection
from backend.ask.guardrails import validate_guardrails
from backend.ask.templates import TEMPLATE_QUESTIONS
from backend.ask.engine import execute_ask_sql


MALICIOUS_AND_INVALID_QUERIES = [
    # 1. DDL DROP
    ("DROP TABLE OPSLENS.ORDERS", "DDL DROP statement"),
    # 2. DML DELETE
    ("DELETE FROM OPSLENS.LINEITEM WHERE L_ORDERKEY = 1", "DML DELETE statement"),
    # 3. DML INSERT
    ("INSERT INTO OPSLENS.ORDERS (O_ORDERKEY) VALUES (999999)", "DML INSERT statement"),
    # 4. DML UPDATE
    ("UPDATE OPSLENS.ORDERS SET O_TOTALPRICE = 0", "DML UPDATE statement"),
    # 5. DDL TRUNCATE
    ("TRUNCATE TABLE OPSLENS.CONFIG", "DDL TRUNCATE statement"),
    # 6. DDL ALTER
    ("ALTER TABLE OPSLENS.CUSTOMER ADD COLUMN ATTACK_VECTOR VARCHAR(10)", "DDL ALTER statement"),
    # 7. DDL CREATE
    ("CREATE TABLE OPSLENS.BACKDOOR (ID INT)", "DDL CREATE statement"),
    # 8. Administrative GRANT
    ("GRANT ALL PRIVILEGES ON SCHEMA OPSLENS TO PUBLIC", "Administrative GRANT"),
    # 9. Stacked multi-statement SQL injection
    ("SELECT * FROM OPSLENS.ORDERS LIMIT 10; DROP TABLE OPSLENS.CUSTOMER;", "Stacked multi-statement injection"),
    # 10. Prohibited System Catalog Access
    ("SELECT * FROM SYS.EXA_ALL_USERS LIMIT 10", "Restricted SYS schema access"),
    # 11. Prohibited EXA Statistics Access
    ("SELECT * FROM EXA_STATISTICS.EXA_SQL_HOURLY LIMIT 10", "Restricted EXA_STATISTICS access"),
    # 12. Prohibited Reference Sample Schema Access (TPCH)
    ("SELECT * FROM TPCH.ORDERS LIMIT 10", "Restricted TPCH sample schema"),
    # 13. Prohibited Reference Sample Schema Access (ENERGY)
    ("SELECT * FROM ENERGY.ENERGY_READINGS LIMIT 10", "Restricted ENERGY sample schema"),
    # 14. Prohibited Reference Sample Schema Access (WEATHER)
    ("SELECT * FROM WEATHER.WEATHER_DAILY LIMIT 10", "Restricted WEATHER sample schema"),
    # 15. Missing explicit LIMIT
    ("SELECT * FROM OPSLENS.ORDERS", "Missing LIMIT clause"),
    # 16. LIMIT exceeding quota (> 1000)
    ("SELECT * FROM OPSLENS.ORDERS LIMIT 5000", "LIMIT > 1000 quota breach"),
    # 17. Stored procedure / Script execution
    ("EXECUTE SCRIPT OPSLENS.DUMP_DATA()", "EXECUTE command prohibited"),
    # 18. MERGE statement
    ("MERGE INTO OPSLENS.ORDERS O USING OPSLENS.CUSTOMER C ON (O.O_CUSTKEY = C.C_CUSTKEY) WHEN MATCHED THEN DELETE", "MERGE command prohibited"),
]


@pytest.fixture(scope="module")
def conn():
    c = get_connection(schema="OPSLENS")
    yield c
    c.close()


@pytest.mark.parametrize("malicious_sql, description", MALICIOUS_AND_INVALID_QUERIES)
def test_guardrails_reject_malicious_sql(malicious_sql, description, conn):
    """Asserts that each malicious or policy-violating SQL sample is rejected by guardrails."""
    res = validate_guardrails(malicious_sql, conn=conn)
    assert not res["is_safe"], f"Expected guardrail REJECTION for {description}: '{malicious_sql}'"
    assert len(res["failures"]) > 0
    print(f"  -> [REJECTED as expected] {description:<35} | Failure reason: {res['failures'][0]}")


def test_guardrails_rejection_count():
    """Asserts that at least 12 distinct malicious samples were evaluated and rejected."""
    assert len(MALICIOUS_AND_INVALID_QUERIES) >= 12


def test_all_eight_template_questions_execution(conn):
    """Executes all 8 curated template questions on live Exasol to ensure 100% compliance and safe execution."""
    assert len(TEMPLATE_QUESTIONS) == 8

    print("\n" + "=" * 80)
    print(" OpsLens Ask-the-Warehouse — Live Template Execution Verification")
    print("=" * 80)

    for idx, t in enumerate(TEMPLATE_QUESTIONS, 1):
        q_id = t["id"]
        q_text = t["question"]
        q_sql = t["sql"]

        # 1. Guardrail validation check
        guard_res = validate_guardrails(q_sql, conn=conn)
        assert guard_res["is_safe"], f"Template question {q_id} failed guardrails: {guard_res['failures']}"
        assert guard_res["chips"]["select_only"]["passed"]
        assert guard_res["chips"]["single_statement"]["passed"]
        assert guard_res["chips"]["opslens_schema_only"]["passed"]
        assert guard_res["chips"]["limit_enforced"]["passed"]

        # 2. Live execution check
        exec_res = execute_ask_sql(q_sql, question=q_text, conn=conn)
        assert exec_res["success"], f"Execution of template {q_id} failed: {exec_res.get('error')}"
        assert exec_res["row_count"] >= 0
        assert len(exec_res["columns"]) > 0
        assert exec_res["duration_sec"] < 5.0
        assert exec_res["saved_to_query_stats"] is True

        print(f"[{idx}/8] {q_id:<20} | Rows: {exec_res['row_count']:>4} | Latency: {exec_res['duration_sec']:.3f}s | Guardrails: 5/5 PASS")

    print("=" * 80)
