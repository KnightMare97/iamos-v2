-- Domain: AI Vision Quality Assurance (QA) Engine
CREATE TABLE asset_quality_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    content_item_id UUID REFERENCES content_items(id) ON DELETE SET NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    matches_visual_direction BOOLEAN NOT NULL DEFAULT FALSE,
    contains_no_text BOOLEAN NOT NULL DEFAULT FALSE,
    is_appropriate BOOLEAN NOT NULL DEFAULT FALSE,
    looks_professional BOOLEAN NOT NULL DEFAULT FALSE,
    passed_qa BOOLEAN NOT NULL DEFAULT FALSE,                        -- TRUE only if all 4 parameters pass
    raw_ai_feedback TEXT,                                            -- Stored text from Haiku/GPT-4o-mini
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_asset_qa_lookup ON asset_quality_checks(asset_id, passed_qa);
