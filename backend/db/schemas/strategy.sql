-- Domain: Strategy
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    brief TEXT,
    revision_count INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,                             -- Concurrency Guard
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(client_id, period_start)
);

CREATE INDEX idx_campaigns_client_id ON campaigns(client_id);
CREATE INDEX idx_campaigns_state ON campaigns(state);
