<!-- docs/vpn.md -->
# KB-0142 — VPN: GlobalProtect Connection Drops / Gateway Unreachable

**Category:** Network Access | **Owner team:** Network Ops | **Last updated:** 2026-08-14 by M. Rohner

**Environment:** Limmatica AG uses Palo Alto GlobalProtect (client v6.2.1+) via portal `vpn-gp.limmatica.corp`. Migrated from Cisco AnyConnect in Q1 2026 — legacy portal `vpn.limmatica.corp` was decommissioned 2026-03-31.

**Recurring pattern (12 tickets logged since migration):** Users still configured with the legacy AnyConnect profile fail silently or loop on "unable to reach gateway." Root cause in 9/12 cases: stale gateway entry pointing to the decommissioned portal.

**Other confirmed causes:**
- Client cert expired (renewed automatically via SCEP, but fails if device was offline >30 days — ticket #INC0041207)
- MFA app (Okta Verify) clock drift >60s causes silent token rejection, no error shown to user
- Client version <6.2.1 incompatible with new portal's TLS config

**Verified resolution steps (per INC0041207, INC0041355):**
1. Confirm gateway field reads `vpn-gp.limmatica.corp`, not the legacy address
2. If cert error: run `\\IT-TOOLS\Scripts\reset-vpn-profile.ps1` from IT Tools share — regenerates cert via SCEP, takes ~90s
3. If MFA-related: instruct user to force-sync Okta Verify (Settings > Sync Now)

**Escalation path:** If gateway/cert/MFA all check out and issue persists, escalate to Network Ops queue `NET-VPN` in ServiceNow — likely a firewall rule issue on our side, not user-fixable. SLA: 4 business hours.