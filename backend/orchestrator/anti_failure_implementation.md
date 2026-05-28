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

## 7. Missed Publish Detection & Operator Override Interventions
- **Scheduled Detector Job (Every 30 Minutes):**
  - The `missed_publish_detector` worker must run an explicit boundary query to capture lost or stuck scheduling records:
    ```sql
    SELECT pj.* FROM publish_jobs pj
    JOIN clients c ON pj.client_id = c.id
    WHERE pj.state = 'SCHEDULED'
      AND pj.scheduled_at < NOW() - INTERVAL '2 hours'
      AND pj.missed_alert_sent = FALSE
      AND c.status = 'active';
    ```
  - For each returned row, the worker must execute in an atomic isolation:
    1. Emit the `publish.missed` event payload containing the target `job_id` and metadata.
    2. Dispatch an urgent Telegram Alert payload to the operator channel with the contextual Job ID.
    3. Update `missed_alert_sent = TRUE` to lock the notification loop.

- **Orchestration State Rules (State Invariance):**
  - Arrival of a `publish.missed` event MUST NOT mutate the `state` of the `publish_jobs` table. The job remains strictly in `SCHEDULED` status to maintain historical tracking and block ghost re-fires.
  
- **Operator Manual Resolutions:**
  - `POST /publish-jobs/{id}/confirm-manual`: Atomically transitions the target job state from `SCHEDULED` to `DONE` with an optimistic lock guard (`version = version + 1`), confirming the operator resolved the slot physically on Instagram.
  - `POST /publish-jobs/{id}/cancel`: Atomically forces the job state directly to the terminal `CANCELLED` status, safely liquidating the missed slot from the active pipeline.

## 8. Operator Vacation, Leave Substitution, and Bulk Resolution
- **Operator Resolution Cascade Algorithm:**
  - Upon dispatching any Telegram validation block, the approval pipeline MUST compute the active router target:
    1. Query the `client_operators` table for the client's `role = 'primary'`.
    2. If the primary operator's status state is `'active'`, route to their `telegram_chat_id`.
    3. If the status is `'on_leave'`, query `role = 'backup'` for that client. If active, route to them.
    4. If backup is missing, inactive, or on leave, escalate the notification block to the Shared Master Group Chat ID.
    5. Write the final computed identifier to `approval_requests.resolved_operator_id`.

- **Bulk Decision Safety Constraints:**
  - The `POST /approvals/bulk-decide` gateway endpoint must enforce strict throttling bounds to prevent destructive batch updates:
    1. **Hard Allocation Cap:** Reject requests updating greater than 20 elements at once.
    2. **Explicit Consent Invariant:** The body payload MUST hold a boolean key `confirm: true`. If absent or false, drop the transaction instantly.
    3. **State Mutability:** Transitions must iterate through an optimistic lock verification before changing states to `'APPROVED'` or `'REJECTED'`.

## 9. Content Preview Rendering Contract & Phased Telegram Implementation
- **Contract Architecture (`GET /content-items/{id}/preview`):**
  - This route must be a zero-LLM, pure server-side rendered (SSR) endpoint returning an isolated, self-contained HTML/CSS block.
  - **Data Injection:** The endpoint queries `content_items` (`caption`, `hashtags`, `visual_direction`) and joins `clients` (`brand_color`, `brand_font`) to assemble a 9:16 aspect ratio absolute CSS mock frame resembling an Instagram Story canvas.

- **Phased Implementation Execution Guide:**
  - **Phase 1 (Current Active Mode):** - The Telegram approval dispatch worker skips rendering images. It aggregates the structured database records and sends a cleanly formatted markdown text payload to the operator:
      ```text
      📱 *NEW CONTENT ITEM PENDING APPROVAL*
      ------------------------------------
      📝 **Caption:** {caption}
      🏷️ **Hashtags:** {hashtags}
      🎨 **Visual Direction:** {visual_direction}
      ```
  - **Phase 2 (Future Enhancement):** - The approval workflow worker will trigger an automated headless render of the `/preview` URL, capture the layout buffer as a PNG image, and issue a `sendPhoto` call alongside the interactive approval inline buttons to the operator.

## 10. Prompt Optimization Feedback Loop & Theme Analysis
- **Automatic Logging Invariant:**
  - Every interception of an `approval.rejected` event that holds non-empty human operator text feedback MUST generate a record into `rejection_patterns` with the active `week_start` timestamp date.

- **Weekly Analysis Cron (Monday Morning Core Pipeline):**
  - Alongside report processing, the `prompt_review_analyzer` triggers a grouped aggregation scanning for raw items:
    ```sql
    SELECT feedback_text, id FROM rejection_patterns
    WHERE client_id = :client_id
      AND week_start = :last_week_date
      AND agent_type = 'content';
    ```
  - **The Signal Threshold Rule:** The worker must evaluate the result array length. If `len(patterns) < 3`, abort processing for that specific client to prevent hallucinating themes out of shallow/random noise data.
  - **LLM Structured Contract:** If the threshold matches, call Tier 2 (Haiku) with `task_type="prompt_review_analyzer"`. The model prompt requires a strict JSON Schema return constraint:
    ```json
    { "theme": "string", "suggested_change": "string", "confidence": 0.85 }
    ```
  - **Operator Notification & Escalation Bounds:** If `confidence > 0.7` and `theme` is non-null:
    1. Update all targeted `rejection_patterns` for that batch setting `flagged_for_review = TRUE`.
    2. Append the formatted object directly into the target `weekly_reports.prompt_improvement_suggestions` block.
    3. Issue a specialized warning summary line into the weekly Operator Telegram dispatch channel.
  - **Safety System Boundary (Anti-AutoMutation):** The architecture prohibits the platform from updating code prompt files automatically. All suggestions function as advisory pointers requiring operator review via the admin panel endpoints.

## 10. Prompt Optimization Feedback Loop & Theme Analysis
- **Automatic Logging Invariant:**
  - Every interception of an `approval.rejected` event that holds non-empty human operator text feedback MUST generate a record into `rejection_patterns` with the active `week_start` timestamp date.

- **Weekly Analysis Cron (Monday Morning Core Pipeline):**
  - Alongside report processing, the `prompt_review_analyzer` triggers a grouped aggregation scanning for raw items:
    ```sql
    SELECT feedback_text, id FROM rejection_patterns
    WHERE client_id = :client_id
      AND week_start = :last_week_date
      AND agent_type = 'content';
    ```
  - **The Signal Threshold Rule:** The worker must evaluate the result array length. If `len(patterns) < 3`, abort processing for that specific client to prevent hallucinating themes out of shallow/random noise data.
  - **LLM Structured Contract:** If the threshold matches, call Tier 2 (Haiku) with `task_type="prompt_review_analyzer"`. The model prompt requires a strict JSON Schema return constraint:
    ```json
    { "theme": "string", "suggested_change": "string", "confidence": 0.85 }
    ```
  - **Operator Notification & Escalation Bounds:** If `confidence > 0.7` and `theme` is non-null:
    1. Update all targeted `rejection_patterns` for that batch setting `flagged_for_review = TRUE`.
    2. Append the formatted object directly into the target `weekly_reports.prompt_improvement_suggestions` block.
    3. Issue a specialized warning summary line into the weekly Operator Telegram dispatch channel.
  - **Safety System Boundary (Anti-AutoMutation):** The architecture prohibits the platform from updating code prompt files automatically. All suggestions function as advisory pointers requiring operator review via the admin panel endpoints.
