# Domain: Prompt Management

## Responsibility
Stores, versions, and serves prompt templates to AI agents. Ensures every AI call uses a known, versioned prompt.

## Owns
- PromptTemplate

## Emits
- nothing

## Consumes
- nothing

## External Dependencies
- none

## API Endpoints
GET    /prompts                       — list all templates
GET    /prompts/{agent_type}/active   — get active template for agent
POST   /prompts                       — create new template version
PATCH  /prompts/{id}/activate         — set as active for agent_type

## Business Rules
- Only one PromptTemplate may be active per agent_type at any time
- Activating a new version automatically deactivates the previous one
- Templates are never deleted — only deactivated
- agent_type values: strategy, content, revision
- Version format: semantic (1.0.0, 1.1.0, etc.)
- AgentCall always records the prompt version used

## Prompt Template Variables
Each template uses these interpolation variables:
- {brand_voice} — from Client
- {campaign_brief} — from Campaign
- {memory_context} — from Memory query results
- {story_slot} — date and index of this story slot
- {feedback} — rejection feedback (revision agent only)
- {existing_caption} — current draft (revision agent only)

## Notes
- Prompt files also exist as markdown in /prompts/templates/
- DB is the source of truth at runtime
- File templates are for version control and review
