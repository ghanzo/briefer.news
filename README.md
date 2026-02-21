# briefer.news

A daily global intelligence briefing. Synthesizes world events — US government, Chinese state
media, tech, finance, science — into meaning.

## Architecture

```
RSS / Google News → Scraper → PostgreSQL → Claude (per-article) → Claude (synthesis) → Static HTML → nginx
```

Processing runs on your machine. Output is static HTML served by nginx. Zero server-side compute at publish time.

## Quick start

```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and set passwords

docker compose up -d
# Pipeline runs daily at SCHEDULE_TIME (default 06:00)
# Site available at http://localhost
# pgAdmin at http://localhost:5050
```

## Run the pipeline manually

```bash
docker compose exec pipeline python main.py --run-now
```

## Project structure

```
briefer.news/
├── docker-compose.yml
├── .env.example
├── lens.md                     ← the interpretive framework Claude uses
├── pipeline/
│   ├── config/
│   │   └── sources.yaml        ← all news sources (edit here, no code changes)
│   ├── db/
│   │   ├── models.py
│   │   └── migrations/
│   │       └── 001_initial.sql
│   ├── scraper/
│   │   ├── discovery.py        ← RSS + Google News → article URLs
│   │   └── extractor.py        ← trafilatura → full article text
│   ├── processor/
│   │   ├── claude.py           ← per-article summarization + meta story
│   │   └── prompts.py
│   ├── builder/
│   │   ├── site.py             ← Jinja2 → static HTML
│   │   └── templates/
│   ├── scheduler.py
│   └── main.py
└── nginx/
    └── nginx.conf
```

## The lens

`lens.md` defines the interpretive framework Claude uses to generate the daily meta story.
Edit it freely — it's plain Markdown, loaded fresh each run. This is where the philosophy lives.
