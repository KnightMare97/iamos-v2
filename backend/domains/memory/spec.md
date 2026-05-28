# Domain: Memory

## Responsibility
Stores performance history and content patterns per client. Provides context to strategy and content agents to improve over time.

## Owns
- MemoryRecord

## Emits
- memory.updated

## Consumes
- publish.succeeded
- publish.failed

## External Dependencies
- pgvector (Postgres extension)

## API Endpoints
GET    /clients/{id}/memory           — list memory records for client
GET    /clients/{id}/memory/similar   — find similar past content (vector search)

## Memory Accumulation Flow
1. Receive publish.succeeded or publish.failed
2. Create MemoryRecord with outcome data
3. Generate embedding from content caption + tags
4. Store embedding in pgvector
5. Emit memory.updated

## Query Interface
- Strategy agent queries: "what has worked for this client before?"
- Content agent queries: "find similar past stories for reference"
- Both use vector similarity search on embeddings
- Results filtered strictly by client_id

## Business Rules
- MemoryRecords are never deleted (append-only)
- Embeddings are generated using the same model consistently — changing embedding model requires re-indexing
- client_id filter is mandatory on every query — no cross-client reads
- engagement_score is set to 0.0 initially (no Instagram analytics yet) and updated when analytics integration is added

## Notes
- Engagement scoring is a stub for Phase 1
- Full analytics integration is a future module
