# Domain: Observability

## Responsibility
Consumes all system events. Logs every action, agent call, and failure. Provides the audit trail and cost tracking.

## Owns
- Event (append-only log)
- AgentCall

## Emits
- nothing

## Consumes
- everything

## External Dependencies
- none

## API Endpoints
GET    /events                        — query event log (filterable)
GET    /events/{aggregate_id}         — all events for an entity
GET    /agent-calls                   — list agent calls (filterable by client)
GET    /agent-calls/costs             — cost summary by client/period
GET    /health                        — system health check

## Business Rules
- Event table is strictly append-only — no updates, no deletes
- Every domain is responsible for emitting events — observability only stores them
- AgentCall is written by the orchestrator after every AI call completes
- Cost calculation: input_tokens * model_input_rate + output_tokens * model_output_rate (rates stored in config)

## Notes
- This domain is the system's black box recorder
- In Phase 1, querying is basic (filter by client, date, event_type)
- Dashboards and alerting are a future addition
