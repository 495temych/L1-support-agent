<!-- docs/account-access.md -->
# Account Lockout / Password Reset

**Applies to:** Active Directory, account lockout, password reset, MFA

**Reported symptoms:** "Account locked" message after failed sign-in attempts, or a forgotten password blocking access on all devices.

**Known causes on record:**
- Standard lockout after repeated failed logins
- Expired password under rotation policy
- Genuinely forgotten credentials

**Standard checks:** identity verification (security question or MFA), lockout timestamp and failed-attempt count on the account.

**Notes:** A single lockout is routine. Multiple lockouts within a short window on the same account should be treated as a possible compromise, not a routine reset.