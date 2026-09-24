import csv
import os
import sys
import time
import importlib
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import streamlit as st

# One-time module reloads per Streamlit session so code changes in retrieval.py
# and agent.py are picked up without a full server restart.
# retrieval is reloaded only once (resetting its model cache is expensive);
# agent is cheap to reload so we do it on every script run.
import tools as _tools_mod
import agent as _agent_mod

if "modules_reloaded" not in st.session_state:
    # One-time reloads so code changes are picked up without a full server restart.
    # retrieval + tools: reloaded once (retrieval has heavy model globals; tools has REGISTRY).
    import retrieval as _retrieval_mod
    importlib.reload(_retrieval_mod)
    importlib.reload(_tools_mod)
    st.session_state.modules_reloaded = True

# agent: cheap to reload on every run (picks up prompt/tool schema changes instantly).
importlib.reload(_agent_mod)
from agent import run_triage
import eval as _eval_mod
import analyze_logs as _analyze_mod

st.set_page_config(
    page_title="L1 Support Agent — Limmatica AG",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Guard: API key ──────────────────────────────────────────────────────────────
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("**ANTHROPIC_API_KEY not set.** Add it to `.env` or your shell environment.")
    st.stop()

# ── Session state ───────────────────────────────────────────────────────────────
for key, default in [
    ("result", None),
    ("tool_state", None),   # "pending" | "confirmed" | "cancelled"
    ("tool_result", None),
    ("query_text", ""),
    ("use_retrieval", True),
    ("pending_log_row", None),
    ("decline_ticket", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Usage logging (real runs only — logs.csv starts empty, populated only here) ──
LOG_FILE = Path(__file__).parent / "logs.csv"
LOG_FIELDS = [
    "timestamp", "query", "retrieved_units", "decision_path", "diagnostic_summary",
    "tool_called", "confirmed", "escalation_queue", "priority", "response_time_sec",
]


def _is_header_line(line: str) -> bool:
    # Skip bare markdown headers like "**Step 1 — Diagnose**" or "**Diagnosis**" — we
    # want the actual sentence that follows, not the section label, as the log summary.
    return line.startswith("**") and line.endswith("**") and line.count("**") == 2


def _log_run(result: dict, response_time_sec: float) -> int | None:
    """Append one row to logs.csv for a completed triage run and return its 0-indexed
    position among data rows, so a later Confirm/Cancel can patch `confirmed` in place.
    Skips NO_TOOLS runs — RAG-off never reaches Step 2, so there's no decision_path
    value for it in the documented schema.
    """
    if result["path"] == "NO_TOOLS":
        return None

    units = result["retrieved"] or []
    retrieved_units = ";".join(
        u["doc"] + (f"::{u['section']}" if u["section"] else "") for u in units
    ) or "none"
    diagnostic_summary = next(
        (l.strip() for l in (result["reasoning"] or "").split("\n")
         if len(l.strip()) > 15 and not _is_header_line(l.strip())),
        "",
    )[:150]
    tool_input = result["tool_input"] or {}
    is_escalate = result["path"] == "ESCALATE"

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": result.get("query", ""),
        "retrieved_units": retrieved_units,
        "decision_path": result["path"],
        "diagnostic_summary": diagnostic_summary,
        "tool_called": result["tool_name"] or "",
        "confirmed": "",  # patched later for AUTO_FIX rows by _patch_confirmed
        "escalation_queue": tool_input.get("queue", "") if is_escalate else "",
        "priority": tool_input.get("priority", "") if is_escalate else "",
        "response_time_sec": f"{response_time_sec:.2f}",
    }

    # Header goes out once — when the file doesn't exist yet, or exists but is empty
    # (e.g. a fresh `touch` or a truncated file). Checking .exists() alone would skip
    # the header forever on an empty-but-present file, corrupting the CSV on next read.
    needs_header = not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)

    with open(LOG_FILE, newline="") as f:
        n_data_rows = sum(1 for _ in csv.reader(f)) - 1  # minus header
    return n_data_rows - 1


def _patch_confirmed(row_index: int | None, confirmed: bool) -> None:
    """Rewrite logs.csv with `confirmed` set on one row — only meaningful for AUTO_FIX
    rows, since that's the only path where declining actually prevents an action."""
    if row_index is None or not LOG_FILE.exists():
        return
    with open(LOG_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    if 0 <= row_index < len(rows) and rows[row_index]["decision_path"] == "AUTO_FIX":
        rows[row_index]["confirmed"] = "true" if confirmed else "false"
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
            writer.writeheader()
            writer.writerows(rows)


def _build_decline_ticket(result: dict) -> dict:
    """Pre-fill an escalation ticket client-side after an AUTO_FIX decline — reuses the
    diagnosis already produced in this response (result['reasoning']), no new model call.
    """
    declined_tool = result["tool_name"] or "unknown"
    reason = "User declined proposed automated fix; issue persists"
    diagnostic_summary = next(
        (l.strip() for l in (result["reasoning"] or "").split("\n")
         if len(l.strip()) > 15 and not _is_header_line(l.strip())),
        "Automated fix did not run; issue not yet resolved.",
    )
    # Same default priority the app's other client-side ticket synthesis paths use
    # (the safety-net ticket below and the SELF_SERVE-fallback ticket) — there's no
    # model-assigned priority to reuse here since AUTO_FIX responses never carry one.
    priority = "P3-Normal"
    summary_for_ticket = f"{diagnostic_summary} {reason} (declined: {declined_tool})."[:150]
    return {
        "diagnostic_summary": diagnostic_summary,
        "declined_tool": declined_tool,
        "reason": reason,
        "queue": "DESKTOP-SUPPORT",
        "priority": priority,
        "summary_for_ticket": summary_for_ticket,
    }


# ── Callbacks ───────────────────────────────────────────────────────────────────
def _confirm():
    r = st.session_state.result
    st.session_state.tool_result = _tools_mod.dispatch(r["tool_name"], r["tool_input"] or {})
    st.session_state.tool_state = "confirmed"
    _patch_confirmed(st.session_state.get("pending_log_row"), confirmed=True)


def _cancel():
    _patch_confirmed(st.session_state.get("pending_log_row"), confirmed=False)
    r = st.session_state.result
    if r["path"] == "AUTO_FIX":
        # Decline fallback: no tool call, no new model query — pre-fill an escalation
        # ticket from the diagnosis already in this response and ask for a separate,
        # explicit confirmation before it's actually sent.
        import random
        st.session_state.decline_ticket = _build_decline_ticket(r)
        st.session_state.preview_ticket_id = f"INC{random.randint(1000000, 9999999)}"
        st.session_state.tool_state = "declined"
    else:
        st.session_state.tool_state = "cancelled"


def _send_decline_ticket():
    ticket = st.session_state.decline_ticket
    st.session_state.tool_result = _tools_mod.dispatch(
        "create_escalation_ticket",
        {"queue": ticket["queue"], "summary": ticket["summary_for_ticket"], "priority": ticket["priority"]},
    )
    st.session_state.tool_state = "declined_sent"


def _cancel_decline_ticket():
    st.session_state.tool_state = "declined_cancelled"


def _escalate_self_serve():
    """Convert a displayed SELF_SERVE result into an ESCALATE ticket-preview flow,
    reusing create_escalation_ticket — no new tool or UI path."""
    r = st.session_state.result
    summary = f"Self-serve steps did not resolve the issue. Original query: {r.get('query', '')}"
    r["path"] = "ESCALATE"
    r["tool_name"] = "create_escalation_ticket"
    r["tool_input"] = {
        "queue": "DESKTOP-SUPPORT",
        "summary": summary[:150],
        "priority": "P3-Normal",
    }
    _init_tool_state(r)


def _set_preset(q: str):
    """Populate the text field with the preset query; user still clicks Analyze."""
    st.session_state.query_text = q


@st.cache_data(show_spinner="Running golden-set evaluation…")
def _run_eval_cached():
    """Runs eval.py's golden set once (cached across reruns) — not per query."""
    rows = _eval_mod.run_eval()
    return rows, _eval_mod.summarize(rows)


def _init_tool_state(result: dict):
    import random
    needs = result["tool_name"] is not None and result["path"] in ("AUTO_FIX", "ESCALATE")
    st.session_state.tool_state = "pending" if needs else None
    st.session_state.tool_result = None
    st.session_state.decline_ticket = None
    # Generate a stable preview ticket ID shown before and after confirmation
    if result["path"] == "ESCALATE":
        st.session_state.preview_ticket_id = f"INC{random.randint(1000000, 9999999)}"


# ── Helpers ─────────────────────────────────────────────────────────────────────
_PATH_COLORS = {
    "SELF_SERVE":   ("#1a7f37", "#dafbe1"),
    "AUTO_FIX":     ("#0550ae", "#dbeafe"),
    "ESCALATE":     ("#9a3412", "#fef3c7"),
    "OUT_OF_SCOPE": ("#555555", "#f0f0f0"),
    "NO_TOOLS":     ("#6d28d9", "#ede9fe"),
}

_PATH_LABELS = {
    "NO_TOOLS": "NO TOOLS (RAG OFF)",
}

def _badge(path: str) -> str:
    fg, bg = _PATH_COLORS.get(path, ("#555", "#eee"))
    label = _PATH_LABELS.get(path, path)
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {fg}33;'
        f'padding:4px 12px;border-radius:5px;font-weight:700;'
        f'font-size:0.95em;letter-spacing:0.03em">{label}</span>'
    )


def _pending_callout(label: str) -> None:
    """Renders the 'awaiting confirmation' banner above Confirm/Cancel buttons."""
    st.markdown(
        f'<div style="background:#fffbeb;border:1px solid #f59e0b;border-radius:6px;'
        f'padding:10px 14px;margin:10px 0 8px 0;color:#78350f;">'
        f'<strong style="color:#78350f">&#9888;&#65039; Human-in-the-loop — awaiting your decision</strong><br/>'
        f'<span style="font-size:0.9em;color:#78350f">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Presets ─────────────────────────────────────────────────────────────────────
PRESETS = [
    # AUTO_FIX demos — single source
    "My VPN cert error persists, I've confirmed the gateway is correct and I was offline for a month",
    "Teams shows me as offline to everyone",
    "Floor 5 print queue is stuck, several people can't print",
    "I need Zoom installed but I don't have admin rights — it's listed in Company Portal",
    # ESCALATE demos — single source
    "I'm locked out of my account",
    "My external monitor isn't detected when docked",
    # Cross-document retrieval demos — one query pulls units from two different KB
    # documents in the same call (an issue playbook + a company-profile.md section,
    # or two issue playbooks together)
    "I've been locked out of my account twice already today",
    "My OneDrive won't sync one of my report files, I'm in Finance and we use # in filenames for versions",
    "My mapped network drive for Finance is gone since this morning, VPN is connected fine",
    "Outlook keeps asking me to sign in again and again today",
    # More single-document coverage
    "Wi-Fi keeps dropping for everyone near the open-plan area on floor 5, seems like too many devices on one access point",
    "My laptop has been unbearably slow since this weekend, fans running constantly",
    # OUT_OF_SCOPE demo
    "What's the weather like today?",
]


# ── Header ──────────────────────────────────────────────────────────────────────
st.title("L1 Support Agent")
st.caption("Limmatica AG · internal IT triage demo · powered by Claude")
st.divider()

# ── Global RAG toggle ───────────────────────────────────────────────────────────
st.toggle("Use retrieval (RAG)", key="use_retrieval")
st.markdown("")

# ── Preset buttons ──────────────────────────────────────────────────────────────
st.markdown("**Quick examples**")
cols = st.columns(3)
for i, preset in enumerate(PRESETS):
    cols[i % 3].button(
        preset,
        key=f"preset_{i}",
        on_click=_set_preset,
        args=(preset,),
        use_container_width=True,
    )

st.markdown("---")

# ── Free-text form ──────────────────────────────────────────────────────────────
with st.form("query_form", clear_on_submit=False):
    query = st.text_area(
        "Or describe a custom issue:",
        value=st.session_state.query_text,
        placeholder="e.g.  My VPN keeps disconnecting since the migration last month",
        height=90,
    )
    submitted = st.form_submit_button("Analyze →", type="primary")

# ── Execute triage ──────────────────────────────────────────────────────────────
if submitted and query.strip():
    t0 = time.time()
    with st.spinner("Running triage…"):
        result = run_triage(query.strip(), st.session_state.use_retrieval)
    response_time_sec = time.time() - t0
    # Safety net: if model chose ESCALATE in text but skipped the tool call,
    # synthesize a minimal ticket so the confirmation card always renders.
    if result["path"] == "ESCALATE" and result["tool_name"] is None:
        first_line = next(
            (l.strip() for l in (result["reasoning"] or "").split("\n") if len(l.strip()) > 15),
            "Issue escalated — technician review required.",
        )
        result["tool_name"] = "create_escalation_ticket"
        result["tool_input"] = {
            "queue": "DESKTOP-SUPPORT",
            "summary": first_line[:150],
            "priority": "P3-Normal",
        }
    st.session_state.result = result
    st.session_state.pending_log_row = _log_run(result, response_time_sec)
    _init_tool_state(result)

# ── Results ─────────────────────────────────────────────────────────────────────
if st.session_state.result:
    result = st.session_state.result
    st.divider()

    # 1 · Retrieval
    st.subheader("1 · Retrieval")
    units = result["retrieved"]
    if units:
        doc_names = {u["doc"] for u in units}
        if len(doc_names) > 1:
            st.caption("🔗 Matched units from **different KB documents** — cross-document grounding.")

        for u in units:
            label = u["doc"] + (f" § {u['section']}" if u["section"] else "")
            badge = " · *reference section*" if u["section"] else ""
            with st.expander(f"**{label}** — similarity {u['score']:.2f}{badge}", expanded=False):
                st.markdown(u["text"])

            highlights = u.get("highlights", [])
            if highlights:
                st.markdown(f"**Why {label} matched — top passages:**")
            for h in highlights:
                # Strip markdown characters for clean plain-text display in the highlight strip
                clean = h["text"].replace("**", "").replace("`", "").replace("*", "")
                st.markdown(
                    f'<div style="background:#fffbeb;border-left:3px solid #f59e0b;'
                    f'padding:5px 10px;margin:3px 0;font-size:0.88em;line-height:1.4;color:#78350f;">'
                    f'<code style="color:#92400e;font-size:0.82em;background:none">'
                    f'{h["score"]:.2f}</code>'
                    f'&ensp;{clean}</div>',
                    unsafe_allow_html=True,
                )
    else:
        if result["use_retrieval"]:
            st.info("No KB article matched above the confidence threshold.")
        else:
            st.info("RAG is off — no retrieval performed.")

    # 2 · Decision
    st.subheader("2 · Decision")
    st.markdown(_badge(result["path"]), unsafe_allow_html=True)
    st.markdown("")

    # 3 · Agent reasoning
    st.subheader("3 · Agent reasoning")
    st.markdown(result["reasoning"] or "_No reasoning returned._")

    # 4 · Action
    st.subheader("4 · Action")
    path = result["path"]

    # ── Non-interactive paths ────────────────────────────────────────────────
    if path == "SELF_SERVE":
        st.success("Steps are in the reasoning above — no operator action required.")
        st.button(
            "This didn't resolve it — escalate to a technician.",
            on_click=_escalate_self_serve,
        )

    elif path == "OUT_OF_SCOPE":
        st.info("Outside IT support scope — no action taken.")

    elif path == "NO_TOOLS":
        st.info(
            "RAG is off, so the agent had no tools and no company-specific grounding "
            "for this call — it could only respond with generic, ungrounded advice. "
            "No structured decision or action is available. Turn retrieval back on "
            "to see the grounded, tool-capable agent."
        )

    # ── Interactive paths (both require operator confirmation) ───────────────
    elif path == "AUTO_FIX":
        tool_name  = result["tool_name"] or "unknown"
        tool_input = result["tool_input"] or {}

        # Action card
        with st.container(border=True):
            st.markdown("**Proposed automated fix**")
            st.markdown(f"Tool: `{tool_name}`")
            if tool_input:
                for k, v in tool_input.items():
                    st.markdown(f"- `{k}`: `{v}`")

        state = st.session_state.tool_state

        if state == "pending":
            _pending_callout("This fix will not run until you confirm below.")
            c1, c2, _ = st.columns([2, 2, 3])
            with c1:
                st.button("✓ Confirm — run action", on_click=_confirm,
                          type="primary", use_container_width=True)
            with c2:
                st.button("✗ Cancel", on_click=_cancel, use_container_width=True)

        elif state == "confirmed" and st.session_state.tool_result:
            tr = st.session_state.tool_result
            st.success(f"**Action taken (simulated)**\n\n{tr['detail']}")
            st.caption(f"Timestamp: {tr['timestamp']}")

        elif state == "declined":
            st.warning(
                "**Automated fix declined — here's a pre-filled ticket.** Built entirely "
                "from the diagnosis above — no new model call."
            )
            ticket = st.session_state.decline_ticket
            ticket_id = st.session_state.get("preview_ticket_id", "INC0000000")

            with st.container(border=True):
                st.markdown("**Draft ServiceNow incident — pending confirmation**")
                st.markdown("")
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown(f"**Ticket ID**\n\n`{ticket_id}`")
                    st.markdown(f"**Assignment group**\n\n`{ticket['queue']}`")
                    st.markdown(f"**Priority**\n\n`{ticket['priority']}`")
                with col_r:
                    st.markdown(f"**Declined fix**\n\n`{ticket['declined_tool']}`")
                    st.markdown(f"**Reason**\n\n{ticket['reason']}")
                    st.markdown(f"**Diagnostic summary**\n\n{ticket['diagnostic_summary']}")

            _pending_callout(
                f"Confirm to submit this ticket to <strong>{ticket['queue']}</strong> "
                f"and notify the on-call technician."
            )
            c1, c2, _ = st.columns([2, 2, 3])
            with c1:
                st.button("✓ Send to ServiceNow", on_click=_send_decline_ticket,
                          type="primary", use_container_width=True)
            with c2:
                st.button("✗ Cancel", on_click=_cancel_decline_ticket, use_container_width=True)

        elif state == "declined_sent" and st.session_state.tool_result:
            tr = st.session_state.tool_result
            ticket_id = st.session_state.get("preview_ticket_id", "INC0000000")
            queue = st.session_state.decline_ticket["queue"]
            st.success(
                f"**Ticket {ticket_id} submitted (simulated)**\n\n"
                f"Redirecting to ServiceNow... *(simulated)*\n\n"
                f"On-call technician for `{queue}` notified. SLA clock started."
            )
            st.caption(f"Timestamp: {tr['timestamp']}")

        elif state == "declined_cancelled":
            st.warning("Escalation skipped by operator. No fix applied, no ticket created.")

    elif path == "ESCALATE":
        if result["tool_name"] == "create_escalation_ticket":
            ti        = result["tool_input"] or {}
            queue     = ti.get("queue", "DESKTOP-SUPPORT")
            summary   = ti.get("summary", "—")
            priority  = ti.get("priority", "P3-Normal")
            ticket_id = st.session_state.get("preview_ticket_id", "INC0000000")

            state = st.session_state.tool_state

            if state in ("pending", None):
                # ── Draft ticket preview (ITSM-style) ────────────────────────
                with st.container(border=True):
                    st.markdown("**Draft ServiceNow incident — pending confirmation**")
                    st.markdown("")
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.markdown(f"**Ticket ID**\n\n`{ticket_id}`")
                        st.markdown(f"**Assignment group**\n\n`{queue}`")
                        st.markdown(f"**Priority**\n\n`{priority}`")
                    with col_r:
                        st.markdown("**Requested by**\n\n`current.user`")
                        st.markdown("**Category**\n\nIT Support / Endpoint")
                        st.markdown(f"**Short description**\n\n{summary}")

                _pending_callout(
                    f"Confirm to submit this ticket to <strong>{queue}</strong> "
                    f"and notify the on-call technician."
                )
                c1, c2, _ = st.columns([2, 2, 3])
                with c1:
                    st.button("✓ Confirm — submit ticket", on_click=_confirm,
                              type="primary", use_container_width=True)
                with c2:
                    st.button("✗ Cancel", on_click=_cancel, use_container_width=True)

            elif state == "confirmed" and st.session_state.tool_result:
                tr = st.session_state.tool_result
                st.success(
                    f"**Ticket {ticket_id} submitted (simulated)**\n\n"
                    f"Redirecting to ServiceNow... *(simulated)*\n\n"
                    f"On-call technician for `{queue}` notified. SLA clock started."
                )
                st.caption(f"Timestamp: {tr['timestamp']}")

            elif state == "cancelled":
                st.warning("Escalation skipped by user. No ticket created.")

        else:
            # Fallback: agent chose ESCALATE but didn't call the ticket tool.
            st.warning(
                "The agent recommends escalation but did not propose a specific ticket. "
                "Review the reasoning above and raise a ticket manually if needed."
            )

# ── Stats: live session usage vs. fixed golden-set eval ──────────────────────────
# These are two different things, shown side by side but never merged into one number:
# live stats are real queries actually run through this app (logs.csv, grows over time);
# the eval below is a fixed 10-query regression check (eval.py), independent of usage.
st.divider()

with st.expander("📊 Live session stats — from logs.csv (real queries run through this app)", expanded=False):
    live = _analyze_mod.summary_stats()
    st.caption(
        "Real usage logged by this app during testing/demo — not the fixed golden-set "
        "eval below. logs.csv starts empty; every row here came from an actual query "
        "submitted above. Run standalone: `python analyze_logs.py`."
    )

    if live["n"] == 0:
        st.info("No queries logged yet — run a query above to populate logs.csv.")
    else:
        if live["low_sample"]:
            st.warning(
                f"Only {live['n']} quer{'y' if live['n'] == 1 else 'ies'} logged — "
                f"sample size too small for a stable rate. Numbers below are illustrative "
                f"only, not a reliable rate."
            )

        c1, c2 = st.columns(2)
        c1.metric("Total logged queries", live["n"])
        c2.metric(
            "Automation rate (SELF_SERVE+AUTO_FIX / non-OUT_OF_SCOPE)",
            f"{live['automation_rate']:.0f}%" if live["automation_rate"] is not None else "n/a",
        )

        st.markdown("**Count and % by decision path**")
        st.dataframe(
            [
                {"Path": p, "Count": live["counts"][p], "%": f"{live['pct'][p]:.0f}%"}
                for p in _analyze_mod.PATHS
            ],
            width="stretch",
            hide_index=True,
        )

        st.markdown(
            "**Agent response time** (proxy for MTTR — measures decision latency, "
            "not full ticket resolution), avg by path"
        )
        st.dataframe(
            [
                {
                    "Path": p,
                    "Avg response time (s)": (
                        f"{live['avg_response_time_sec'][p]:.2f}"
                        if live["avg_response_time_sec"][p] is not None else "n/a"
                    ),
                }
                for p in _analyze_mod.PATHS
            ],
            width="stretch",
            hide_index=True,
        )

with st.expander("🧪 Evaluation — golden-set results", expanded=False):
    eval_rows, eval_summary = _run_eval_cached()
    st.caption(
        f"{eval_summary['n']} hand-labeled queries — a regression check on this KB "
        f"and prompt, not an external benchmark. Run standalone: `python eval.py`."
    )
    m1, m2 = st.columns(2)
    m1.metric("Retrieval accuracy", f"{eval_summary['retrieval_accuracy']:.0%}")
    m2.metric("Path accuracy", f"{eval_summary['path_accuracy']:.0%}")

    st.dataframe(
        [
            {
                "Query": r["query"],
                "Expected units": ", ".join(sorted(r["expected_units"])) or "(none)",
                "Retrieved units": ", ".join(r["retrieved_units"]) or "(none)",
                "Top-1": "✓" if r["top1_correct"] else "✗",
                "Expected path": "/".join(sorted(r["expected_path"])),
                "Actual path": r["actual_path"],
                "Path": "✓" if r["path_correct"] else "✗",
            }
            for r in eval_rows
        ],
        width="stretch",
        hide_index=True,
    )
