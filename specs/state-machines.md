# IAMOS State Machines

## 1. Content Item Lifecycle

### States
PENDING, GENERATION_QUEUED, DRAFT_READY, AWAITING_OPERATOR,
AWAITING_CLIENT, REVISION_REQUESTED, APPROVED, SCHEDULED,
PUBLISHING, PUBLISHED, FAILED, DEAD, ESCALATED

### Transitions
| From | Trigger | To | Guard |
|---|---|---|---|
| PENDING | calendar.approved | GENERATION_QUEUED | — |
| GENERATION_QUEUED | agent completes | DRAFT_READY | — |
| DRAFT_READY | approval requested | AWAITING_OPERATOR | — |
| AWAITING_OPERATOR | operator approves | AWAITING_CLIENT | approval_mode == 2 |
| AWAITING_OPERATOR | operator approves | APPROVED | approval_mode == 1 |
| AWAITING_OPERATOR | operator rejects | REVISION_REQUESTED | — |
| AWAITING_OPERATOR | timeout | ESCALATED | — |
| AWAITING_CLIENT | client approves | APPROVED | — |
| AWAITING_CLIENT | client rejects | REVISION_REQUESTED | — |
| AWAITING_CLIENT | timeout | ESCALATED | — |
| REVISION_REQUESTED | agent revises | DRAFT_READY | revision_count < max |
| REVISION_REQUESTED | agent revises | ESCALATED | revision_count >= max |
| APPROVED | schedule set | SCHEDULED | approval_mode in (1,2) |
| APPROVED | auto | SCHEDULED | approval_mode == 3 |
| SCHEDULED | time reached | PUBLISHING | — |
| PUBLISHING | success | PUBLISHED | — |
| PUBLISHING | failure | FAILED | — |
| FAILED | retry triggered | PUBLISHING | attempts < max_attempts |
| FAILED | max retries exceeded | DEAD | attempts >= max_attempts |
| DEAD | manual override | PUBLISHING | human triggered |

### Terminal States
- PUBLISHED (success)
- DEAD (failure, no more retries)

---

## 2. Calendar Lifecycle

### States
PENDING, DRAFT_READY, AWAITING_OPERATOR, AWAITING_CLIENT,
REVISION_REQUESTED, ACTIVE

### Transitions
| From | Trigger | To | Guard |
|---|---|---|---|
| PENDING | period begins | DRAFT_READY | strategy agent runs |
| DRAFT_READY | sent for review | AWAITING_OPERATOR | — |
| AWAITING_OPERATOR | operator approves | AWAITING_CLIENT | client_calendar_approval == true |
| AWAITING_OPERATOR | operator approves | ACTIVE | client_calendar_approval == false |
| AWAITING_OPERATOR | operator rejects | REVISION_REQUESTED | — |
| AWAITING_CLIENT | client approves | ACTIVE | — |
| AWAITING_CLIENT | client rejects | REVISION_REQUESTED | — |
| REVISION_REQUESTED | agent revises | DRAFT_READY | — |
| ACTIVE | new period begins | PENDING | — |

### Terminal States
- ACTIVE (success — rolls over each period)

---

## 3. Publish Job Lifecycle

### States
QUEUED, ATTEMPTING, DONE, FAILED, DEAD

### Transitions
| From | Trigger | To | Guard |
|---|---|---|---|
| QUEUED | scheduled time reached | ATTEMPTING | — |
| ATTEMPTING | success | DONE | — |
| ATTEMPTING | failure | FAILED | — |
| FAILED | retry | ATTEMPTING | attempts < max_attempts |
| FAILED | max retries | DEAD | attempts >= max_attempts |
| DEAD | manual override | ATTEMPTING | human triggered |

### Terminal States
- DONE (success)
- DEAD (failure)

---

## Rules
- State lives in Postgres, never in workers or memory.- Only the orchestrator may trigger state transitions.
- Every transition is logged as an append-only event.
- No domain may read another domain's state directly — only via events.
