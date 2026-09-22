<!-- docs/wifi.md -->
# KB-0156 — Wi-Fi: Drops on LIMMATICA-CORP SSID

**Category:** Network | **Owner team:** Network Ops | **Last updated:** 2026-06-30 by M. Rohner

**Environment:** Corporate SSID `LIMMATICA-CORP` (WPA2-Enterprise, Aruba APs, floors 3-7 of Sihlquai office). Guest network `LIMMATICA-GUEST` is separate infrastructure and unaffected by these issues.

**Recurring pattern:** Floor 5 has a known AP congestion issue near the open-plan area (>40 concurrent devices on one Aruba AP-515) — logged as a known limitation pending Q4 2026 AP density upgrade, not a per-ticket fixable issue.

**Confirmed causes:**
- Outdated Intel Wi-Fi driver on ThinkPad T14 fleet (pre-2026-05 image) — device-side
- Floor 5 AP congestion (infrastructure-side, see above)
- Certificate-based auth (EAP-TLS) failure after device re-image — device drops off silently

**Verified resolution steps:**
1. Ask: is this one device or has it been reported by multiple people on the same floor? Determines path.
2. Single device: check driver version via Device Manager, update via Intune if pre-2026-05
3. Floor 5, multiple users: this is the known congestion issue — log ticket for tracking but do not spend time troubleshooting client-side, reference `NET-WIFI-FLOOR5-KNOWN`

**Escalation:** New pattern (not floor 5, not driver-related) → escalate to `NET-WIFI` for AP-side log review.