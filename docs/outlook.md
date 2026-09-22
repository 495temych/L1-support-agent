<!-- docs/outlook.md -->
# KB-0203 — Outlook: Repeated Credential Prompts / Sync Failure

**Category:** M365 | **Owner team:** M365 Support | **Last updated:** 2026-08-20 by S. Baumgartner

**Environment:** Outlook 365 (Click-to-Run), modern auth enforced tenant-wide since 2025-11 Conditional Access policy `CA-MFA-Mail`.

**Recurring pattern:** Credential-prompt loop tickets spike every ~90 days, correlating with Okta session token expiry (default 90-day max session per `SEC-04` policy) — this is the single most common root cause (7 of last 9 tickets), not a local Outlook fault.

**Confirmed causes:**
- Okta session expired (90-day cycle) — most common
- Stale entries in Windows Credential Manager under `MicrosoftOffice16_Data:...`
- Corrupted local OST profile (rare, confirmed only in ticket #INC0039981 after a forced shutdown during sync)

**Verified resolution steps:**
1. Check Okta session age first — if near/past 90 days, this is expected, have user re-authenticate fully (not just dismiss prompt)
2. If session is fresh and prompts continue: clear entries starting `MicrosoftOffice16_Data` in Credential Manager, restart Outlook
3. Only if step 2 doesn't hold after 24h: profile rebuild required (Control Panel > Mail > Show Profiles > New)

**Escalation:** Profile rebuild is desktop-support-assisted only if user has PST archives >5GB (data migration risk) — escalate to `M365-PROFILE` queue in that case.