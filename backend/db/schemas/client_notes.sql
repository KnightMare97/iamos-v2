-- Domain: Out-of-Band Client Communication & Human Scratchpad
CREATE TABLE client_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    operator_id UUID NOT NULL REFERENCES operators(id),
    note_text TEXT NOT NULL,
    channel VARCHAR(50) NOT NULL DEFAULT 'whatsapp'
        CHECK (channel IN ('whatsapp', 'phone', 'in_person', 'email', 'other')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_client_notes_retrieval ON client_notes(client_id, created_at DESC);
