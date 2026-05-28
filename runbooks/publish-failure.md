# Runbook: Publish Failure

## Trigger
PublishJob reaches state DEAD (max retries exceeded) or operator receives publish.failed alert.

## Symptoms
- Story not published at scheduled time
- PublishJob.state = FAILED or DEAD
- publish.failed event in event log

## Diagnosis Steps
1. Check PublishJob record
   - How many attempts were made?
   - What is last_error?
   - What was scheduled_at?
2. Check proxy layer
   - Is the proxy for this client's Instagram account reachable?
   - Test proxy connection manually
3. Check Instagram account status
   - Is the account temporarily blocked or rate-limited?
   - Has the session/cookie expired?
4. Check system logs
   - Any network timeouts?
   - Any authentication errors from Instagram API?

## Recovery Actions
### If proxy is down
- Switch client to backup proxy config
- Manually trigger retry: POST /publish-jobs/{id}/retry
- Monitor next attempt

### If Instagram session expired
- Re-authenticate Instagram account
- Update session credentials in config
- Manually trigger retry: POST /publish-jobs/{id}/retry

### If content is the issue (rejected by Instagram)
- Review content for policy violations
- Edit ContentItem caption or asset
- Reset PublishJob state to QUEUED manually
- Monitor next scheduled attempt

### If DEAD and time-sensitive
- Publish manually from Instagram app
- Mark PublishJob as manually_resolved in notes
- File issue to investigate root cause

## Prevention
- Monitor proxy health daily
- Rotate Instagram sessions proactively every 30 days
- Keep max_attempts at 5 with backoff to avoid rate limiting
