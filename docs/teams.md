<!-- docs/teams.md -->
# KB-0217 — Teams: Presence Stuck / App Unresponsive

**Category:** M365 | **Owner team:** M365 Support | **Last updated:** 2026-08-05 by S. Baumgartner

**Environment:** Teams (new client, migrated fleet-wide 2026-06). Known regression in build 26189 caused presence bugs org-wide for ~3 days (INC0040112 through INC0040129, 14 tickets) — since patched.

**Confirmed causes:**
- Corrupted local cache at `%appdata%\Microsoft\Teams` (new client: `%localappdata%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache`)
- Stale session not refreshing after laptop sleep/wake
- Build 26189 regression (patched 2026-06-18 — if user is on an older build, this is likely the cause)

**Verified resolution steps:**
1. Check Teams build version first (Settings > About) — if pre-26189-patch, flag for forced update via Intune, this alone often resolves it
2. If up to date: fully quit Teams (not just close window — check Task Manager for lingering `ms-teams.exe`), clear LocalCache folder, relaunch
3. Confirm presence resolves within 2 min of relaunch

**Escalation:** If cache clear doesn't hold and multiple users on the same tenant report simultaneously, escalate to `M365-TENANT` — likely a Microsoft-side service health issue, check M365 Service Health dashboard first before escalating.