# Domain: Publishing

## Responsibility
Schedules and executes publishing of approved content to Instagram. Handles retries, proxy routing, and failure recovery.

## Owns
- PublishJob

## Emits
- publish.scheduled
- publish.succeeded
- publish.failed
- publish.retrying

## Consumes
- content.approved

## External Dependencies
- Instagram API (via instagrapi or similar)
- Proxy/VPN layer (required for Iran)

## API Endpoints
GET    /publish-jobs/{id}             — get job status
GET    /clients/{id}/publish-jobs     — list jobs for client
POST   /publish-jobs/{id}/retry       — manual retry trigger

## Publish Flow
1. Receive content.approved event
2. Create PublishJob with state QUEUED
3. At scheduled_at, move to ATTEMPTING
4. Route request through proxy layer
5. Attempt Instagram publish
6. On success: emit publish.succeeded, state → DONE
7. On failure: increment attempts, emit publish.failed
8. If attempts < max: schedule retry with backoff, emit publish.retrying
9. If attempts >= max: state → DEAD, alert operator

## Retry Strategy
- Max attempts: 5
- Backoff: 5min, 15min, 30min, 1hr, 2hr
- Each retry is a new attempt on the same PublishJob

## Proxy Layer
- All Instagram requests routed through configurable proxy
- Proxy config is per-client (different accounts may need different IPs)
- If proxy fails: log error, do not attempt direct connection

## Idempotency
- Every publish action has an idempotency key = PublishJob.id
- Duplicate publish attempts for same job are detected and skipped

## Business Rules
- PublishJob is created only after content.approved
- scheduled_at comes from ContentItem.scheduled_at
- Publishing never modifies ContentItem state directly — emits events which orchestrator acts on
- Dead jobs require manual operator intervention to retry

## Publish Modes
- **Mode 1 (manual):** The system prepares the content package and sends it to the operator via Telegram with all associated assets and captions. The operator handles publishing manually on the app and confirms execution via Telegram. The system then transitions the job state to `DONE`. No Instagram proxy credentials or active sessions are required for this profile mode.
