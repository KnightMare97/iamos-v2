# Runbook: Approval Timeout

## Trigger
ApprovalRequest reaches timeout_at without a decision. approval.timeout event emitted.

## Symptoms
- Content stuck in AWAITING_OPERATOR or AWAITING_CLIENT
- approval.timeout event in event log
- Operator receives timeout alert via Telegram

## Diagnosis Steps
1. Check ApprovalRequest record
   - Which stage timed out (operator or client)?
   - When was the request sent?
   - Was the Telegram notification delivered?
2. Check Telegram bot status
   - Is the bot running?
   - Was the chat_id reachable?

## Recovery Actions
### If operator missed the notification
- Resend approval request: POST /approvals/{id}/resend
- Operator reviews and decides via Telegram or admin panel

### If client is unresponsive (mode 2)
- Escalate to operator to decide on behalf of client
- Document decision in ApprovalRequest notes
- Manually advance approval

### If Telegram bot was down
- Restart Telegram bot service
- Resend pending approval notifications
- Review all approvals that timed out in the window

### If content deadline is at risk
- Operator can approve directly via admin panel
- Adjust scheduled_at on ContentItem if needed

## Prevention
- Set realistic timeout windows per client (default 24hrs)- Ensure operator Telegram notifications are not muted
- Add escalation alert at 75% of timeout window
