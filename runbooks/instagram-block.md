# Runbook: Instagram Account Block

## Trigger
Instagram returns block or challenge response during publish attempt. Multiple publish.failed events for same client in short window.

## Symptoms
- last_error contains "block", "challenge", "checkpoint"
- All publish attempts for a client failing
- Unusual pattern in publish.failed events

## Diagnosis Steps
1. Check error type
   - Temporary rate limit? (back off and retry)
   - Checkpoint/challenge required? (manual intervention)
   - Permanent block? (account recovery needed)
2. Check recent publish frequency
   - Were too many stories published in short succession?
   - Did IP address change between attempts?
3. Check proxy config
   - Is the same IP being used consistently for this account?
   - Has the IP been flagged?

## Recovery Actions
### Temporary rate limit
- Pause all publish jobs for this client: 2-6 hours
- Resume with manual retry
- Reduce publish frequency temporarily

### Checkpoint/challenge required
- Log into Instagram account manually
- Complete challenge (email/phone verification)
- Re-authenticate session
- Update credentials in config
- Resume publish jobs

### IP flagged
- Rotate to a clean proxy IP for this client
- Ensure new IP is sticky (same IP for all requests for this account)
- Wait 1 hour before retrying

### Permanent block
- Contact Instagram support
- Pause all automated publishing for this client
- Notify client immediately
- Document incident

## Prevention
- Use sticky IPs per Instagram account (never rotate mid-session)
- Respect Instagram rate limits (max 100 actions/day per account)
- Publish stories at human-like intervals (not all at once)
- Keep session credentials fresh
