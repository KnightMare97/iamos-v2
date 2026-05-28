-- Domain: Content Type Configuration & Asset Sourcing Guards
CREATE TABLE client_content_type_config (
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL
        CHECK (content_type IN (
            'photo_product',
            'photo_lifestyle', 
            'video_reel',
            'video_boomerang',
            'text_graphic',
            'quote_graphic',
            'ai_generated_background',
            'ai_generated_illustration',
            'client_upload_required'
        )),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    asset_source VARCHAR(30) NOT NULL DEFAULT 'client_upload'
        CHECK (asset_source IN ('client_upload', 'ai_generated', 'shooting', 'any')),
    PRIMARY KEY (client_id, content_type)
);

CREATE INDEX idx_client_content_type_sourcing ON client_content_type_config(client_id, content_type, enabled);
