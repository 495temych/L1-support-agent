<!-- docs/laptop-performance.md -->
# KB-0098 — Laptop Performance: ThinkPad T14 Running Slow

**Category:** Hardware/OS | **Owner team:** Desktop Support | **Last updated:** 2026-05-22 by T. Iten

**Environment:** Standard fleet device: Lenovo ThinkPad T14 Gen 4, 16GB RAM, imaged via Intune Autopilot. Known issue: CrowdStrike Falcon sensor full scans (Sundays 03:00, but can trigger ad hoc after signature updates) cause noticeable slowdown for ~20 min.

**Confirmed causes:**
- Low disk space — T14 fleet ships with 256GB SSD, OneDrive "Files On-Demand" not enabled by default on some 2025 images, causing full local sync and disk fill
- CrowdStrike scan in progress (check Task Manager for `CSFalconService` CPU usage)
- Excessive startup items — common after user-installed browser extensions/toolbars
- Battery degradation on devices >2 years old (check via `Lenovo Vantage` battery health report — 20% of the >2yr fleet flagged)

**Verified resolution steps:**
1. Check `CSFalconService` in Task Manager first — if active, this is expected behavior, not a fault, inform user it'll resolve in ~20 min
2. Check disk space — if low, verify OneDrive Files On-Demand is enabled (Settings > OneDrive > Save space)
3. Check startup items via Task Manager > Startup apps

**Escalation:** If device is >2 years old and Vantage reports battery health <60%, escalate to `HW-REPLACE` for battery/device replacement — not a software fix.