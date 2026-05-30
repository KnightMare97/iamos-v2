-- IAMOS Comprehensive Database Schema Initialization - v2.0.0
-- Ensures multi-tenancy isolation, dynamic AI configurations, and granular state tracking.

BEGIN;

-- ۱. جدول اصلی کلاینت‌ها (تنظیمات برند و مسیرهای پویا هوش مصنوعی)
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    industry_vertical VARCHAR(100),
    target_audience TEXT,
    brand_voice TEXT NOT NULL,
    ui_language VARCHAR(10) DEFAULT 'fa',
    brand_font VARCHAR(50) DEFAULT 'Vazirmatn',
    brand_color VARCHAR(20) DEFAULT '#ffffff',
    brand_logo_url TEXT,
    anti_repetition_days INTEGER DEFAULT 7,
    preferred_provider VARCHAR(30) DEFAULT 'google',
    fallback_provider VARCHAR(30) DEFAULT 'openrouter',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'offboarded')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۲. جدول یادداشت‌های سوپروایزر و CONTENT TEAM LEAD
CREATE TABLE IF NOT EXISTS client_notes (
    id BIGSERIAL PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۳. جدول پیکربندی منبع تامین دارایی‌ها (هوش مصنوعی یا عکاسی انسانی)
CREATE TABLE IF NOT EXISTS client_content_type_config (
    client_id UUID PRIMARY KEY REFERENCES clients(id) ON DELETE CASCADE,
    asset_source VARCHAR(30) DEFAULT 'raw_upload' CHECK (asset_source IN ('raw_upload', 'ai_generated')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۴. جدول کمپین‌ها و استراتژی‌های کلان تقویم
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    state VARCHAR(30) DEFAULT 'PENDING',
    month_context TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۵. جدول قالب‌های لایوت لایه مونتاژ (Assembly Layer)
CREATE TABLE IF NOT EXISTS story_layouts (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    css_styles TEXT NOT NULL,
    html_template TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- تزریق لایوت‌های پیش‌فرض فارسی
INSERT INTO story_layouts (id, name, css_styles, html_template) VALUES
('minimal_quote', 'نقل قول مینیمال', 'direction: rtl; color: #ffffff; text-align: right;', '<div class="quote-box">{{caption}}</div>'),
('product_feature', 'معرفی محصول باکس شیشه‌ای', 'direction: rtl; background: rgba(0,0,0,0.4);', '<div class="glass-card">{{caption}}</div>')
ON CONFLICT (id) DO NOTHING;

-- ۶. جدول اسلات‌های محتوایی استوری‌ها (Granular Slot Architecture)
CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    layout_template_id VARCHAR(50) REFERENCES story_layouts(id),
    state VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    caption TEXT,
    approved_caption TEXT,
    visual_direction TEXT,
    hashtags TEXT[],
    ai_prompt_anti_context TEXT,
    campaign_override BOOLEAN DEFAULT FALSE,
    revision_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    scheduled_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۷. جدول دارایی‌های بصری (Assets)
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    content_item_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
    type VARCHAR(30) NOT NULL,
    source VARCHAR(30) NOT NULL,
    url TEXT NOT NULL,
    ai_description TEXT,
    vision_qa_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۸. سپر نظارت بینایی ماشین (Vision QA Logs)
CREATE TABLE IF NOT EXISTS asset_quality_checks (
    id BIGSERIAL PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    matches_visual_direction BOOLEAN NOT NULL,
    contains_no_text BOOLEAN NOT NULL,
    is_appropriate BOOLEAN NOT NULL,
    looks_professional BOOLEAN NOT NULL,
    passed_qa BOOLEAN NOT NULL,
    raw_ai_feedback TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۹. درخواست عکاسی انسانی (Human Fallback Channel)
CREATE TABLE IF NOT EXISTS shooting_requests (
    id BIGSERIAL PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ۱۰. کارهای انتشار نهایی اسلات‌ها (Publish Jobs)
CREATE TABLE IF NOT EXISTS publish_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    content_item_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    state VARCHAR(30) DEFAULT 'QUEUED',
    delivery_channel VARCHAR(30) DEFAULT 'TELEGRAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ساخت ایندکس‌های کارایی بالا برای کوئری‌های چندمستاجری (Multi-Tenancy Performance)
CREATE INDEX IF NOT EXISTS idx_content_items_client_schedule ON content_items(client_id, scheduled_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_content_item ON assets(content_item_id);

COMMIT;
