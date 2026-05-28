-- Domain: Content Production
CREATE TABLE content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID REFERENCES campaigns(id),                      -- Can be null for one-off/regular slots
    campaign_request_id UUID REFERENCES campaign_requests(id) ON DELETE SET NULL, -- Link to urgent request flow
    campaign_override BOOLEAN NOT NULL DEFAULT FALSE,                -- True if injected via urgent flow
    state VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    scheduled_at TIMESTAMPTZ,
    caption TEXT,
    visual_direction TEXT,
    hashtags TEXT[],
    revision_count INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    content_item_id UUID REFERENCES content_items(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('photo', 'video', 'ai_generated')),
    source VARCHAR(50) NOT NULL CHECK (source IN ('client_upload', 'ai', 'shooting')),
    url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_content_items_client_id ON content_items(client_id);
CREATE INDEX idx_content_items_override ON content_items(campaign_override) WHERE campaign_override = TRUE;
CREATE INDEX idx_assets_content_item_id ON assets(content_item_id);
