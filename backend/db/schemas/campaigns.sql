-- Domain: Campaigns & Urgent Content Injections
CREATE TABLE campaign_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    operator_id UUID REFERENCES operators(id),
    type VARCHAR(50) NOT NULL
        CHECK (type IN ('sale', 'new_product', 'event', 'collaboration', 'announcement')),
    go_live_at TIMESTAMPTZ NOT NULL,
    duration_days INTEGER NOT NULL DEFAULT 1,
    structured_data JSONB NOT NULL DEFAULT '{}'::jsonb,              -- High-signal structured facts (discounts, codes)
    notes TEXT,
    urgency VARCHAR(20) NOT NULL DEFAULT 'normal'
        CHECK (urgency IN ('normal', 'urgent', 'emergency')),
    state VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending', 'slots_created', 'generating', 'awaiting_approval', 'active', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE campaign_request_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_request_id UUID NOT NULL REFERENCES campaign_requests(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    ai_description TEXT,                                             -- Tier 2 Vision description output
    assigned_to_content_item_id UUID,                                -- Linked via UI drag-and-drop or generator mapping
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_campaign_requests_client_state ON campaign_requests(client_id, state);
CREATE INDEX idx_campaign_request_assets_lookup ON campaign_request_assets(campaign_request_id);

-- Add late constraint to safely link back to content items after content schema load
ALTER TABLE campaign_request_assets 
ADD CONSTRAINT fk_assigned_content_item 
FOREIGN KEY (assigned_to_content_item_id) REFERENCES content_items(id) ON DELETE SET NULL;
