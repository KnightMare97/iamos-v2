-- Migration: Legacy Telegram Chat IDs to Multi-Operator Domain
BEGIN;

-- 1. Create unique operators from existing client telegram_chat_ids
INSERT INTO operators (name, telegram_chat_id, status)
SELECT DISTINCT 
    'Operator ' || telegram_chat_id as name, 
    telegram_chat_id, 
    'active'
FROM clients 
WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id != ''
ON CONFLICT (telegram_chat_id) DO NOTHING;

-- 2. Link them as Primary Operators for those clients
INSERT INTO client_operators (client_id, operator_id, role)
SELECT c.id, o.id, 'primary'
FROM clients c
JOIN operators o ON c.telegram_chat_id = o.telegram_chat_id
ON CONFLICT DO NOTHING;

COMMIT;
