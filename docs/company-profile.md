<!-- docs/company-profile.md -->
# Limmatica AG — IT Environment Reference

**Category:** Organizational Context | **Owner team:** IT Operations | **Last updated:** 2026-08-25 by IT Ops Team

This document is the master reference other KB articles assume you already know. Not a troubleshooting guide — a snapshot of what Limmatica AG actually runs, so support decisions stay consistent across tickets.

---

## Company

Limmatica AG — mid-size financial services firm, ~850 employees, headquartered at Sihlquai 231, Zurich, floors 3-7. IT Operations team of 6, split into Network Ops, Desktop Support, M365 Support, and Security Ops (see escalation queues below).

## Core systems

| System | Product | Notes |
|---|---|---|
| Identity | Active Directory (`LIMMATICA` domain) + Okta SSO | Okta Verify is the MFA app of record; security questions deprecated Feb 2026 |
| VPN | Palo Alto GlobalProtect | Migrated from Cisco AnyConnect, Q1 2026 |
| Email/Collab | Microsoft 365 E3 (`LIC-M365-E3`) | Outlook, Teams, OneDrive, SharePoint |
| Endpoint security | CrowdStrike Falcon | Full scans Sundays 03:00 CET, ad hoc after signature updates |
| Device management | Microsoft Intune (Autopilot) | Standard image: Lenovo ThinkPad T14 Gen 4, 16GB RAM |
| Print | Konica Minolta bizhub C4051i fleet, PaperCut MF | Server: `PRINT01.limmatica.corp` |
| File shares | Legacy mapped drives (`FS01.limmatica.corp`) + SharePoint | SharePoint migration target: Q1 2027 |
| Ticketing | ServiceNow | Incident records, see field mapping in README |

## Naming conventions (used consistently across all KB articles)

- Internal domains: `*.limmatica.corp`
- KB article IDs: `KB-0XXX`
- Ticket IDs: `INC00XXXXX` (ServiceNow format)
- Escalation queues: `<TEAM>-<AREA>`, e.g. `NET-VPN`, `M365-SYNC`, `SEC-INCIDENT`

## Escalation queues (assignment groups)

| Queue | Owns | Typical SLA |
|---|---|---|
| `NET-VPN` | VPN/gateway/certificate issues | 4 business hours |
| `NET-PRINT` | Print server/spooler infrastructure | 4 business hours |
| `NET-WIFI` | Wireless AP/infrastructure issues | 4 business hours |
| `M365-PROFILE` | Outlook profile rebuilds | 1 business day |
| `M365-TENANT` | Teams/tenant-wide service issues | Check M365 Service Health first |
| `M365-SYNC` | OneDrive backend sync issues | 1 business day |
| `INFRA-FS01` | Legacy file server issues | 4 business hours |
| `HW-REPLACE` | Physical hardware replacement | 2 business days |
| `SEC-INCIDENT` | Suspected account compromise | Immediate, Security Ops |

## Governing policies referenced across KB articles

- **SEC-04** (rev. March 2026) — account lockout policy: 5 failed attempts/15 min → lockout, 30-min auto-unlock or manual unlock. §4.2: 2+ lockouts in 24h treated as possible compromise, routine unlock forbidden, must escalate.
- **SEC-07** (since Sept 2025) — standard users run without local admin rights. Software installs go through the Company Portal catalog (47 approved titles as of last audit) or a `SR-SOFTWARE` request with manager approval.

## Known organizational quirks (context, not bugs)

- Finance team's Excel naming habit (`#` in filenames for report versioning) is the leading cause of OneDrive sync tickets from that department specifically.
- Floor 5's open-plan area has a known Wi-Fi AP congestion issue (>40 concurrent devices on one Aruba AP-515), pending a Q4 2026 density upgrade — not fixable per-ticket.
- Lockout tickets spike every Monday morning, correlating with the Friday password-rotation reminder being forgotten over the weekend.

---

*Every other KB article in this base assumes the systems, naming conventions, and policies documented here. If a ticket references something not covered by this profile, treat it as genuinely out of scope for automated resolution.*