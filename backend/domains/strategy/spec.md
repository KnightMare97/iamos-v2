# Domain: Strategy

## Responsibility
Generates content calendars and campaign briefs for each client. Decides what stories to create, when, and with what direction.

## Owns
- Campaign

## Emits
- calendar.draft.ready
- campaign.created

## Consumes
- client.onboarded
- client.updated
- calendar.revision.requested
- memory.updated

## External Dependencies
- Claude API (strategy agent)
- PromptTemplate (via prompts domain)

## API Endpoints
POST   /campaigns                     — manually trigger campaign creation
GET    /campaigns/{id}                — get campaign detail
GET    /clients/{id}/campaigns        — list campaigns for client
PATCH  /campaigns/{id}/brief          — update campaign brief

## Agent: Strategy Agent
- Input: client profile, brand voice, memory records, period dates
- Output: structured campaign brief + daily story thread plan
- Prompt template: agent_type = "strategy"
- Must not exceed 2000 output tokens
- All calls logged to AgentCall

## Business Rules
- One active Campaign per client per period
- Campaign period is monthly by default, weekly detail layer on top
- Calendar generation is triggered automatically when a period begins
- Revision is triggered by calendar.revision.requested event
- Max revisions before human escalation: 2

## Notes
- Agent proposes. Orchestrator decides. Strategy agent never writes to Campaign directly — it returns output to the orchestrator which creates/updates the Campaign record.
