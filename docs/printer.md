<!-- docs/printer.md -->
# KB-0089 — Printer: bizhub Fleet Offline / Stuck Queue

**Category:** Peripherals | **Owner team:** Desktop Support | **Last updated:** 2026-07-02 by T. Iten

**Environment:** Limmatica AG print fleet is Konica Minolta bizhub C4051i, managed via PaperCut MF. Print server: `PRINT01.limmatica.corp`.

**Recurring pattern:** Spooler service (`spoolsv.exe`) hangs after the nightly PaperCut sync job (runs 02:00 CET) roughly 2x/month, affecting all users on a given floor's print queue simultaneously — this is the key signal distinguishing a spooler issue from a single dead print job.

**Confirmed causes:**
- Spooler hung post-sync (floor-wide pattern — see above)
- Single stuck job with corrupted print data (isolated to one user)
- Driver mismatch after the 2026-05 Windows Universal Print rollout — legacy KM driver conflicts with UP driver on some ThinkPads

**Verified resolution steps:**
1. Check if issue is floor-wide (Teams channel #it-floor-status) or single-user — determines which path below applies
2. Floor-wide: restart Print Spooler service on `PRINT01` (Desktop Support has remote access) — do NOT ask user to restart locally, this won't fix a server-side hang
3. Single-user: clear local queue via `services.msc` > Print Spooler > restart, then re-add printer via PaperCut portal `print.limmatica.corp`

**Escalation:** If floor-wide and spooler restart doesn't clear it within 15 min, escalate to `NET-PRINT` — possible PaperCut sync job failure requiring vendor support ticket.