<!-- docs/wifi.md -->
# Wi-Fi — Drops on a Specific Network

**Applies to:** Wi-Fi, wireless adapter, network connectivity

**Reported symptoms:** Repeated disconnects on the corporate SSID specifically, while other networks (e.g. mobile hotspot) remain stable.

**Known causes on record:**
- Outdated or corrupted network adapter driver (device-side)
- Access point congestion or channel interference (infrastructure-side)

**Standard checks:** whether the issue affects one device or several users on the same access point, adapter driver version, signal strength relative to the nearest AP.

**Notes:** A single affected device usually points to the driver. Multiple users on the same AP reporting the same issue points to infrastructure — different fix path entirely.