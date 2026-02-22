# Summarization Pipeline — Plan & Context

> **SUPERSEDED** — see `PLAN_PROCESSING.md` for the current master plan.
> This file kept for reference on Groq filter and model cost details.

## Current state (as of Feb 2026)

The pipeline already implements a tiered summarization architecture:

```
Article full_text (capped at 5,000 chars in code)
    → Claude Haiku 4.5   — per-article: summary, headline, importance_score, tags
    → Claude Sonnet 4.6  — category synthesis (receives Haiku summaries, not full text)
    → Claude Sonnet 4.6  — meta story (uses lens.md as interpretive framework)
```

**Relevant files:**
- `pipeline/processor/claude.py`     — all API calls (`summarize_article`, `generate_category_summaries`, `generate_meta_story`)
- `pipeline/processor/prompts.py`    — all prompt templates (edit here to tune output)
- `pipeline/main.py`                 — `run_process()` orchestrates the loop
- `lens.md`                          — editorial framework injected into meta story prompt

**Current cost estimate** (~200 articles/day, 55 active sources):
- Haiku per-article: ~$0.35/day
- Sonnet synthesis: ~$0.15/day
- **Total: ~$0.50/day**

The `run_process()` loop is currently **serial** — processes one article at a time.

---

## Planned improvements

### 1. Groq pre-filter (before extraction)

**Goal:** Use a cheap/free LLM to decide whether an article stub is worth
extracting and summarizing at all. Runs on title + meta_description only
(available from RSS without fetching the article URL), so junk never costs
an HTTP request, a Playwright render, or a Haiku call.

**Why:** Many sources produce low-signal articles — routine State Dept travel
advisories, CDC newsletter items, boilerplate schedule posts. These inflate
processing cost and dilute the briefing.

**Groq:**
- Cloud API (groq.com) — NOT a local model, nothing runs on your machine
- Free tier: 14,400 req/day, ~500K tokens/day — sufficient for this use case
- Model: `llama-3.3-70b-versatile` (best quality on free tier)
- Same call pattern as Anthropic: `groq.Groq(api_key=...).chat.completions.create(...)`
- Add `groq` to requirements.txt, `GROQ_API_KEY` to .env

**Filter runs at:** between discovery (stub found) and extraction (full text fetched).

**Prompt shape:**
```
Given this article title and description from a government news source,
should it be included in a global intelligence briefing?

Title: {title}
Description: {meta_description}
Source: {source_name}

Respond with JSON only: {"keep": true/false, "reason": "one line"}

Exclude if: routine travel advisory, boilerplate schedule/calendar post,
minor administrative notice, duplicate/update of already-covered story.
Keep if: policy announcement, enforcement action, scientific finding,
regulatory change, diplomatic statement, any genuine news event.
```

**New DB table needed:**
```sql
CREATE TABLE rejected_url_hashes (
    url_hash    VARCHAR(64) PRIMARY KEY,
    title       TEXT,
    reason      TEXT,        -- Groq's rejection reason, useful for tuning
    rejected_at TIMESTAMPTZ  DEFAULT NOW()
);
```

**Integration point in `main.py` `run_scrape()`:**
```python
# After save_article_stub(), before extract_article():
if groq_filter_enabled:
    keep, reason = groq_filter(stub["title"], stub.get("meta_description", ""), source_name)
    if not keep:
        # mark article filtered, store hash so we never re-scrape
        article.filtered_out = True
        session.commit()
        save_rejected_hash(session, stub["url_hash"], stub["title"], reason)
        run.articles_filtered += 1
        continue
```

Also need `filtered_out` boolean column on `articles` table and
`articles_filtered` counter on `scrape_runs`.

**Before wiring in:** run a manual evaluation pass — feed a sample of 50-100
real scraped article stubs through the filter and review pass/fail. The
`reason` field in the response makes this easy to audit. Tune the prompt
until precision is acceptable (better to keep borderline articles than to
drop real news).

---

### 2. Switch per-article model to Gemini 2.0 Flash

**Goal:** Reduce per-article summarization cost ~8× with no meaningful
quality loss.

**Model comparison** (200 articles/day, ~1,500 input tokens each):

| Model                      | $/MTok in | $/MTok out | Est. daily |
|----------------------------|-----------|------------|------------|
| Gemini 2.0 Flash           | $0.10     | $0.40      | ~$0.04     |
| GPT-4o-mini                | $0.15     | $0.60      | ~$0.06     |
| Claude Haiku 4.5 (Batch)   | $0.40     | $2.00      | ~$0.18     |
| Claude Haiku 4.5 (current) | $0.80     | $4.00      | ~$0.35     |

**Recommendation: Gemini 2.0 Flash** — best cost/quality ratio for structured
JSON extraction from government/technical content. Google API reliability is
solid. Handles the article summary prompt well.

**API key:** `GEMINI_API_KEY` from aistudio.google.com (free quota available).
**Package:** `google-generativeai` or `google-genai`

**Keep Sonnet for synthesis** — the category summaries and meta story are
low-volume (10-15 calls/day total) and quality matters more there.

**Not recommended for per-article:** Groq/Llama — open models hallucinate
entity names and misattribute policy actions at higher rates than Haiku.
Acceptable for a yes/no filter, not for producing summaries that Sonnet
will then synthesize.

---

### 3. Anthropic Batch API for Haiku (alternative to #2)

If staying with Anthropic for everything, use the Batch API for the
per-article Haiku step:
- **50% cost reduction** automatically
- Processes within 24h (fine for a daily pipeline)
- Requires restructuring `run_process()` to submit a batch, wait, collect results
- See: https://docs.anthropic.com/en/docs/build-with-claude/batch-processing

This is simpler than adding a new provider but saves less than Gemini Flash.
Could combine: Gemini Flash for per-article + Sonnet (direct) for synthesis.

---

### 4. Parallelize `run_process()` (quick win)

Current code is a serial for-loop. Simple fix with `concurrent.futures`:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(summarize_article, claude, a.title, a.full_text): a
               for a in unprocessed}
    for future, article in futures.items():
        result = future.result()
        # save to DB...
```

Rate limit awareness needed — add a semaphore or use tenacity for backoff.
Reduces wall-clock time for processing stage significantly at high volumes.

---

## Implementation order (recommended)

1. **Manual filter evaluation** — scrape a batch, run stubs through Groq manually,
   review `reason` fields, tune prompt. No code changes yet.

2. **`rejected_url_hashes` migration** + `filtered_out` on articles — schema only.

3. **Wire in Groq filter** behind a `GROQ_FILTER_ENABLED=true` env flag so it
   can be toggled off instantly if it misbehaves.

4. **Switch per-article model to Gemini Flash** or enable Batch API — do after
   filter is stable so cost/quality baselines are clean.

5. **Parallelize `run_process()`** — lowest risk, independent of other changes.

---

## Open questions

- What importance_score threshold should gate inclusion in category synthesis?
  (Currently all non-failed articles go in — probably should be >= 0.3)
- Should filtered_out articles be deleted from the articles table eventually,
  or kept indefinitely with the flag? (Keeping them is safer for audit.)
- Groq free tier limit: 500K tokens/day. At ~500 tokens per filter call,
  that's 1,000 articles/day before hitting the cap. Fine for now.
