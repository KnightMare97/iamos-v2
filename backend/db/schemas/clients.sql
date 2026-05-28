-- Domain: Client Management
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    brand_voice TEXT,
    approval_mode INTEGER NOT NULL DEFAULT 1 CHECK (approval_mode IN (1, 2, 3)),
    publish_mode INTEGER NOT NULL DEFAULT 1 CHECK (publish_mode IN (1, 2, 3)),
    client_calendar_approval BOOLEAN NOT NULL DEFAULT FALSE,
    stories_per_day INTEGER NOT NULL DEFAULT 5,
    active_days INTEGER[] NOT NULL DEFAULT '{0,1,2,3,4,5}'::INTEGER[],
    timezone VARCHAR(100) NOT NULL DEFAULT 'Asia/Tehran',
    instagram_handle VARCHAR(255),
    telegram_chat_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE instagram_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) UNIQUE,
    username VARCHAR(255) NOT NULL,
    encrypted_password TEXT NOT NULL,
    session_file TEXT,
    proxy_url TEXT,                                                  -- Primary Proxy
    proxy_url_backup TEXT,                                           -- Iran Connectivity Guard
    last_login_at TIMESTAMPTZ,
    session_valid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE daily_story_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    date DATE NOT NULL,
    stories_count INTEGER NOT NULL CHECK (stories_count >= 0),
    created_by VARCHAR(255) NOT NULL,                                -- Operator ID or System
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(client_id, date)
);

CREATE TABLE shooting_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'scheduled', 'completed', 'cancelled')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_shooting_requests_client_id ON shooting_requests(client_id);
CREATE INDEX idx_daily_story_overrides_client_date ON daily_story_overrides(client_id, date);
