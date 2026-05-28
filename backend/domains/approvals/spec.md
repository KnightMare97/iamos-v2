# Domain: Approvals

## Responsibility
Manages all human approval workflows. Sends notifications via Telegram, receives decisions, enforces timeouts, routes based on approval_mode.

## Owns
- ApprovalRequest

## Emits
- approval.requested
- content.approved
- approval.rejected
- calendar.approved
- calendar.revision.requested
- approval.timeout

## Consumes
- content.draft.ready
- calendar.draft.ready

## External Dependencies
- Telegram Bot API

## API Endpoints
POST   /approvals/{id}/decide         — operator or client submits decision
GET    /approvals/{id}                — get approval request detail
GET    /clients/{id}/approvals        — list approvals for client

## Approval Modes
- Mode 1: operator approves only  Flow: content.draft.ready → notify operator → decision → emit result
- Mode 2: operator first, then client  Flow: content.draft.ready → notify operator → operator approves → notify client → client decision → emit result
- Mode 3: auto-publish (future)  Flow: content.draft.ready → emit content.approved immediately

## Telegram Bot Behavior
- On approval request: send preview of content + Approve/Reject buttons
- On rejection: prompt for feedback text
- On timeout: emit approval.timeout, notify operator
- Messages must include client name and scheduled date for context

## Business Rules
- Timeout window: 24 hours by default (configurable per client)
- Approval mode is snapshotted at request creation time
- One ApprovalRequest per ContentItem or Campaign — no duplicates
- Feedback text is required on rejection
- Both operator and client decisions are timestamped

## Notes
- Telegram is the only approval channel for now
- Web-based approval (client portal) is a future addition
- Approval domain does not know about content structure — it only knows aggregate_id and aggregate_type
