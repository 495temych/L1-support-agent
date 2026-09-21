<!-- docs/vpn.md -->
# VPN — Connection Drops / Fails to Connect

**Applies to:** VPN, Cisco AnyConnect, remote access, MFA

**Reported symptoms:** Users report the VPN client disconnecting repeatedly, or getting stuck at "unable to reach gateway." Some cases show a successful connection but no actual network access afterward.

**Known causes on record:**
- Client certificate expired (most common, ~60% of VPN tickets last quarter)
- Gateway address outdated after infrastructure migration
- MFA app clock drift causing token mismatch
- Outdated VPN client version

**Standard checks:** certificate expiry date, current gateway address in client config, MFA app time sync, client version.

**Notes:** Certificate renewal requires an IT-issued cert and cannot be resolved client-side.