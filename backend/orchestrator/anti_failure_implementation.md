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

## 11. Agency Shared Calendar Gateways & Exclusion Constraints
- **Endpoint Contracts:**
  - `GET /agency-calendar`: Fetches a global time-sorted view of upcoming system-wide holidays and campaigns.
  - `POST /agency-calendar`: Creates an agency-wide event. Requires explicit structural validations on `event_type` and `region`.
  - `POST /clients/{id}/calendar-exclusions/{event_id}`: Inserts a unique row into `client_calendar_exclusions` to block the selected event context from mutating the target client's future strategy generations.
  - `DELETE /clients/{id}/calendar-exclusions/{event_id}`: Drops the exclusion link, re-enabling cultural context inclusion for subsequent cron cycles.
- **Race Condition Guard:** State mutations on calendar exclusions during an active strategy run (`state = 'GENERATING'`) must be blocked at the HTTP gateway layer to prevent corrupted prompt interpolation states.

## 12. Visual UI Module Toggles & Runbook Automation Control
- **Dynamic Module Guard Invariant:**
  - Before any automated worker processes a transaction hook or an event stream message for a given domain, the system must validate the specific client's runtime configuration:
    ```sql
    SELECT modules_enabled->>:domain_key AS is_enabled 
    FROM clients 
    WHERE id = :client_id;
    ```
  - If the extracted value returns `false` (string or boolean), the worker must halt execution immediately, drop the processing frame gracefully, and log the intervention under an observability code of `system.ui_toggle_suppressed`.
  - **Exception Rule:** Critical operational runbook shortcuts (`POST /publish-jobs/{id}/confirm-manual`, manual proxy rotations, or hard column overrides) bypass the module checking layer to ensure the administrator always maintains override authority.

## 13. Advanced Strategy Editing (Flow A) & Urgent Campaign Injection (Flow B)
- **Flow A: Micro-Targeted Calendar Save Restrictions:**
  - When the administrator commits changes to a monthly grid via the workspace, the backend MUST NOT pass modifications back to an LLM loop for voice translation or alignment.
  - The orchestrator isolates only the mutation keys (modified, inserted, or removed rows). Slots marked untouched remain locked in their current state database vector. Only newly inserted or structurally rewritten slots re-enter the `PENDING` queue loop.

- **Flow B: Urgent Campaign Ingestion Pipeline Execution:**
  - **Step 1 (Asset Vision Logging):** Incoming binary assets trigger a Tier 2 Vision pipeline execution under `task_type="campaign_asset_vision"`. The resulting structured text output is permanently written to `campaign_request_assets.ai_description`.
  - **Step 2 (Priority Injection Boundary):** The system calculates required slots (`duration_days * clients.stories_per_day`) and inserts records directly into `content_items` setting `campaign_override = TRUE`. These rows immediately hijack and override regular thematic slots for those calendar coordinate hours.
  - **Step 3 (Hard Fact Invariant Prompting):** Content generation workers mapping `campaign_override = TRUE` slots are prohibited from inferring marketing statistics. The values inside `campaign_requests.structured_data` (e.g., specific coupon text, numeric discount rates) are injected as absolute literals into the model parameter boundaries.
  - **Step 4 (Expedited Timeout & Group Chat Escalation Routing):**
    - Arrival of an `urgency = 'emergency'` campaign request bypasses standard message throttling and triggers an instant Telegram webhook dispatch to the assigned operator.
    - If `go_live_at` sits within a 24-hour window from the execution frame, the approval payload is prefixed with `🔴 URGENT`.
    - The `timeout_at` boundary constraint for validation requests linked to a `campaign_request_id` drops from the standard 24-hour system window directly down to **2 hours**. If unacted upon within 2 hours, it triggers immediate fallback alerts.
  - **Step 5 (Visual Safety Validation Guard):** The frontend workspace provides a manual mapping matrix for assets. Before any `campaign_override = TRUE` content item can pass state transition validation to `APPROVED`, the orchestrator asserts that a matching foreign key exists inside `campaign_request_assets.assigned_to_content_item_id`. Any unmapped slots throw a hard block constraint.

## 14. Automated Image Generation Pipeline & Visual QA Constraints
- **The 5-Step AI Generation Lifecycle Invariant:**
  - **Step 1: Expanded Prompt Crafting:** If a content slot resolves to an asset source of `'ai_generated'`, the orchestrator invokes a Tier 3 `image_prompt_generation` task. It expands the brief into a structured metadata output: `prompt_string`, `negative_prompt`, `aspect_ratio: "9:16"`, and `style_descriptors`.
  - **Step 2: Isolated API Execution:** The system dispatches the prompt payload to the client's preferred provider (DALL-E 3, Stable Diffusion, or Ideogram) and saves the returned binary URL instantly inside the `assets` matrix.
  - **Step 3: Machine Vision QA Shielding:** The orchestrator halts the state flow and invokes a Tier 2 `image_qa_vision` call. The vision engine explicitly asserts four boolean flags: `matches_visual_direction`, `contains_no_text`, `is_appropriate`, and `looks_professional`. 
    - **Circuit Breaker Check:** If any flag evaluates to `FALSE`, the transaction writes the error logs to `asset_quality_checks` and triggers an automated loop regeneration. This automated self-healing loop is capped at a strict maximum of **2 attempts**.
  - **Step 4: Forced Human-in-the-Loop Interception:** The system is strictly prohibited from auto-publishing any record derived from an AI visual asset. It forces insertion into the `approval_requests` queue, forwarding the binary rendering along with the caption to the operator Telegram node.
  - **Step 5: Iterative Feedback Expansion Loop:** If the human operator clicks `REJECT` and appends instructional prompt feedback, the orchestrator updates `asset_quality_checks`, concatenates the text string directly to the `prompt_string` boundary block, and fires the regeneration loop. If the operator rejection cycle hits **2 iterations**, the system triggers a hard failure exception, drops the AI flow, and issues an urgent `shooting` request notification.

- **Phase 3 Video Generation Invariant:**
  - Video asset types (`video_reel`, `video_boomerang`) and high-end video provider actions are architecture-ready but structurally locked. During data initialization, all video categories inside `client_content_type_config` must hold an explicit value of `enabled = FALSE` until separate engine activation work is committed.

## 14. Automated Image Generation Pipeline & Visual QA Constraints
- **The 5-Step AI Generation Lifecycle Invariant:**
  - **Step 1: Expanded Prompt Crafting:** If a content slot resolves to an asset source of `'ai_generated'`, the orchestrator invokes a Tier 3 `image_prompt_generation` task. It expands the brief into a structured metadata output: `prompt_string`, `negative_prompt`, `aspect_ratio: "9:16"`, and `style_descriptors`.
  - **Step 2: Isolated API Execution:** The system dispatches the prompt payload to the client's preferred provider (DALL-E 3, Stable Diffusion, or Ideogram) and saves the returned binary URL instantly inside the `assets` matrix.
  - **Step 3: Machine Vision QA Shielding:** The orchestrator halts the state flow and invokes a Tier 2 `image_qa_vision` call. The vision engine explicitly asserts four boolean flags: `matches_visual_direction`, `contains_no_text`, `is_appropriate`, and `looks_professional`. 
    - **Circuit Breaker Check:** If any flag evaluates to `FALSE`, the transaction writes the error logs to `asset_quality_checks` and triggers an automated loop regeneration. This automated self-healing loop is capped at a strict maximum of **2 attempts**.
  - **Step 4: Forced Human-in-the-Loop Interception:** The system is strictly prohibited from auto-publishing any record derived from an AI visual asset. It forces insertion into the `approval_requests` queue, forwarding the binary rendering along with the caption to the operator Telegram node.
  - **Step 5: Iterative Feedback Expansion Loop:** If the human operator clicks `REJECT` and appends instructional prompt feedback, the orchestrator updates `asset_quality_checks`, concatenates the text string directly to the `prompt_string` boundary block, and fires the regeneration loop. If the operator rejection cycle hits **2 iterations**, the system triggers a hard failure exception, drops the AI flow, and issues an urgent `shooting` request notification.

- **Phase 3 Video Generation Invariant:**
  - Video asset types (`video_reel`, `video_boomerang`) and high-end video provider actions are architecture-ready but structurally locked. During data initialization, all video categories inside `client_content_type_config` must hold an explicit value of `enabled = FALSE` until separate engine activation work is committed.
