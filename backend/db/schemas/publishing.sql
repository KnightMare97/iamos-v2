-- Domain: Publishing
CREATE TABLE publish_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    content_item_id UUID NOT NULL UNIQUE,
    scheduled_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_attempt_at TIMESTAMPTZ,
    error_message TEXT,
    state VARCHAR(50) NOT NULL DEFAULT 'QUEUED'
        CHECK (state IN ('QUEUED', 'ATTEMPTING', 'DONE', 'FAILED', 'DEAD', 'CANCELLED')),
    missed_alert_sent BOOLEAN NOT NULL DEFAULT FALSE,                -- New: Torrent Notification Shield
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_publish_jobs_client_id ON publish_jobs(client_id);
CREATE INDEX idx_publish_jobs_state_scheduled ON publish_jobs(state, scheduled_at);
CREATE INDEX idx_publish_jobs_missed_detector ON publish_jobs(state, scheduled_at, missed_alert_sent);
