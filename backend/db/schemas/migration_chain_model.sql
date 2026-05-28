-- Migration: Update agent_calls for Chain Model Redesign
ALTER TABLE agent_calls ADD COLUMN IF NOT EXISTS tier INTEGER CHECK (tier IN (1, 2, 3));
ALTER TABLE agent_calls ADD COLUMN IF NOT EXISTS confidence_score FLOAT;
ALTER TABLE agent_calls ADD COLUMN IF NOT EXISTS escalation_reason TEXT;
ALTER TABLE agent_calls ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'anthropic';
CREATE INDEX IF NOT EXISTS idx_agent_calls_tier ON agent_calls(tier);
