import os
import sys
import importlib
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
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Callbacks ───────────────────────────────────────────────────────────────────
def _confirm():
    r = st.session_state.result
    st.session_state.tool_result = _tools_mod.dispatch(r["tool_name"], r["tool_input"] or {})
    st.session_state.tool_state = "confirmed"


def _cancel():
    st.session_state.tool_state = "cancelled"


def _set_preset(q: str):
    """Populate the text field with the preset query; user still clicks Analyze."""
    st.session_state.query_text = q


def _init_tool_state(result: dict):
    import random
    needs = result["tool_name"] is not None and result["path"] in ("AUTO_FIX", "ESCALATE")
    st.session_state.tool_state = "pending" if needs else None
    st.session_state.tool_result = None
    # Generate a stable preview ticket ID shown before and after confirmation
    if result["path"] == "ESCALATE":
        st.session_state.preview_ticket_id = f"INC{random.randint(1000000, 9999999)}"


# ── Helpers ─────────────────────────────────────────────────────────────────────
_PATH_COLORS = {
    "SELF_SERVE":   ("#1a7f37", "#dafbe1"),
    "AUTO_FIX":     ("#0550ae", "#dbeafe"),
    "ESCALATE":     ("#9a3412", "#fef3c7"),
    "OUT_OF_SCOPE": ("#555555", "#f0f0f0"),
}

def _badge(path: str) -> str:
    fg, bg = _PATH_COLORS.get(path, ("#555", "#eee"))
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {fg}33;'
        f'padding:4px 12px;border-radius:5px;font-weight:700;'
        f'font-size:0.95em;letter-spacing:0.03em">{path}</span>'
    )


def _pending_callout(label: str) -> None:
    """Renders the 'awaiting confirmation' banner above Confirm/Cancel buttons."""
    st.markdown(
        f'<div style="background:#fffbeb;border:1px solid #f59e0b;border-radius:6px;'
        f'padding:10px 14px;margin:10px 0 8px 0;">'
        f'<strong>&#9888;&#65039; Human-in-the-loop — awaiting your decision</strong><br/>'
        f'<span style="font-size:0.9em">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Presets ─────────────────────────────────────────────────────────────────────
PRESETS = [
    # AUTO_FIX demos
    "My VPN keeps disconnecting",
    "Teams shows me as offline to everyone",
    "Floor 5 print queue is stuck, several people can't print",
    "My VPN cert error persists, I've confirmed the gateway is correct and I was offline for a month",
    "I need Zoom installed but I don't have admin rights — it's listed in Company Portal",
    # ESCALATE demos
    "I'm locked out of my account",
    "My OneDrive has been stuck syncing for two days",
    "My external monitor isn't detected when docked",
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
    with st.spinner("Running triage…"):
        result = run_triage(query.strip(), st.session_state.use_retrieval)
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
    _init_tool_state(result)

# ── Results ─────────────────────────────────────────────────────────────────────
if st.session_state.result:
    result = st.session_state.result
    st.divider()

    # 1 · Retrieval
    st.subheader("1 · Retrieval")
    if result["retrieved"]:
        r = result["retrieved"]
        with st.expander(f"**{r['name']}** — similarity {r['score']:.2f}", expanded=False):
            st.markdown(r["content"])

        highlights = r.get("highlights", [])
        if highlights:
            st.markdown("**Why this document matched — top passages:**")
            for h in highlights:
                # Strip markdown characters for clean plain-text display in the highlight strip
                clean = h["text"].replace("**", "").replace("`", "").replace("*", "")
                st.markdown(
                    f'<div style="background:#fffbeb;border-left:3px solid #f59e0b;'
                    f'padding:5px 10px;margin:3px 0;font-size:0.88em;line-height:1.4;">'
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

    elif path == "OUT_OF_SCOPE":
        st.info("Outside IT support scope — no action taken.")

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

        elif state == "cancelled":
            st.warning("Action skipped by operator. No changes made.")

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
