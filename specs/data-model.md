# IAMOS Core Data Model

## Entities

### Client
Domain: clients

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| name | string | Client/business name |
| brand_voice | text | Tone and style instructions for AI |
| approval_mode | integer | 1=operator, 2=operator+client, 3=auto |
| client_calendar_approval | boolean | Whether client approves calendars |
| stories_per_day | integer | Configurable per client |
| active_days | array[integer] | e.g. [0,1,2,3,4,6] (0=Mon, 6=Sun) |
| timezone | string | e.g. Asia/Tehran |
| instagram_handle | string | Target account |
| telegram_chat_id | string | For approval notifications |
| created_at | timestamp | — |

### Campaign
Domain: strategy

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| client_id | UUID | FK → Client |
| period_start | date | Start of this calendar period |
| period_end | date | End of this calendar period |
| state | string | Calendar lifecycle state |
| brief | text | Strategic direction for this period |
| created_at | timestamp | — |

### ContentItem
Domain: content

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| client_id | UUID | FK → Client |
| campaign_id | UUID | FK → Campaign |
| state | string | Content lifecycle state |
| scheduled_at | timestamp | When to publish |
| caption | text | Story caption/text |
| revision_count | integer | Number of revision cycles |
| created_at | timestamp | — |

### Asset
Domain: content

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| client_id | UUID | FK → Client |
| content_item_id | UUID | FK → ContentItem |
| type | string | photo, video, ai_generated |
| source | string | client_upload, ai, shooting |
| url | string | Storage URL |
| created_at | timestamp | — |

### ApprovalRequest
Domain: approvals

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| aggregate_id | UUID | ContentItem or Campaign id |
| aggregate_type | string | ContentItem or Campaign |
| client_id | UUID | FK → Client |
| approval_mode | integer | Snapshot of mode at time of request |
| operator_decision | string | approved, rejected, null |
| operator_decided_at | timestamp | — |
| client_decision | string | approved, rejected, null |
| client_decided_at | timestamp | — |
| timeout_at | timestamp | Deadline for response |
| state | string | Approval lifecycle state |
| feedback | text | Rejection reason if any |

### PublishJob
Domain: publishing

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| content_item_id | UUID | FK → ContentItem |
| client_id | UUID | FK → Client |
| scheduled_at | timestamp | When to attempt |
| attempts | integer | Number of attempts made |
| last_error | text | Last failure reason |
| state | string | Publish job lifecycle state |

### MemoryRecord
Domain: memory

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| client_id | UUID | FK → Client |
| content_item_id | UUID | FK → ContentItem |
| engagement_score | float | Performance metric |
| tags | array[string] | Content type tags |
| embedding | vector | pgvector embedding for similarity |
| created_at | timestamp | — |

### AgentCall
Domain: observability

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| client_id | UUID | FK → Client |
| aggregate_id | UUID | What this call was for |
| agent_type | string | strategy, content, revision |
| prompt_version | string | FK → PromptTemplate version |
| model | string | e.g. claude-sonnet-4-20250514 |
| input_tokens | integer | — |
| output_tokens | integer | — |
| cost_usd | float | Calculated cost |
| duration_ms | integer | — |
| state | string | success, failed |
| created_at | timestamp | — |

### PromptTemplate
Domain: prompts

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| agent_type | string | Which agent uses this |
| version | string | Semantic version e.g. 1.0.0 |
| content | text | The prompt text |
| active | boolean | Only one active per agent_type |
| created_at | timestamp | — |

### Event (append-only log)
Domain: observability

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| event_type | string | e.g. content.draft.ready |
| aggregate_id | UUID | — |
| aggregate_type | string | — |
| client_id | UUID | — |
| timestamp | timestamp | — |
| version | integer | Schema version |
| payload | JSONB | Event-specific data |
| triggered_by | string | human:{id} or agent:{type} |

### ShootingRequest
Domain: clients

| Field | Type | Purpose |
|---|---|---|
| id | UUID | Primary key |
| client_id | UUID | FK → Client |
| requested_at | timestamp | — |
| status | string | pending, scheduled, completed, cancelled |
| notes | text | Client instructions |

## Constraints
- client_id is present on every entity — this is how client isolation is enforced
- Event table is never updated or deleted from
- Only one PromptTemplate may be active per agent_type at any time
- revision_count must not exceed system max (default: 3) without human escalation
