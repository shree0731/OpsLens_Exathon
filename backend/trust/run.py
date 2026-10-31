"""
OpsLens Trust Score Runner CLI
Computes and prints current trust scores.

Usage:
  python -m backend.trust.run
"""

from backend.trust.engine import calculate_all_trust_scores


def main():
    print("=" * 65)
    print(" OpsLens Trust Score Engine — Running Calculation")
    print("=" * 65)
    
    scores = calculate_all_trust_scores()
    
    print(f"\n{'OBJECT NAME':<26} | {'TYPE':<10} | {'SCORE':>6} | {'STATUS':<6} | {'F':>5} {'C':>5} {'U':>5} {'S':>5}")
    print("-" * 72)
    for s in scores:
        print(f"{s['OBJECT_NAME']:<26} | {s['OBJECT_TYPE']:<10} | {s['TRUST_SCORE']:>6.1f} | {s['STATUS']:<6} | {s['FRESHNESS_SCORE']:>5.0f} {s['COMPLETENESS_SCORE']:>5.0f} {s['UNIQUENESS_SCORE']:>5.0f} {s['CONSISTENCY_SCORE']:>5.0f}")


if __name__ == "__main__":
    main()
