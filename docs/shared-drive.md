<!-- docs/shared-drive.md -->
# KB-0174 — Shared Drives: Path Unreachable

**Category:** File Services | **Owner team:** Infrastructure | **Last updated:** 2026-07-10 by T. Iten

**Environment:** Legacy mapped drives (`\\FS01.limmatica.corp\...`) still used by Finance and Legal departments alongside SharePoint migration (in progress, target completion Q1 2027).

**Confirmed causes:**
- VPN not connected (remote users) — check this first, majority of tickets
- Permissions changed after the 2026-06 AD group restructuring (`LIMMATICA\Finance-RW` replaced older `LIMMATICA\Fin-Users` group — some permissions didn't migrate cleanly)
- `FS01` server maintenance window (Tuesdays 22:00-23:00 CET, scheduled)
- Mapped drive letter conflict after a new USB/network device took the same letter

**Verified resolution steps:**
1. Confirm VPN status first for remote users
2. Check if issue is isolated to Finance/Legal paths specifically — if so, likely the June AD group migration, verify user is in `Finance-RW` not the deprecated `Fin-Users`
3. Re-map drive via `\\IT-TOOLS\Scripts\map-drives.bat` (pulls correct paths per department from central script)

**Escalation:** If multiple users report the same path down outside the Tuesday maintenance window, escalate immediately to `INFRA-FS01` — do not assume it's the scheduled window without checking the date/time.