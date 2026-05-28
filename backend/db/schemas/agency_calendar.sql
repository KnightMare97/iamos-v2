-- Domain: Shared Agency Intelligence & Cultural Calendars
CREATE TABLE agency_calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL 
        CHECK (event_type IN ('holiday', 'seasonal', 'cultural', 'campaign')),
    region VARCHAR(50) NOT NULL DEFAULT 'IR',                       -- Region support (e.g., IR, AU, Global)
    content_guidance TEXT,                                           -- Direct context injection for LLM
    applies_to_all BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE client_calendar_exclusions (
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES agency_calendar_events(id) ON DELETE CASCADE,
    PRIMARY KEY (client_id, event_id)
);

CREATE INDEX idx_agency_calendar_date ON agency_calendar_events(event_date, region);
