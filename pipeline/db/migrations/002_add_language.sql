-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 002 — add language column to articles
-- Supports multilingual scraping (Chinese, Russian, Arabic, etc.)
-- Language is stored as ISO 639-1 code: en, zh, ru, ar, ja, ko, de, fr, etc.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE articles ADD COLUMN IF NOT EXISTS language VARCHAR(10);

CREATE INDEX IF NOT EXISTS idx_articles_language ON articles(language);
