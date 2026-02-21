-- ─────────────────────────────────────────────────────────────────────────────
-- Briefer — initial schema
-- ─────────────────────────────────────────────────────────────────────────────

-- News sources (RSS feeds, Google News topics, custom scrapers)
CREATE TABLE IF NOT EXISTS sources (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255)    NOT NULL,
    type            VARCHAR(50)     NOT NULL,   -- rss | google_news | custom
    url             TEXT,
    category        VARCHAR(100)    NOT NULL,   -- geopolitics | technology | finance | science | health
    tier            INTEGER         NOT NULL DEFAULT 1,  -- 1=gov, 2=google_news, 3=analysis
    extractor       VARCHAR(50)     DEFAULT 'trafilatura',
    active          BOOLEAN         DEFAULT TRUE,
    fail_count      INTEGER         DEFAULT 0,
    last_fetched_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     DEFAULT NOW()
);

-- Raw scraped articles
CREATE TABLE IF NOT EXISTS articles (
    id                  SERIAL PRIMARY KEY,
    source_id           INTEGER         REFERENCES sources(id) ON DELETE SET NULL,
    title               TEXT            NOT NULL,
    url                 TEXT            NOT NULL,
    url_hash            VARCHAR(64)     NOT NULL UNIQUE,    -- SHA-256 of URL (fast dedup)
    title_hash          VARCHAR(64),                        -- SHA-256 of normalized title
    full_text           TEXT,
    meta_description    TEXT,
    author              TEXT,
    publish_date        TIMESTAMPTZ,
    image_urls          JSONB           DEFAULT '[]',
    keywords            JSONB           DEFAULT '[]',
    raw_metadata        JSONB           DEFAULT '{}',       -- source-specific extras
    extraction_method   VARCHAR(50),                        -- which extractor succeeded
    extraction_failed   BOOLEAN         DEFAULT FALSE,
    scraped_at          TIMESTAMPTZ     DEFAULT NOW(),
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_url_hash       ON articles(url_hash);
CREATE INDEX IF NOT EXISTS idx_articles_title_hash     ON articles(title_hash);
CREATE INDEX IF NOT EXISTS idx_articles_publish_date   ON articles(publish_date DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source_id      ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_scraped_at     ON articles(scraped_at DESC);

-- Claude's per-article processing output
CREATE TABLE IF NOT EXISTS article_summaries (
    id               SERIAL PRIMARY KEY,
    article_id       INTEGER         REFERENCES articles(id) ON DELETE CASCADE UNIQUE,
    summary          TEXT,
    headline         TEXT,           -- Claude-generated headline
    importance_score FLOAT,          -- 0.0 (trivial) → 1.0 (historic)
    category         VARCHAR(100),   -- Claude's categorization
    tags             JSONB           DEFAULT '[]',
    processed_at     TIMESTAMPTZ     DEFAULT NOW(),
    model_used       VARCHAR(100),
    failed           BOOLEAN         DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_summaries_importance ON article_summaries(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_category   ON article_summaries(category);

-- Daily briefing documents
CREATE TABLE IF NOT EXISTS daily_briefings (
    id                       SERIAL PRIMARY KEY,
    briefing_date            DATE            NOT NULL UNIQUE,
    meta_headline            TEXT,
    meta_story               TEXT,           -- the synthesized "meaning of the day"
    top_article_ids          JSONB           DEFAULT '[]',   -- ordered list of article IDs
    total_articles_scraped   INTEGER         DEFAULT 0,
    total_articles_processed INTEGER         DEFAULT 0,
    created_at               TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_briefings_date ON daily_briefings(briefing_date DESC);

-- Per-category summaries for each briefing
CREATE TABLE IF NOT EXISTS category_summaries (
    id           SERIAL PRIMARY KEY,
    briefing_id  INTEGER         REFERENCES daily_briefings(id) ON DELETE CASCADE,
    category     VARCHAR(100)    NOT NULL,
    headline     TEXT,
    summary      TEXT,
    article_ids  JSONB           DEFAULT '[]',
    created_at   TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cat_summaries_briefing ON category_summaries(briefing_id);

-- Audit log for each pipeline run
CREATE TABLE IF NOT EXISTS scrape_runs (
    id                   SERIAL PRIMARY KEY,
    started_at           TIMESTAMPTZ     DEFAULT NOW(),
    completed_at         TIMESTAMPTZ,
    articles_discovered  INTEGER         DEFAULT 0,
    articles_extracted   INTEGER         DEFAULT 0,
    articles_failed      INTEGER         DEFAULT 0,
    status               VARCHAR(50)     DEFAULT 'running',  -- running | completed | failed
    error_message        TEXT
);
