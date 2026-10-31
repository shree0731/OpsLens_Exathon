"""
OpsLens Lineage Snapshot Generator
Injects row_drop and stale_feed separately, and outputs the final JSON of GET /api/lineage.
"""

import json
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def get_snapshot(fault_name: str) -> dict:
    # 1. Reset
    client.post("/api/faults/reset")
    # 2. Inject fault
    client.post(f"/api/faults/{fault_name}")
    # 3. Fetch lineage
    res = client.get("/api/lineage")
    return res.json()


def main():
    # Snapshot 1: row_drop
    lineage_row_drop = get_snapshot("row_drop")
    print("=" * 80)
    print(" >>> GET /api/lineage JSON after injecting row_drop")
    print("=" * 80)
    print(json.dumps(lineage_row_drop, indent=2))

    # Snapshot 2: stale_feed
    lineage_stale_feed = get_snapshot("stale_feed")
    print("\n" + "=" * 80)
    print(" >>> GET /api/lineage JSON after injecting stale_feed")
    print("=" * 80)
    print(json.dumps(lineage_stale_feed, indent=2))

    # Final reset
    client.post("/api/faults/reset")


if __name__ == "__main__":
    main()
