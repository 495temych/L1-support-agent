"""Summary statistics over logs.csv — real usage from actual runs through the app,
not synthetic data and not the eval.py golden set. Standalone: `python analyze_logs.py`.
Also imported by app.py to show live-session stats in the UI, next to (but clearly
distinct from) eval.py's fixed golden-set numbers.
"""
import csv
from pathlib import Path

LOG_FILE = Path(__file__).parent / "logs.csv"
PATHS = ["SELF_SERVE", "AUTO_FIX", "ESCALATE", "OUT_OF_SCOPE"]
MIN_ROWS_FOR_STABLE_RATE = 5


def _read_rows() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, newline="") as f:
        return list(csv.DictReader(f))


def summary_stats() -> dict:
    """Reads logs.csv fresh (no caching — must reflect the latest logged run) and
    computes: total, count/% by decision_path, automation rate, avg response time
    by decision_path. n is 0 and rates are None if the log is empty.
    """
    rows = _read_rows()
    n = len(rows)

    by_path = {p: [r for r in rows if r.get("decision_path") == p] for p in PATHS}
    counts = {p: len(by_path[p]) for p in PATHS}
    pct = {p: (counts[p] / n * 100) if n else 0.0 for p in PATHS}

    denom = n - counts["OUT_OF_SCOPE"]
    automation_rate = (
        (counts["SELF_SERVE"] + counts["AUTO_FIX"]) / denom * 100 if denom > 0 else None
    )

    avg_response_time_sec = {}
    for p in PATHS:
        times = [float(r["response_time_sec"]) for r in by_path[p] if r.get("response_time_sec")]
        avg_response_time_sec[p] = (sum(times) / len(times)) if times else None

    return {
        "n": n,
        "counts": counts,
        "pct": pct,
        "automation_rate": automation_rate,
        "avg_response_time_sec": avg_response_time_sec,
        "low_sample": n < MIN_ROWS_FOR_STABLE_RATE,
    }


def print_summary(stats: dict | None = None) -> None:
    stats = stats if stats is not None else summary_stats()
    print(f"Live session stats — {stats['n']} logged queries from actual app runs "
          f"(logs.csv). This is NOT the eval.py golden set.\n")

    if stats["n"] == 0:
        print("No queries logged yet. Run some queries through the app first.")
        return

    if stats["low_sample"]:
        print(f"Sample size too small for a stable rate (< {MIN_ROWS_FOR_STABLE_RATE} rows) "
              f"— numbers below are illustrative only, not a reliable rate.\n")

    print("Count and % by decision path:")
    for p in PATHS:
        print(f"  {p:12s} {stats['counts'][p]:3d}  ({stats['pct'][p]:.0f}%)")

    if stats["automation_rate"] is not None:
        print(f"\nAutomation rate (SELF_SERVE + AUTO_FIX, over total minus OUT_OF_SCOPE): "
              f"{stats['automation_rate']:.0f}%")
    else:
        print("\nAutomation rate: n/a (no non-OUT_OF_SCOPE queries logged yet)")

    print("\nAgent response time (proxy for MTTR — measures decision latency, not full "
          "ticket resolution), avg by path:")
    for p in PATHS:
        t = stats["avg_response_time_sec"][p]
        print(f"  {p:12s} {f'{t:.2f}s' if t is not None else 'n/a'}")


if __name__ == "__main__":
    print_summary()
