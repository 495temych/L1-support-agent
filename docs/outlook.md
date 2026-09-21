<!-- docs/outlook.md -->
# Outlook — Repeated Sign-In Prompts / Not Syncing

**Applies to:** Outlook, Microsoft 365, Exchange, credential caching

**Reported symptoms:** Outlook prompts for a password every 30-60 minutes, or the status bar shows "Disconnected" while mail stops updating.

**Known causes on record:**
- Stale cached credentials in Windows Credential Manager
- Corrupted local Outlook profile
- Expired modern-auth token

**Standard checks:** Credential Manager entries for Outlook/Office, Outlook connection status indicator, whether the issue is device-specific or account-wide.

**Notes:** If clearing cached credentials doesn't hold after a day, the profile itself is usually the problem and typically needs a rebuild.