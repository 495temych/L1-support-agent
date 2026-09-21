<!-- docs/printer.md -->
# Printer — Offline / Stuck Print Queue

**Applies to:** Printers, print spooler, network printers

**Reported symptoms:** Printer shows "offline" in Devices & Printers, or jobs sit in the queue without printing.

**Known causes on record:**
- Print spooler service hung or crashed
- Driver mismatch after a Windows update
- Printer physically powered off or dropped from network

**Standard checks:** printer power/network status, queue contents, spooler service status (Services > Print Spooler).

**Notes:** If the queue clears but the issue recurs daily, it's usually a driver problem, not a one-off.