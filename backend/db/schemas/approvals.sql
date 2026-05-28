-- Domain: Approvals
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL CHECK (aggregate_type IN ('ContentItem', 'Campaign')),
    client_id UUID NOT NULL REFERENCES clients(id),
    approval_mode INTEGER NOT NULL CHECK (approval_mode IN (1, 2, 3)),
    operator_decision VARCHAR(20) CHECK (operator_decision IN ('approved', 'rejected')),
    operator_decided_at TIMESTAMPTZ,
    client_decision VARCHAR(20) CHECK (client_decision IN ('approved', 'rejected')),
    client_decided_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(aggregate_id, aggregate_type)
);

CREATE INDEX idx_approval_requests_client_id ON approval_requests(client_id);
CREATE INDEX idx_approval_requests_aggregate_id ON approval_requests(aggregate_id);
CREATE INDEX idx_approval_requests_state ON approval_requests(state);
CREATE INDEX idx_approval_requests_timeout_at ON approval_requests(timeout_at);
