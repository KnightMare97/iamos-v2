-- Domain: LLMOps & Prompt Optimization Loop
CREATE TABLE rejection_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,                                 -- 'content' or 'strategy'
    feedback_text TEXT NOT NULL,
    week_start DATE NOT NULL,
    content_item_id UUID REFERENCES content_items(id) ON DELETE SET NULL,
    flagged_for_review BOOLEAN NOT NULL DEFAULT FALSE,               -- Set to TRUE if AI discovers a structural theme
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rejection_patterns_analysis ON rejection_patterns(client_id, week_start, agent_type);
