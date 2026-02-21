import os
from datetime import datetime, date

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    Boolean, DateTime, Date, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func

Base = declarative_base()


def get_engine():
    url = os.environ["DATABASE_URL"]
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


# ─────────────────────────────────────────────────────────────────────────────

class Source(Base):
    __tablename__ = "sources"

    id              = Column(Integer, primary_key=True)
    name            = Column(String(255), nullable=False)
    type            = Column(String(50),  nullable=False)   # rss | google_news | custom
    url             = Column(Text)
    category        = Column(String(100), nullable=False)
    tier            = Column(Integer, default=1)
    extractor       = Column(String(50),  default="trafilatura")
    active          = Column(Boolean,     default=True)
    fail_count      = Column(Integer,     default=0)
    last_fetched_at = Column(TIMESTAMPTZ)
    created_at      = Column(TIMESTAMPTZ, server_default=func.now())

    articles = relationship("Article", back_populates="source")

    def __repr__(self):
        return f"<Source {self.name!r} ({self.category})>"


class Article(Base):
    __tablename__ = "articles"

    id                 = Column(Integer, primary_key=True)
    source_id          = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"))
    title              = Column(Text,        nullable=False)
    url                = Column(Text,        nullable=False)
    url_hash           = Column(String(64),  nullable=False, unique=True)
    title_hash         = Column(String(64))
    full_text          = Column(Text)
    meta_description   = Column(Text)
    author             = Column(Text)
    publish_date       = Column(TIMESTAMPTZ)
    image_urls         = Column(JSONB,  default=list)
    keywords           = Column(JSONB,  default=list)
    raw_metadata       = Column(JSONB,  default=dict)
    extraction_method  = Column(String(50))
    extraction_failed  = Column(Boolean, default=False)
    scraped_at         = Column(TIMESTAMPTZ, server_default=func.now())
    created_at         = Column(TIMESTAMPTZ, server_default=func.now())

    source  = relationship("Source",         back_populates="articles")
    summary = relationship("ArticleSummary", back_populates="article", uselist=False)

    def __repr__(self):
        return f"<Article {self.title[:60]!r}>"


class ArticleSummary(Base):
    __tablename__ = "article_summaries"

    id               = Column(Integer, primary_key=True)
    article_id       = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), unique=True)
    summary          = Column(Text)
    headline         = Column(Text)
    importance_score = Column(Float)
    category         = Column(String(100))
    tags             = Column(JSONB, default=list)
    processed_at     = Column(TIMESTAMPTZ, server_default=func.now())
    model_used       = Column(String(100))
    failed           = Column(Boolean, default=False)

    article = relationship("Article", back_populates="summary")

    def __repr__(self):
        return f"<ArticleSummary article_id={self.article_id} score={self.importance_score}>"


class DailyBriefing(Base):
    __tablename__ = "daily_briefings"

    id                       = Column(Integer, primary_key=True)
    briefing_date            = Column(Date, nullable=False, unique=True)
    meta_headline            = Column(Text)
    meta_story               = Column(Text)
    top_article_ids          = Column(JSONB, default=list)
    total_articles_scraped   = Column(Integer, default=0)
    total_articles_processed = Column(Integer, default=0)
    created_at               = Column(TIMESTAMPTZ, server_default=func.now())

    category_summaries = relationship("CategorySummary", back_populates="briefing")

    def __repr__(self):
        return f"<DailyBriefing {self.briefing_date}>"


class CategorySummary(Base):
    __tablename__ = "category_summaries"

    id          = Column(Integer, primary_key=True)
    briefing_id = Column(Integer, ForeignKey("daily_briefings.id", ondelete="CASCADE"))
    category    = Column(String(100), nullable=False)
    headline    = Column(Text)
    summary     = Column(Text)
    article_ids = Column(JSONB, default=list)
    created_at  = Column(TIMESTAMPTZ, server_default=func.now())

    briefing = relationship("DailyBriefing", back_populates="category_summaries")

    def __repr__(self):
        return f"<CategorySummary {self.category} briefing_id={self.briefing_id}>"


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id                   = Column(Integer, primary_key=True)
    started_at           = Column(TIMESTAMPTZ, server_default=func.now())
    completed_at         = Column(TIMESTAMPTZ)
    articles_discovered  = Column(Integer, default=0)
    articles_extracted   = Column(Integer, default=0)
    articles_failed      = Column(Integer, default=0)
    status               = Column(String(50), default="running")  # running | completed | failed
    error_message        = Column(Text)

    def __repr__(self):
        return f"<ScrapeRun {self.id} {self.status}>"
