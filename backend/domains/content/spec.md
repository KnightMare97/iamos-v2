# Domain: Content Production

## Responsibility
Generates story drafts for each content item in an approved calendar. Handles asset management (client uploads, AI-generated, shooting assets).

## Owns
- ContentItem
- Asset

## Emits
- content.draft.ready
- asset.uploaded

## Consumes
- calendar.approved
- approval.rejected
- client.updated

## External Dependencies
- Claude API (content agent)
- Image generation API (future — stubbed for now)
- File storage (local volume initially, S3-compatible later)
- PromptTemplate (via prompts domain)

## API Endpoints
GET    /content-items/{id}            — get content item detail
GET    /campaigns/{id}/content-items  — list items for campaign
POST   /content-items/{id}/assets     — upload asset
DELETE /content-items/{id}/assets/{asset_id} — remove asset

## Agent: Content Agent
- Input: campaign brief, story slot date/index, brand voice, memory records, existing assets if any
- Output: caption text + asset instructions (or generated asset)
- Prompt template: agent_type = "content"
- Must not exceed 1000 output tokens per item
- All calls logged to AgentCall

## Asset Sources
- client_upload: human uploads via API or Telegram
- ai_generated: content agent produces (text initially, image future)
- shooting: manually added by operator after shooting session

## Business Rules
- One ContentItem per story slot per day per client
- ContentItem is created when calendar.approved is received
- revision_count increments on each approval.rejected
- Max revision_count: 3 — escalate to human after
- Asset must exist before ContentItem can move to APPROVED state
- client_id on every Asset — no cross-client asset access ever

## Notes
- Agent proposes captions and asset instructions
- Orchestrator creates/updates ContentItem records
- Content agent never writes to DB directly
