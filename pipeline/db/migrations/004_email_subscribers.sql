-- 004_email_subscribers.sql
-- Self-built email subscriber table for briefer.news daily email delivery.
-- Lifecycle: pending → confirmed → (optionally) unsubscribed or bounced.
-- Applied 2026-05-26 via docker exec briefer_postgres psql.

CREATE TABLE IF NOT EXISTS email_subscribers (
    id                      BIGSERIAL PRIMARY KEY,
    email                   TEXT NOT NULL UNIQUE,
    status                  TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'confirmed', 'unsubscribed', 'bounced')),
    confirmation_token      TEXT,                -- random token for double-opt-in URL
    confirmed_at            TIMESTAMPTZ,
    unsubscribed_at         TIMESTAMPTZ,
    unsubscribe_token       TEXT NOT NULL,       -- signed token for one-click unsubscribe URL
    edition_preference      TEXT DEFAULT 'both'
                            CHECK (edition_preference IN ('us', 'china', 'both')),
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS email_subscribers_status_idx ON email_subscribers(status);
CREATE INDEX IF NOT EXISTS email_subscribers_unsub_token_idx ON email_subscribers(unsubscribe_token);

CREATE OR REPLACE FUNCTION email_subscribers_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS email_subscribers_touch ON email_subscribers;
CREATE TRIGGER email_subscribers_touch
    BEFORE UPDATE ON email_subscribers
    FOR EACH ROW EXECUTE FUNCTION email_subscribers_touch_updated_at();
