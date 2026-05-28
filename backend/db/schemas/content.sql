-- Domain: Content Production
CREATE TABLE content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    state VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    scheduled_at TIMESTAMPTZ,
    caption TEXT,
    revision_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    content_item_id UUID NOT NULL REFERENCES content_items(id),
    type VARCHAR(50) NOT NULL CHECK (type IN ('photo', 'video', 'ai_generated')),
    source VARCHAR(50) NOT NULL CHECK (source IN ('client_upload', 'ai', 'shooting')),
    url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_content_items_client_id ON content_items(client_id);
CREATE INDEX idx_content_items_campaign_id ON content_items(campaign_id);
CREATE INDEX idx_content_items_state ON content_items(state);
CREATE INDEX idx_content_items_scheduled_at ON content_items(scheduled_at);
CREATE INDEX idx_assets_client_id ON assets(client_id);
CREATE INDEX idx_assets_content_item_id ON assets(content_item_id);
