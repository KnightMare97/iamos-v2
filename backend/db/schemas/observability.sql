-- Domain: Observability
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    client_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1,
    payload JSONB NOT NULL DEFAULT '{}',
    triggered_by VARCHAR(255) NOT NULL
);

-- append-only: no updates, no deletes ever
CREATE INDEX idx_events_client_id ON events(client_id);
CREATE INDEX idx_events_aggregate_id ON events(aggregate_id);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp);

CREATE TABLE agent_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL,
    aggregate_id UUID,
    agent_type VARCHAR(50) NOT NULL,
    prompt_version VARCHAR(20),
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd FLOAT NOT NULL DEFAULT 0.0,
    duration_ms INTEGER,
    state VARCHAR(20) NOT NULL CHECK (state IN ('success', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_calls_client_id ON agent_calls(client_id);
CREATE INDEX idx_agent_calls_agent_type ON agent_calls(agent_type);
CREATE INDEX idx_agent_calls_created_at ON agent_calls(created_at);
