-- Domain: Prompt Management
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_type, version)
);

CREATE INDEX idx_prompt_templates_agent_type ON prompt_templates(agent_type);
CREATE INDEX idx_prompt_templates_active ON prompt_templates(active);
