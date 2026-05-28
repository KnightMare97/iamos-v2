# IAMOS Orchestrator & Multi-Layer Anti-Failure System Specification

## 1. Core Error Domain Boundaries
All sub-system operations (Strategy, Content, Approvals, Publishing, Memory, Reporting) must handle transient and fatal conditions without leaking raw thread state to the orchestrator layer.

## 2. Multi-Provider AI Routing Failover Architecture
- Every LLM execution request must pass through the `AIRouter` component.
- **Circuit Breaker Mechanics:** If a provider hits 3 sequential timeouts (504) or rate-limit rejections (429), its status in the `CircuitBreakerRegistry` trips to open for 15 minutes. 
- All traffic drops dynamically to the defined fallback queue order: `[anthropic -> openai -> google -> xai]`.

## 3. Daily Story Capacity Overrides
- The scheduling logic must cross-check the `daily_story_overrides` table before invoking any strategy generation loops.
- If a target date holds a specific record override for a client, the default `stories_per_day` configuration column is ignored, and the system scales slots allocation precisely to match the override parameter.

## 4. Reporting Domain Metrics Separation
- **Phase 1 Execution (Always Online):** Telemetry relies purely on system transactional logs (`stories_scheduled`, `stories_published`, `stories_failed`, `stories_revised`, `avg_approval_hours`).
- **Phase 2 Execution (Instagram Connected):** Quantitative analytics (`avg_views`, `avg_reply_rate`, `avg_exit_rate`) are allowed to return null if the token state remains unlinked. 

## 5. Atomic Client Offboarding Execution Chain
- Offboarding operations must wrap under an explicit database transaction block.
- Upon dispatch of `POST /clients/{id}/offboard`:
  1. Atomically switch `clients.status = 'offboarded'` and write `offboarded_at`.
  2. Locate all matching `publish_jobs` in a non-terminal status (`QUEUED`, `ATTEMPTING`) and force transition to `CANCELLED`.
  3. Locate all matching `approval_requests` where `state = 'PENDING'` and force transition to `CANCELLED`.
  4. Flush any matching active event schedules from the worker stream queues.
  5. Emit the global broadcast event stream message: `client.offboarded`.

## 6. Missed Publish Detection & Operator Override Interventions
- **Scheduled Detector Job (Every 30 Minutes):**
  - The `missed_publish_detector` worker runs an explicit boundary query to capture lost or stuck scheduling records:
    ```sql
    SELECT pj.* FROM publish_jobs pj
    JOIN clients c ON pj.client_id = c.id
    WHERE pj.state = 'SCHEDULED'
      AND pj.scheduled_at < NOW() - INTERVAL '2 hours'
      AND pj.missed_alert_sent = FALSE
      AND c.status = 'active';
    ```
  - For each returned row, the worker executes in atomic isolation:
    1. Emit the `publish.missed` event payload containing the target `job_id`.
    2. Dispatch an urgent Telegram Alert payload to the operator channel.
    3. Update `missed_alert_sent = TRUE` to lock the notification loop.
- **Orchestration State Rules (State Invariance):**
  - Arrival of a `publish.missed` event MUST NOT mutate the state of the job. It remains strictly `SCHEDULED`.
- **Operator Manual Resolutions:**
  - `POST /publish-jobs/{id}/confirm-manual`: Atomically transitions the target job state from `SCHEDULED` to `DONE`.
  - `POST /publish-jobs/{id}/cancel`: Atomically forces the job state directly to the terminal `CANCELLED` status.

## 7. Operator Vacation, Leave Substitution, and Bulk Resolution
- **Operator Resolution Cascade Algorithm:**
  - Upon dispatching any validation block, the approval pipeline computes the active target:
    1. Query `client_operators` for the client's `role = 'primary'`.
    2. If the primary operator's status is `'active'`, route to their `telegram_chat_id`.
    3. If the status is `'on_leave'`, query `role = 'backup'` for that client. If active, route to them.
    4. If backup is missing, escalate the notification block to the Shared Master Group Chat ID.
    5. Write the final computed identifier to `approval_requests.resolved_operator_id`.
- **Bulk Decision Safety Constraints:**
  - The `POST /approvals/bulk-decide` gateway endpoint enforces strict limits:
    1. Hard Allocation Cap: Reject requests updating greater than 20 elements at once.
    2. Explicit Consent Invariant: The body payload MUST hold a boolean key `confirm: true`.

## 8. Content Preview Rendering Contract & Phased Telegram Implementation
- **Contract Architecture (`GET /content-items/{id}/preview`):**
  - Pure server-side rendered (SSR) endpoint returning an isolated, self-contained HTML/CSS 9:16 aspect ratio absolute canvas.
- **Phased Implementation Execution Guide:**
  - **Phase 1 (Current Active Mode):** The Telegram approval dispatch worker skips rendering images. It aggregates the structured records and sends a cleanly formatted markdown text payload.
  - **Phase 2 (Future Enhancement):** The approval workflow worker triggers an automated headless render of the preview URL to capture a PNG image buffer.

## 9. Prompt Optimization Feedback Loop & Theme Analysis
- **Automatic Logging Invariant:**
  - Every interception of an `approval.rejected` event that holds non-empty human operator text feedback generates a record into `rejection_patterns`.
- **Weekly Analysis Cron (Monday Morning Core Pipeline):**
  - **The Signal Threshold Rule:** The worker evaluates the result array length. If `len(patterns) < 3`, abort processing for that specific client to prevent shallow hallucinated themes.
  - **Safety System Boundary (Anti-AutoMutation):** The architecture prohibits the platform from updating code prompt files automatically. All suggestions function as advisory pointers.

## 10. Agency Shared Calendar Gateways & Exclusion Constraints
- **Endpoint Contracts:**
  - `GET /agency-calendar`: Fetches global time-sorted view of upcoming holidays.
  - `POST /clients/{id}/calendar-exclusions/{event_id}`: Inserts an exclusion row to block specific event contexts.
- **Race Condition Guard:** State mutations on calendar exclusions during an active strategy run (`state = 'GENERATING'`) are blocked at the gateway layer.

## 11. Visual UI Module Toggles & Runbook Automation Control
- **Dynamic Module Guard Invariant:**
  - Before any automated worker processes an event stream message, the system validates the client's configuration: `modules_enabled->>:domain_key AS is_enabled`. If false, halt execution immediately and log under `system.ui_toggle_suppressed`.

## 12. Advanced Strategy Editing (Flow A) & Urgent Campaign Injection (Flow B)
- **Flow A: Micro-Targeted Calendar Save Restrictions:**
  - When the administrator commits changes to a monthly grid, the backend isolates only the mutation keys. Slots marked untouched remain locked in their current state database vector.
- **Flow B: Urgent Campaign Ingestion Pipeline Execution:**
  - **Step 1 (Asset Vision Logging):** Assets trigger a Tier 2 Vision pipeline writing to `campaign_request_assets.ai_description`.
  - **Step 2 (Priority Injection Boundary):** System inserts records directly into `content_items` setting `campaign_override = TRUE`. These rows immediately hijack regular slots.
  - **Step 3 (Hard Fact Invariant Prompting):** The values inside `campaign_requests.structured_data` are injected as absolute literals.
  - **Step 4 (Expedited Timeout & Group Chat Escalation Routing):** Arrival of an `'emergency'` campaign request drops the validation timeout window directly down to **2 hours**.
  - **Step 5 (Visual Safety Validation Guard):** Content items require a valid asset link inside `campaign_request_assets.assigned_to_content_item_id` before passing state transition validation to `APPROVED`.

## 13. Automated Image Generation Pipeline & Visual QA Constraints
- If a content slot resolves to an asset source of `'ai_generated'`, the orchestrator invokes a Tier 3 `image_prompt_generation` task.
- **Machine Vision QA Shielding:** The orchestrator halts the state flow and invokes a Tier 2 `image_qa_vision` call asserting: `matches_visual_direction`, `contains_no_text`, `is_appropriate`, and `looks_professional`. Any fail triggers a regeneration loop capped at a strict maximum of **2 attempts**.
- **Iterative Feedback Capping:** Operator manual rejections with textual prompt adjustments trigger up to **2 iterations** before throwing a hard exception and issuing a physical `shooting` request notification.
