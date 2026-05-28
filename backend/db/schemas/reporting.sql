-- Domain: Reporting & Business Intelligence
CREATE TABLE weekly_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    
    -- Phase 1 Metrics (Always Available)
    stories_scheduled INTEGER NOT NULL DEFAULT 0,
    stories_published INTEGER NOT NULL DEFAULT 0,
    stories_failed INTEGER NOT NULL DEFAULT 0,
    stories_missed INTEGER NOT NULL DEFAULT 0,                       -- New: Tracked via publish.missed
    stories_revised INTEGER NOT NULL DEFAULT 0,
    avg_approval_hours FLOAT,
    ai_cost_usd FLOAT NOT NULL DEFAULT 0.0,
    tier2_calls INTEGER NOT NULL DEFAULT 0,
    tier3_calls INTEGER NOT NULL DEFAULT 0,
    
    -- Derived Signals (The Smart Metrics)
    revision_rate_trend_percentage FLOAT,
    operator_workload_score VARCHAR(20),
    tier3_escalation_rate FLOAT,
    
    -- Phase 2+ Metrics (Nullable until Instagram Graph API Connection)
    avg_views FLOAT,
    avg_reply_rate FLOAT,
    avg_exit_rate FLOAT,
    top_content_type VARCHAR(50),
    
    -- AI Generated Narrative
    narrative_summary TEXT,
    
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(client_id, week_start)
);

CREATE TABLE story_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    content_item_id UUID NOT NULL REFERENCES content_items(id),
    published_at TIMESTAMPTZ,
    views INTEGER,
    replies INTEGER,
    exits INTEGER,
    shares INTEGER,
    engagement_score FLOAT,
    instagram_fetched_at TIMESTAMPTZ,
    UNIQUE(content_item_id)
);

CREATE INDEX idx_weekly_reports_client_date ON weekly_reports(client_id, week_start);
CREATE INDEX idx_story_performance_client ON story_performance(client_id);
