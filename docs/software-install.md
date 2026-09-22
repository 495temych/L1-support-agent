<!-- docs/software-install.md -->
# KB-0112 — Software Installation Blocked / Admin Rights

**Category:** Endpoint Management | **Owner team:** Desktop Support | **Last updated:** 2026-06-15 by T. Iten

**Environment:** Standard users are non-admin per `SEC-07` policy (since 2025-09). Approved self-service catalog available via Company Portal (Intune).

**Confirmed causes:**
- Standard account, expected behavior (not a fault) — most common ticket type in this category by volume
- Software not in the approved catalog (Company Portal currently lists 47 approved titles)
- Company Portal itself failing to launch (rare, usually resolved by Intune sync: Settings > Accounts > Access Work/School > Info > Sync)

**Verified resolution steps:**
1. Check Company Portal first — is the software listed? If yes, direct user there, no ticket action needed beyond guidance
2. If not listed: this requires a Software Request via ServiceNow catalog item `SR-SOFTWARE`, needs manager approval — not something support can grant directly
3. If Company Portal won't launch: force Intune sync per steps above

**Escalation:** Pre-approved but urgent one-off need (e.g. client demo in 1 hour) → `DESKTOP-URGENT` queue for temporary elevated install via Intune "Run script" — requires team lead sign-off per `SEC-07` exception process, logged and time-boxed to 24h.