<!-- docs/onedrive.md -->
# KB-0231 — OneDrive: Sync Stuck / "Processing Changes"

**Category:** M365 | **Owner team:** M365 Support | **Last updated:** 2026-07-28 by S. Baumgartner

**Environment:** OneDrive for Business, 1TB default quota per `LIC-M365-E3`. Known issue: filenames containing `#` or `%` fail to sync silently (documented Microsoft limitation, not Limmatica-specific).

**Recurring pattern:** Finance team users (heavy Excel file-naming with `#` for report versioning, e.g. `Q2_Report#final.xlsx`) account for a disproportionate share of these tickets — worth asking department first.

**Confirmed causes:**
- Quota exceeded (check via OneDrive admin center, not just client — client sometimes shows stale quota)
- Filename contains unsupported character (`#`, `%`, or path >400 chars)
- Backend sync service disruption — occurred tenant-wide 2026-04-11, ref `INC0038802`, Microsoft-side, no local fix existed

**Verified resolution steps:**
1. Check quota first via `admin.microsoft.com` > OneDrive usage report
2. Ask which files aren't syncing — check for `#`/`%` in filenames, especially if user is in Finance
3. If neither applies: check M365 Service Health for active OneDrive incidents before spending more time locally

**Escalation:** If quota and filenames check out and no active Microsoft incident, escalate to `M365-SYNC` — requires backend sync log pull, not resolvable at desktop level.