# IAMOS Event Catalog

## Event Envelope
Every event in the system must conform to this structure:

| Field | Type | Purpose |
|---|---|---|
| event_id | UUID | Unique identifier |
| event_type | string | e.g. content.draft.ready |
| aggregate_id | UUID | The entity this event is about |
| aggregate_type | string | e.g. ContentItem, Campaign |
| client_id | UUID | Always present — enforces client isolation |
| timestamp | ISO8601 | When it happened |
| version | integer | For schema evolution |
| payload | JSON | Event-specific data |
| triggered_by | string | human:{user_id} or agent:{agent_type} |

## Event Catalog
| Event | Emitted By | Consumed By | Meaning |
|---|---|---|---|
| client.onboarded | clients | strategy, memory | New client set up and ready |
| client.updated | clients | strategy, content | Brand voice or preferences changed |
| calendar.draft.ready | strategy | approvals | Monthly/weekly calendar ready for review |
| calendar.approved | approvals | content | Calendar greenlit, content generation begins |
| calendar.revision.requested | approvals | strategy | Calendar sent back for changes |
| content.draft.ready | content | approvals | Story draft ready for review |
| content.approved | approvals | publishing | Content cleared for publishing |
| approval.rejected | approvals | content | Draft sent back with feedback |
| approval.timeout | approvals | orchestrator | No response within deadline |
| asset.uploaded | content | content | Human uploaded photo/video asset |
| publish.scheduled | publishing | observability | Job queued for specific time |
| publish.succeeded | publishing | memory, observability | Story went live |
| publish.failed | publishing | orchestrator, observability | Publish attempt failed |
| publish.retrying | publishing | observability | Retry in progress |
| memory.updated | memory | strategy, content | New performance data stored |
| shooting.requested | clients | observability | Client requested a shooting session |

## Rules
- Events are append-only. Never update or delete an event.
- Every event must include client_id even if the aggregate is not client-scoped.
- Event type format: {domain}.{entity}.{past_tense_verb}
- Consumers must be idempotent — receiving the same event twice must not cause side effects.
