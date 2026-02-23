-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 003 — Processing pipeline schema additions
--
-- Adds:
--   1. rejected_url_hashes  — permanent record of articles the Groq filter rejected
--   2. briefing_outputs     — multi-variant output table (replaces single meta_story)
--   3. filtered_out column  — on articles table, marks pre-filter-era junk
--   4. articles_filtered    — new counter on scrape_runs
--   5. subcategory, entities, time_sensitivity on article_summaries
-- ─────────────────────────────────────────────────────────────────────────────

-- Permanent record of rejected stubs (Groq filter decisions)
-- Kept forever — small table, important for audit and filter tuning
CREATE TABLE IF NOT EXISTS rejected_url_hashes (
    url_hash    VARCHAR(64)  PRIMARY KEY,
    title       TEXT,
    reason      TEXT,        -- Groq's one-line reason (audit trail for filter tuning)
    source_name TEXT,        -- which source this came from
    rejected_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rejected_rejected_at ON rejected_url_hashes(rejected_at DESC);

-- Multi-variant briefing output table (replaces monolithic daily_briefings.meta_story)
CREATE TABLE IF NOT EXISTS briefing_outputs (
    id          SERIAL PRIMARY KEY,
    briefing_id INTEGER      REFERENCES daily_briefings(id) ON DELETE CASCADE,
    output_type VARCHAR(50)  NOT NULL,   -- 'meta_story' | 'category' | 'topic_brief' | 'deep_dive'
    category    VARCHAR(100),            -- NULL for global meta_story; category name otherwise
    topic       VARCHAR(200),            -- for topic_briefs only
    headline    TEXT,
    body        TEXT,
    word_count  INTEGER,
    article_ids JSONB        DEFAULT '[]',   -- source articles that fed this output
    model_used  VARCHAR(100),
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outputs_briefing      ON briefing_outputs(briefing_id);
CREATE INDEX IF NOT EXISTS idx_outputs_type_category ON briefing_outputs(output_type, category);

-- New columns on existing tables
ALTER TABLE articles ADD COLUMN IF NOT EXISTS filtered_out BOOLEAN DEFAULT FALSE;

ALTER TABLE scrape_runs ADD COLUMN IF NOT EXISTS articles_filtered INTEGER DEFAULT 0;

-- Richer article_summaries schema (adds subcategory, entities, time_sensitivity)
ALTER TABLE article_summaries ADD COLUMN IF NOT EXISTS subcategory     VARCHAR(100);
ALTER TABLE article_summaries ADD COLUMN IF NOT EXISTS entities        JSONB DEFAULT '[]';
ALTER TABLE article_summaries ADD COLUMN IF NOT EXISTS time_sensitivity VARCHAR(20);  -- breaking | developing | background

CREATE INDEX IF NOT EXISTS idx_summaries_subcategory ON article_summaries(subcategory);
CREATE INDEX IF NOT EXISTS idx_summaries_time        ON article_summaries(time_sensitivity);
