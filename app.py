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
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Callbacks for human-in-the-loop confirmation ────────────────────────────────
def _confirm():
    r = st.session_state.result
    st.session_state.tool_result = dispatch(r["tool_name"], r["tool_input"] or {})
    st.session_state.tool_state = "confirmed"


def _cancel():
    st.session_state.tool_state = "cancelled"


# ── Path badge (inline HTML) ────────────────────────────────────────────────────
_PATH_COLORS = {
    "SELF_SERVE": ("#1a7f37", "#dafbe1"),
    "AUTO_FIX":   ("#0550ae", "#dbeafe"),
    "ESCALATE":   ("#9a3412", "#fef3c7"),
}

def _badge(path: str) -> str:
    fg, bg = _PATH_COLORS.get(path, ("#555", "#eee"))
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {fg}33;'
        f'padding:4px 12px;border-radius:5px;font-weight:700;'
        f'font-size:0.95em;letter-spacing:0.03em">{path}</span>'
    )


# ── Header ──────────────────────────────────────────────────────────────────────
st.title("L1 Support Agent")
st.caption("Limmatica AG · internal IT triage demo · powered by Claude")
st.divider()

# ── Input form ──────────────────────────────────────────────────────────────────
with st.form("query_form", clear_on_submit=False):
    query = st.text_area(
        "Describe the issue",
        placeholder="e.g.  My VPN keeps disconnecting since the migration last month",
        height=110,
    )
    col_toggle, col_btn = st.columns([3, 1])
    with col_toggle:
        use_retrieval = st.toggle("Use retrieval (RAG)", value=True)
    with col_btn:
        submitted = st.form_submit_button("Analyze →", type="primary", use_container_width=True)

if submitted and query.strip():
    with st.spinner("Running triage…"):
        result = run_triage(query.strip(), use_retrieval)
    st.session_state.result = result
    st.session_state.tool_state = "pending" if result["path"] == "AUTO_FIX" else None
    st.session_state.tool_result = None

# ── Results ─────────────────────────────────────────────────────────────────────
if st.session_state.result:
    result = st.session_state.result
    st.divider()

    # 1 · Retrieval
    st.subheader("1 · Retrieval")
    if result["retrieved"]:
        r = result["retrieved"]
        with st.expander(
            f"**{r['name']}** — similarity {r['score']:.2f}",
            expanded=False,
        ):
            st.markdown(r["content"])
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

    if path == "SELF_SERVE":
        st.success("Steps are in the reasoning above — user can action these directly.")

    elif path == "ESCALATE":
        st.warning("Escalation required — diagnostic summary is in the reasoning above.")

    elif path == "AUTO_FIX":
        tool_name = result["tool_name"] or "unknown"
        tool_input = result["tool_input"] or {}

        with st.container(border=True):
            st.markdown(f"**Tool:** `{tool_name}`")
            if tool_input:
                for k, v in tool_input.items():
                    st.markdown(f"- `{k}`: `{v}`")

        state = st.session_state.tool_state

        if state == "pending":
            st.markdown(
                "> **Human-in-the-loop:** this action will not run until you confirm below."
            )
            c1, c2, _ = st.columns([2, 2, 3])
            with c1:
                st.button(
                    "✓ Confirm — run action",
                    on_click=_confirm,
                    type="primary",
                    use_container_width=True,
                )
            with c2:
                st.button(
                    "✗ Cancel",
                    on_click=_cancel,
                    use_container_width=True,
                )

        elif state == "confirmed" and st.session_state.tool_result:
            tr = st.session_state.tool_result
            st.success(f"**Action executed (simulated)**\n\n{tr['detail']}")
            st.caption(f"Timestamp: {tr['timestamp']}")

        elif state == "cancelled":
            st.warning("Action cancelled by operator. No changes made.")
