-- Domain: Memory
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    content_item_id UUID NOT NULL REFERENCES content_items(id),
    engagement_score FLOAT NOT NULL DEFAULT 0.0,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_records_client_id ON memory_records(client_id);
CREATE INDEX idx_memory_records_content_item_id ON memory_records(content_item_id);
CREATE INDEX idx_memory_records_embedding ON memory_records    USING ivfflat (embedding vector_cosine_ops)    WITH (lists = 100);
