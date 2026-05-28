# Domain: Client Management

## Responsibility
Owns all client configuration. Single source of truth for who a client is, how their approval workflow runs, and what their content schedule looks like.

## Owns
- Client
- ShootingRequest

## Emits
- client.onboarded
- client.updated
- shooting.requested

## Consumes
- nothing

## External Dependencies
- none

## API Endpoints
POST   /clients              — create client
GET    /clients              — list all clients
GET    /clients/{id}         — get client detail
PATCH  /clients/{id}         — update client config
POST   /clients/{id}/shooting-requests — request a shooting

## Business Rules
- approval_mode must be 1, 2, or 3
- stories_per_day and active_days are configurable per client and can be changed by admin or strategy agent
- brand_voice is a free-text field used verbatim in AI prompts
- telegram_chat_id is required for approval_mode 1 or 2
- client_calendar_approval defaults to false

## Notes
- This domain has no AI agents
- All mutations emit a corresponding event
