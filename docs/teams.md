<!-- docs/teams.md -->
# Teams — Incorrect Presence Status / App Not Loading

**Applies to:** Microsoft Teams, presence status, chat/calls

**Reported symptoms:** Status stuck on "Offline" or "Away" despite active use, or chats/calls fail to load and the app becomes unresponsive.

**Known causes on record:**
- Corrupted local Teams cache (common after a client update)
- Stale sign-in session not refreshing

**Standard checks:** pending Teams updates, whether a manual sign-out/sign-in resolves it, size/state of the local cache folder.

**Notes:** Cache clears usually fix this immediately. If the issue returns within the same day across multiple users, escalate — it's likely tenant-side, not local.