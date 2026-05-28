# IAMOS Production Resilience & Anti-Failure Spec

## 1. Concurrency & Idempotency Layer
- **Aggregate Locking:** All mutations to `content_items` or `campaigns` must use optimistic concurrency locks. 
  `UPDATE content_items SET state = :next_state, version = version + 1 WHERE id = :id AND version = :expected_version;`
- **Conflict Handling:** If affected rows == 0, discard the message, emit an observability log, and raise a metrics alert `transition_conflict_detected`.
- **Inbound Deduplication:** Every worker consumer must evaluate an idempotency check against incoming `event_id` keys in Redis with a strict 24-hour TTL before executing core calculations.

## 2. Safe Event Transaction Sequence
- **Transactional Outbox Pattern:** To eliminate memory loss from unexpected microservice deaths, the event state MUST be written to Postgres FIRST before emitting an acknowledgment (`XACK`) to Redis Streams.

## 3. Recovery Paths for Deadlocks (Timeouts & Escalations)
- **State Machine Extension:** Explicitly support `ESCALATED -> AWAITING_OPERATOR` via human supervisor override endpoints.
- **Storm Prevention:** Rate limit batch alerts dispatched to operators. Max 5 telegram pings per human supervisor every 15 minutes. Pollers must flag `timeout_notified_at` to block infinite notification bursts.

## 4. Guardrails for Content Guard (AI Validation Filter)
- Every generated draft from Haiku/Sonnet must undergo automated linting before hitting the Approval Queue:
  1. Character length constraint check (Strictly <= 80 characters).
  2. Structural valid JSON layout evaluation.
  3. Prohibited terms blacklist scanning (Brand guidelines violation check).

## 5. Token Mitigation & Decay Tuning
- **Memory Context Slicing:** Cap vector contexts at a maximum of top-3 matching elements (Strict budget constraint <= 500 tokens).
- **Temporal Decaying:** Vector search queries must include dynamic weighting based on `created_at` or filter out records holding uninitialized performance signals (`engagement_score == 0.0`).

## 6. Client Lifecycle & Offboarding Operational Procedure
- **Atomic Offboarding Transaction:** The `POST /clients/{id}/offboard` endpoint must run the entire termination vector within a single isolated database transaction block:
  1. Set `clients.status = 'offboarded'` and log timestamps + reasons.
  2. Batch-update all `publish_jobs` in `('QUEUED', 'SCHEDULED', 'ATTEMPTING')` states directly to `'CANCELLED'`.
  3. Batch-update all `approval_requests` holding a state of `'PENDING'` directly to `'CANCELLED'`.
  4. Invalidate credentials by forcing `instagram_sessions.session_valid = false`.
  5. Commit transaction and emit the `client.offboarded` event payload to Redis Streams.

- **Stale Event Interception (Orchestrator Guard):**
  - Before any domain worker (Strategy, Content, Approvals, Publishing) triggers an LLM orchestration call or state transition, it MUST verify the client status state:
    `SELECT status FROM clients WHERE id = :client_id;`
  - If a client holds a status of `'offboarded'`, the orchestrator must instantly halt processing, emit an observability log under event type `system.stale_event`, and securely discard the message payload.
- **Paused Mode Handling:** If a client holds a status of `'paused'`, the scheduling loops within the strategy and content domains must hold and suspend automatic asset dispatching without executing a destructive wipe of pending queues.
