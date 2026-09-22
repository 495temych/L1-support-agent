<!-- docs/account-access.md -->
# KB-0067 — Account Lockout / Password Reset

**Category:** Identity | **Owner team:** Security Ops | **Last updated:** 2026-08-01 by M. Rohner

**Environment:** Active Directory domain `LIMMATICA`, synced to Okta for M365/SaaS SSO. Lockout policy per `SEC-04` (rev. March 2026): 5 failed attempts within 15 min → lockout, auto-unlocks after 30 min or manual unlock.

**Recurring pattern:** Lockouts spike every Monday morning (password rotation reminders sent Friday, many users forget over the weekend) — not a security concern on its own, just seasonal ticket volume.

**Confirmed causes:**
- Standard lockout after failed attempts (majority of tickets, especially Mondays — see above)
- Password expired under 90-day rotation policy, user unaware
- Genuinely forgotten credentials

**Verified resolution steps:**
1. Verify identity via Okta Verify push (security questions deprecated org-wide since Feb 2026, do not use)
2. Check lockout timestamp + failed-attempt count in AD Admin Center — confirms it's a standard lockout, not something else
3. Unlock via `Unlock-ADAccount -Identity <username>` (Desktop Support has this delegated permission) or direct user to self-service reset at `reset.limmatica.corp`

**Escalation:** 2+ lockouts within 24 hours on the same account is treated as a possible compromise indicator per `SEC-04` §4.2 — do NOT perform a routine unlock, escalate immediately to `SEC-INCIDENT` for review before any account action.