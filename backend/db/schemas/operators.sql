-- Domain: Operator Management & Vacation Routing
CREATE TABLE operators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    telegram_chat_id VARCHAR(255) NOT NULL UNIQUE,
    telegram_username VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'on_leave', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE client_operators (
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    operator_id UUID NOT NULL REFERENCES operators(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('primary', 'backup')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (client_id, operator_id)
);

CREATE INDEX idx_client_operators_lookup ON client_operators(client_id, role);
CREATE INDEX idx_operators_status ON operators(status);
