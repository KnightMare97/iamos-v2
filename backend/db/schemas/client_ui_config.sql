-- Domain: Admin UI & Module Management Configuration
ALTER TABLE clients ADD COLUMN IF NOT EXISTS modules_enabled JSONB NOT NULL DEFAULT '{
  "strategy": true,
  "content": true,
  "approvals": true,
  "publishing": true,
  "memory": true,
  "reporting": true
}'::jsonb;

-- Index for high-performance extraction of active modules across orchestrator loops
CREATE INDEX IF NOT EXISTS idx_clients_modules_jsonb ON clients USING gin (modules_enabled);
