"""
OpsLens Exasol Connectivity Verification Script
Tests basic connectivity, retrieves Exasol database version, and executes 'SELECT 1'.
"""

import sys
from backend.db import get_connection, get_db_config


def test_connectivity():
    config = get_db_config()
    print("=" * 60)
    print(" OpsLens — Exasol Connectivity Test")
    print("=" * 60)
    print(f"Target DSN       : {config['dsn']}")
    print(f"User             : {config['user']}")
    print(f"Verify Cert      : {config['verify_cert']}")
    print(f"Encryption       : {config['encryption']}")
    print("-" * 60)

    try:
        # Connect without enforcing OPSLENS schema yet (in case schema does not exist initially)
        print("Connecting to Exasol...")
        conn = get_connection(schema="")
        print(">> Connection established successfully!")

        # 1. Retrieve Exasol Version
        version = None
        version_queries = [
            "SELECT PARAM_VALUE FROM SYS.EXA_METADATA WHERE PARAM_NAME = 'databaseProductVersion'",
            "SELECT PARAM_VALUE FROM SYS.EXA_PARAMETERS WHERE PARAM_NAME = 'databaseProductVersion'",
        ]

        for q in version_queries:
            try:
                res = conn.execute(q).fetchall()
                if res and res[0]:
                    version = res[0][0]
                    break
            except Exception:
                continue

        if not version:
            try:
                # Fallback to session details
                res = conn.execute("SELECT CURRENT_VERSION()").fetchall()
                version = res[0][0] if res else "Unknown"
            except Exception:
                version = "Exasol (Version string query unavailable)"

        print(f"Exasol Version   : {version}")

        # 2. Execute SELECT 1
        print("Executing 'SELECT 1'...")
        stmt = conn.execute("SELECT 1 AS TEST_VAL")
        result = stmt.fetchall()
        print(f"Query Result     : {result}")
        print(">> 'SELECT 1' check passed!")

        # 3. Print Session Details
        try:
            session_info = conn.execute(
                "SELECT CURRENT_USER, CURRENT_SCHEMA, CURRENT_SESSION"
            ).fetchall()
            print(f"Session Info     : User={session_info[0][0]}, Schema={session_info[0][1]}, SessionId={session_info[0][2]}")
        except Exception as e:
            print(f"Session Info query skipped: {e}")

        conn.close()
        print("=" * 60)
        print(" STATUS: SUCCESS - Exasol is fully responsive.")
        print("=" * 60)
        return True

    except Exception as exc:
        print("\n" + "!" * 60)
        print(" STATUS: FAILED - Could not connect to Exasol.")
        print("!" * 60)
        print(f"Exact Error: {exc}\n")
        return False


if __name__ == "__main__":
    success = test_connectivity()
    if not success:
        sys.exit(1)
