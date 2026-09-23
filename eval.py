"""Golden-set evaluation for retrieval + path classification.

Calls retrieve() and run_triage() directly — no UI, no mocking. Runnable
standalone: `python eval.py`. Also imported by app.py to surface the same
results in a collapsed expander (cached at startup, not re-run per query).

The golden set mirrors the "Demo queries" table in README.md — same
queries, same expected paths — plus a hand-labeled expected_units set per
query: the KB unit(s) (doc name, or "doc::section" for a company-profile.md
section) that should be retrieved for that query to be considered grounded
correctly. Most rows have a single expected unit, where precision@2 and
recall@2 collapse to the same value as top-1 accuracy; the "Locked out
twice already today" row has two, since it's the deliberate cross-document
case (account-access playbook + company-profile's SEC-04 policy section).
"""
from agent import run_triage

GOLDEN_SET = [
    {
        "query": "My VPN keeps disconnecting",
        "expected_units": {"vpn"},
        "expected_path": {"AUTO_FIX"},
    },
    {
        "query": "Teams shows me as offline to everyone",
        "expected_units": {"teams"},
        "expected_path": {"AUTO_FIX"},
    },
    {
        "query": "Floor 5 print queue is stuck",
        "expected_units": {"printer"},
        "expected_path": {"AUTO_FIX"},
    },
    {
        "query": "VPN cert error, gateway confirmed correct, offline for a month",
        "expected_units": {"vpn"},
        "expected_path": {"AUTO_FIX"},
    },
    {
        "query": "Need Zoom installed, no admin rights, it's in Company Portal",
        "expected_units": {"software-install"},
        "expected_path": {"AUTO_FIX"},
    },
    {
        "query": "I'm locked out of my account",
        "expected_units": {"account-access"},
        "expected_path": {"ESCALATE"},
    },
    {
        "query": "Locked out twice already today",
        "expected_units": {
            "account-access",
            "company-profile::Governing policies referenced across KB articles",
        },
        "expected_path": {"ESCALATE"},
    },
    {
        "query": "My OneDrive has been stuck syncing for two days",
        "expected_units": {"onedrive"},
        "expected_path": {"ESCALATE"},
    },
    {
        "query": "My external monitor isn't detected when docked",
        "expected_units": {"hardware-peripherals"},
        "expected_path": {"SELF_SERVE", "ESCALATE"},  # doc supports either; see README
    },
    {
        "query": "What's the weather like today?",
        "expected_units": set(),  # nothing in the KB should clear the threshold
        "expected_path": {"OUT_OF_SCOPE"},
    },
]


def _unit_id(u: dict) -> str:
    return u["doc"] if u["section"] is None else f"{u['doc']}::{u['section']}"


def _retrieval_metrics(expected: set, retrieved_ids: list) -> dict:
    top1 = retrieved_ids[0] if retrieved_ids else None
    if not expected:
        # Nothing should have matched — correct iff retrieval also found nothing.
        return {
            "top1_correct": top1 is None,
            "precision": 1.0 if not retrieved_ids else 0.0,
            "recall": 1.0,
        }
    got = set(retrieved_ids)
    tp = len(got & expected)
    return {
        "top1_correct": top1 in expected,
        "precision": (tp / len(got)) if got else 0.0,
        "recall": tp / len(expected),
    }


def run_eval() -> list[dict]:
    """Run every golden-set case through the real pipeline and score it."""
    rows = []
    for case in GOLDEN_SET:
        result = run_triage(case["query"], use_retrieval=True)
        retrieved_ids = [_unit_id(u) for u in result["retrieved"]]
        m = _retrieval_metrics(case["expected_units"], retrieved_ids)
        rows.append({
            "query": case["query"],
            "expected_units": case["expected_units"],
            "retrieved_units": retrieved_ids,
            "top1_correct": m["top1_correct"],
            "precision_at_2": m["precision"],
            "recall_at_2": m["recall"],
            "expected_path": case["expected_path"],
            "actual_path": result["path"],
            "path_correct": result["path"] in case["expected_path"],
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "n": n,
        "retrieval_accuracy": sum(r["top1_correct"] for r in rows) / n,
        "precision_at_2": sum(r["precision_at_2"] for r in rows) / n,
        "recall_at_2": sum(r["recall_at_2"] for r in rows) / n,
        "path_accuracy": sum(r["path_correct"] for r in rows) / n,
    }


def _fmt_units(ids) -> str:
    return ", ".join(sorted(ids)) if ids else "(none)"


def print_report(rows: list[dict], summary: dict) -> None:
    multi = [r for r in rows if len(r["expected_units"]) > 1]
    print(f"Golden-set evaluation — {summary['n']} queries "
          f"({len(multi)} with >1 expected unit, where precision@2/recall@2 "
          f"diverge from top-1 accuracy; all other rows have precision@2 == "
          f"recall@2 == top1_correct by construction)\n")

    for r in rows:
        mark = lambda ok: "✓" if ok else "✗"
        print(f'{mark(r["top1_correct"])} retrieval | {mark(r["path_correct"])} path  '
              f'"{r["query"]}"')
        print(f'    expected units:  {_fmt_units(r["expected_units"])}')
        print(f'    retrieved units: {_fmt_units(r["retrieved_units"])}  '
              f'(precision@2={r["precision_at_2"]:.2f}, recall@2={r["recall_at_2"]:.2f})')
        print(f'    expected path:   {"/".join(sorted(r["expected_path"]))}   '
              f'actual: {r["actual_path"]}')
        print()

    print(
        f"SUMMARY  retrieval_accuracy={summary['retrieval_accuracy']:.0%}  "
        f"precision@2={summary['precision_at_2']:.0%}  "
        f"recall@2={summary['recall_at_2']:.0%}  "
        f"path_accuracy={summary['path_accuracy']:.0%}"
    )


if __name__ == "__main__":
    _rows = run_eval()
    print_report(_rows, summarize(_rows))
