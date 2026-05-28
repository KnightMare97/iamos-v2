-- Domain: Publishing
CREATE TABLE publish_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_item_id UUID NOT NULL REFERENCES content_items(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    state VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(content_item_id)
);

CREATE INDEX idx_publish_jobs_client_id ON publish_jobs(client_id);
CREATE INDEX idx_publish_jobs_state ON publish_jobs(state);
CREATE INDEX idx_publish_jobs_scheduled_at ON publish_jobs(scheduled_at);
