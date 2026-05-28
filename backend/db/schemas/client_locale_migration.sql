-- Migration: Add UI and Content Generation Locale Support
ALTER TABLE clients ADD COLUMN IF NOT EXISTS ui_language VARCHAR(5) NOT NULL DEFAULT 'fa'
    CHECK (ui_language IN ('fa', 'en'));
