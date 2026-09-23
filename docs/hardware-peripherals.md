<!-- docs/hardware-peripherals.md -->
# KB-0261 — Peripherals: Dock/Monitor Not Detected

**Category:** Hardware | **Owner team:** Desktop Support | **Last updated:** 2026-07-19 by T. Iten

**Environment:** Standard desk setup fleet-wide is a Dell WD22TB4 Thunderbolt dock paired with a Dell UltraSharp U2723QE monitor (single-monitor desks) or dual U2723QE on senior/Finance desks. Rollout completed 2026-04 — replaced the older CalDigit TS3+ docks, which are still in circulation on ~40 legacy desks pending replacement.

**Recurring pattern:** 18 tickets logged since the Dell WD22TB4 rollout, 13 of which trace to Thunderbolt cable seating — the dock's Thunderbolt 4 port is easy to half-insert without a click, unlike the older CalDigit's magnetic connector, and support hasn't fully retrained users on the new connector.

**Confirmed causes:**
- Thunderbolt cable not fully seated (most common post-rollout — see above)
- WD22TB4 firmware outdated — firmware v5.2 and below has a known cold-boot detection bug, fixed in v5.4 (check via Dell Peripheral Manager)
- U2723QE monitor set to wrong input source (defaults to DP but dock outputs via USB-C — common on desks where a monitor was swapped)
- Legacy CalDigit TS3+ docks (pre-rollout) — known to drop external displays after macOS/Windows sleep, no fix exists, flagged for replacement
- USB-C port failure on the ThinkPad T14 itself (rare, confirmed only on 2 devices from the same manufacturing batch, ref `INC0040561`)

**Verified resolution steps:**
1. Confirm dock model first — WD22TB4 or legacy CalDigit TS3+ (check label on underside of dock). Determines which path below applies.
2. **WD22TB4:** reseat the Thunderbolt cable fully (should click), check firmware version via Dell Peripheral Manager — update to v5.4+ if below
3. **U2723QE showing "no signal":** check input source is set to USB-C (labeled "DP Alt Mode" in the monitor's OSD menu), not DP
4. **Legacy CalDigit TS3+:** if issue is post-sleep display drop, this is a known unfixable limitation — log for `HW-REPLACE` queue rather than troubleshooting further
5. Test peripheral (keyboard/mouse/USB) directly on the laptop's own USB-C port, bypassing the dock, to isolate dock-vs-device fault

**Escalation:** If Device Manager shows no device detected at all (not even "unrecognized device") after confirming cable seating and firmware, this is physical hardware failure — escalate to `HW-REPLACE`. Do not attempt further remote troubleshooting; replacement dock/cable required, technician must bring a spare WD22TB4 for swap-test on site.