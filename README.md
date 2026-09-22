# L1 Support Agent — Limmatica AG

## What & why

First-line IT support is disproportionately expensive relative to what it mostly does: match a user's complaint against a known procedure and either hand back a checklist, trigger a routine action, or escalate when neither applies. A technician who knows the company can do this in 30 seconds; someone new cannot — the knowledge is in their head, not in the ticket system. This project explores whether a small LLM agent, grounded in org-specific knowledge via retrieval, can reliably reproduce that "fast, context-aware" path, and whether the grounding actually matters or whether a pre-trained model's general knowledge is already sufficient.

---

## Architecture

```
User query
    │
    ▼
[Retrieval — retrieval.py]
  sentence-transformers (all-MiniLM-L6-v2, local)
  Cosine similarity over 10 KB articles
  Threshold 0.35 → returns None on low confidence
    │
    ▼                         (RAG off: this step is skipped)
Retrieved article or None
    │
    ▼
[Agent — agent.py]
  Claude (claude-haiku-4-5) + system prompt from prompt.md
  Context: retrieved article injected into user message
    │
    ├── SELF_SERVE ──→ numbered steps returned to user
    │
    ├── AUTO_FIX ────→ tool call proposed (name + params)
    │                      │
    │                      ▼
    │               Human confirmation (app.py)
    │                      │
    │                      ▼
    │               tools.py dispatch (mocked)
    │
    └── ESCALATE ───→ diagnostic summary for technician
```

**Three decision paths:**

| Path | When | What happens |
|---|---|---|
| **SELF_SERVE** | Fix is documented, safe, and simple enough for the user | Agent returns numbered steps; user self-resolves |
| **AUTO_FIX** | Fix is safe, reversible, and better executed by the agent | Agent proposes a specific tool call; operator must confirm before it runs |
| **ESCALATE** | Issue is ambiguous, infrastructure-side, or confidence is low | Agent summarises diagnostic findings for a human technician |

---

## Why RAG matters here

The RAG toggle exists to make a specific, demonstrable point: **general LLM knowledge gives generic advice; org-specific knowledge gives org-specific procedures.**

With RAG **off**, Claude might suggest "try reinstalling the VPN client" for a GlobalProtect connection issue — correct in spirit, but not actionable for Limmatica. It doesn't know the correct portal address (`vpn-gp.limmatica.corp`), the decommissioned legacy portal, the SCEP reset script path, or which ServiceNow queue to route to.

With RAG **on**, it knows all of that — because the KB articles are deliberately written with org-specific detail: internal hostnames, AD group names, policy codes, ticket numbers, and historical incident patterns. That specificity is what makes the contrast visible and defensible.

This is also why the threshold matters. Without it, retrieval always returns *something*, even for queries with no KB match. Returning `None` below 0.35 keeps the comparison honest.

---

## Demo script

| Query | Path | What it shows |
|---|---|---|
| `My VPN keeps disconnecting since the migration` | AUTO_FIX → `reset_vpn_profile` | RAG-off gives generic advice; RAG-on cites the AnyConnect→GlobalProtect migration, the SCEP cert, and the exact script path |
| `Teams is showing me as offline and won't respond` | AUTO_FIX → `clear_teams_cache` | With RAG, agent checks build version first (26189 regression); without RAG it skips that context |
| `I'm locked out of my account — it's happened three times this week` | ESCALATE | Key demo: agent correctly refuses AUTO_FIX because 2+ lockouts in 24 h is a SEC-04 §4.2 compromise indicator, not a routine unlock |
| `All the printers on my floor stopped working` | AUTO_FIX → `restart_print_spooler` | Shows floor-wide vs single-user triage logic; RAG provides the PaperCut sync pattern that explains the failure |
| `My OneDrive has been stuck on processing changes for two days` | SELF_SERVE or ESCALATE | Demonstrates the agent asking the right qualifying question (Finance user? filenames with `#`?); outcome depends on what context RAG supplies |
| `What's the weather like today?` | ESCALATE | No KB match above threshold (retrieval returns None); model correctly stays in-scope rather than hallucinating relevance |

---

## Design decisions worth defending

**Why one file per KB article?**
Each article is the retrieval unit. Chunking a single large document would require overlap tuning and introduces boundary ambiguity. One article per file gives clean, semantically coherent units with zero chunking overhead. The corpus is small enough that this is unambiguously correct at this scale — at hundreds of articles you'd revisit chunking, not before.

**Why mocked tools?**
The demo runs locally against real Limmatica-style procedures without any actual AD/Intune/PaperCut access. Mocking preserves the complete decision path (retrieval → triage → confirmation → dispatch → result) without infrastructure dependencies. A reviewer can trace every step without anything changing on a real system.

**Why a similarity threshold (0.35)?**
Without it, retrieval always returns the closest match, even for irrelevant queries — and the agent may hallucinate grounding from a weakly related article. The threshold makes the "no confident match" case explicit and keeps the RAG-on/off comparison honest.

**Why human-in-the-loop confirmation for AUTO_FIX?**
The system prompt forbids tool calls without explicit operator confirmation. This isn't just a safety feature — it reflects correct system design. An agent that silently unlocks accounts or restarts production services is a liability, especially in a security-sensitive environment (SEC-04, SEC-07). The confirmation step makes this principle visible in the demo, not just in the code.

**Why the same code path for RAG on/off?**
`use_retrieval` is a single boolean parameter to `run_triage`. The rest of the pipeline — the same prompt, the same tools, the same response parsing — is identical. This means the comparison is valid: the only variable is whether retrieved context was injected.

---

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
streamlit run app.py
```

The first run downloads the `all-MiniLM-L6-v2` model (~90 MB) and builds embeddings for the 10 KB articles. Both are cached in memory for the session.

---

## What's next / known limitations

- **Synthetic KB articles.** All 10 documents were written for this demo. Real deployment needs actual company documentation, which varies widely in quality, consistency, and coverage.
- **Mocked tools.** No real actions are taken. Production integration requires secure service accounts with least-privilege access to AD, Intune, PaperCut, and ServiceNow.
- **Small corpus (10 articles).** Embedding quality and threshold calibration need revalidation at scale. With hundreds of articles, top-k retrieval and optional re-ranking become necessary.
- **Single-turn only.** The agent doesn't maintain conversation history. Real triage often requires clarifying questions across multiple turns before a path can be determined.
- **Username as free text.** Tools accept usernames as unvalidated strings. A real deployment would resolve these against AD or Okta before calling any tool.
- **No evaluation set.** The threshold (0.35) and model choice are set by inspection, not by measured precision/recall against a labelled query set.
