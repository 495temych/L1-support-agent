import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import streamlit as st
from agent import run_triage
from tools import dispatch

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
    ("pending_preset", None),
    ("use_retrieval", True),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Callbacks ───────────────────────────────────────────────────────────────────
def _confirm():
    r = st.session_state.result
    st.session_state.tool_result = dispatch(r["tool_name"], r["tool_input"] or {})
    st.session_state.tool_state = "confirmed"


def _cancel():
    st.session_state.tool_state = "cancelled"


def _set_preset(q: str):
    st.session_state.pending_preset = q
    st.session_state.result = None
    st.session_state.tool_state = None
    st.session_state.tool_result = None


def _init_tool_state(result: dict):
    needs = result["tool_name"] is not None and result["path"] in ("AUTO_FIX", "ESCALATE")
    st.session_state.tool_state = "pending" if needs else None
    st.session_state.tool_result = None


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
    "My VPN keeps disconnecting",
    "Teams shows me as offline to everyone",
    "I'm locked out of my account",
    "My OneDrive has been stuck syncing for two days",
    "My external monitor isn't detected when docked",
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
        placeholder="e.g.  My VPN keeps disconnecting since the migration last month",
        height=90,
    )
    submitted = st.form_submit_button("Analyze →", type="primary")

# ── Execute triage ──────────────────────────────────────────────────────────────
if st.session_state.pending_preset:
    q = st.session_state.pending_preset
    st.session_state.pending_preset = None
    with st.spinner("Analyzing…"):
        result = run_triage(q, st.session_state.use_retrieval)
    st.session_state.result = result
    _init_tool_state(result)

if submitted and query.strip():
    with st.spinner("Running triage…"):
        result = run_triage(query.strip(), st.session_state.use_retrieval)
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
            ti       = result["tool_input"] or {}
            queue    = ti.get("queue", "DESKTOP-SUPPORT")
            summary  = ti.get("summary", "—")
            priority = ti.get("priority", "P3-Normal")

            # Ticket card
            with st.container(border=True):
                st.markdown("**Proposed escalation ticket**")
                st.markdown(f"Queue: `{queue}`")
                st.markdown(f"Summary for technician: {summary}")
                st.markdown(f"Priority: `{priority}`")

            state = st.session_state.tool_state

            if state == "pending":
                _pending_callout(
                    f"This will open a ticket in <strong>{queue}</strong> "
                    f"and notify the on-call technician."
                )
                c1, c2, _ = st.columns([2, 2, 3])
                with c1:
                    st.button("✓ Confirm — create ticket", on_click=_confirm,
                              type="primary", use_container_width=True)
                with c2:
                    st.button("✗ Cancel", on_click=_cancel, use_container_width=True)

            elif state == "confirmed" and st.session_state.tool_result:
                tr     = st.session_state.tool_result
                ticket = tr.get("ticket_number", "INC?")
                st.success(f"**Ticket #{ticket} created (simulated)**\n\n{tr['detail']}")
                st.caption(f"Timestamp: {tr['timestamp']}")

            elif state == "cancelled":
                st.warning("Escalation skipped by operator. No ticket created.")

        else:
            # Fallback: agent chose ESCALATE but didn't call the ticket tool.
            # After the prompt fix this shouldn't occur, but handle gracefully.
            st.warning(
                "The agent recommends escalation but did not propose a specific ticket. "
                "Review the reasoning above and raise a ticket manually if needed."
            )
