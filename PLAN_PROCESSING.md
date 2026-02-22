# Processing Pipeline — Master Plan

> This document supersedes `PLAN_SUMMARIZATION.md`.
> Updated: Feb 2026. Re-read this at the start of any processing work.

---

## The three-stage model

```
STAGE 1 — FILTER
  Input:  article stub (title + meta_description, from RSS/scrape — no full text yet)
  Model:  Groq Llama 3.3-70B (free tier)
  Output: keep | reject + reason
  Goal:   eliminate junk before any HTTP fetch or paid API call happens

        ↓ keep only

STAGE 2 — ARTICLE SUMMARIZATION
  Input:  full article text (fetched only for kept articles)
  Model:  Gemini 2.0 Flash (cheap, structured JSON)
  Output: structured summary per article (~100-150 words + metadata)
  Goal:   compress each article into a clean, precise, consistently structured unit
          that Stage 3 can reason over

        ↓ all summaries

STAGE 3 — META SUMMARIES
  Input:  all Stage 2 summaries for the day, grouped by category
  Model:  Claude Sonnet 4.6 (quality matters here — this is customer-facing)
  Output: multiple meta summary variants (see below)
  Goal:   produce the actual published content of the site
```

Everything in Stage 3 is public-facing. Stages 1 and 2 are internal infrastructure.

---

## Stage 1 — Filter

### What it filters

The filter runs on **title + meta_description only** — information available
from RSS/scraping before any article fetch. This means rejected articles cost:
- Zero HTTP requests
- Zero Playwright renders
- Zero Gemini calls

Things that should be filtered out:
- Routine travel advisories ("Level 2 Advisory: Exercise Increased Caution in X")
- Boilerplate public schedules ("Secretary's Schedule for [date]")
- Minor administrative notices (FOIA processing updates, form revisions)
- Pure procedural Federal Register items (comment period extensions, etc.)
- Duplicate coverage of a story already in the DB that day

Things that must NOT be filtered:
- Any policy announcement, even minor-sounding ones
- All enforcement actions (indictments, sanctions, consent orders)
- Scientific findings and research results
- Regulatory changes (even proposed rules — these matter)
- Diplomatic statements and foreign policy actions
- Anything from the White House (presidential actions especially)

**Bias toward keeping.** A false negative (dropping a real story) is worse than
a false positive (keeping a junk article that Gemini briefly summarizes).

### Testing strategy — do this before wiring in

This must be validated before the filter touches live scraping.

**Step 1:** Scrape a real batch (run `--scrape-only --limit 200`). Don't summarize.

**Step 2:** Run all stubs through the Groq filter in a standalone test script.
Log every decision with `{"keep": bool, "reason": "..."}`.

**Step 3:** Manual review. For every `keep: false` decision, ask:
"Would a well-informed person want to know about this?" If yes, the filter
is too aggressive — tighten the exclusion criteria in the prompt.

**Step 4:** Look for patterns in false positives (kept but worthless) and false
negatives (dropped but valuable). Adjust the prompt, re-run. Repeat until
the false negative rate is ~0% and false positive rate is acceptable (~20-30%
is fine — Gemini is cheap).

**Step 5:** Only then wire into the live pipeline behind `GROQ_FILTER_ENABLED=true`.

### DB changes needed

```sql
-- Permanent record of rejected stubs so we never re-scrape them
CREATE TABLE rejected_url_hashes (
    url_hash    VARCHAR(64) PRIMARY KEY,
    title       TEXT,
    reason      TEXT,        -- Groq's one-line reason — audit trail for tuning
    rejected_at TIMESTAMPTZ  DEFAULT NOW()
);

-- New column on articles (for articles already in DB before filter existed)
ALTER TABLE articles ADD COLUMN filtered_out BOOLEAN DEFAULT FALSE;

-- New counter on scrape_runs
ALTER TABLE scrape_runs ADD COLUMN articles_filtered INTEGER DEFAULT 0;
```

### Integration point

Filter runs in `run_scrape()` in `main.py`, after stub is discovered and
url_hash checked, but before `extract_article()` is called:

```
discover stub
→ check rejected_url_hashes (skip if found — already rejected)
→ check articles.url_hash (skip if found — already processed)
→ GROQ FILTER on title + meta_description
    → reject: save to rejected_url_hashes, skip
    → keep: proceed to extract_article()
```

The filter call lives in a new `pipeline/processor/filter.py`.

---

## Stage 2 — Article Summarization

### What the summary should contain

Each article produces a structured object stored in `article_summaries`:

```json
{
  "headline":         "8-12 word rewritten headline, precise and informative",
  "summary":          "100-150 word factual summary — what happened, who did it, what it means",
  "importance_score": 0.0,
  "category":         "geopolitics",
  "subcategory":      "sanctions",
  "tags":             ["OFAC", "Russia", "energy sanctions"],
  "entities":         ["OFAC", "Gazprom", "Treasury Department"],
  "time_sensitivity": "breaking | developing | background",
  "source_tier":      1
}
```

New fields vs current implementation:
- `subcategory` — finer-grained topic within category (useful for topic pages)
- `entities` — named entities extracted (people, orgs, countries) — enables filtering/search
- `time_sensitivity` — breaking news vs. background context vs. developing story

### The summarizer instructions document

The model's behavior is controlled by a prompt template in `prompts.py` and a
separate instructions document. Create:

**`pipeline/processor/summarizer_instructions.md`**

This document tells the model:
- What kind of reader this summary is written for (internal analyst, not public)
- What to prioritize when space is limited (action over context)
- How to handle uncertainty (attribute clearly, don't speculate)
- Entity naming conventions (full agency names on first mention, etc.)
- What "importance_score" means concretely with examples at each decile
- Category and subcategory taxonomy (so categories are consistent)

This is separate from `lens.md` which is the interpretive framework for Stage 3.
Stage 2 summaries should be factual and neutral — no interpretation.

### Model

**Gemini 2.0 Flash** (`gemini-2.0-flash-exp` or `gemini-2.0-flash`)
- $0.10/MTok input, $0.40/MTok output
- At 200 articles × ~1,500 tokens: ~$0.04/day
- At 1,000 articles × ~1,500 tokens: ~$0.20/day (scales well)
- Strong structured JSON output, handles technical/government content well
- API key: `GEMINI_API_KEY` from aistudio.google.com

Run in parallel (ThreadPoolExecutor, max_workers=10) — Gemini has generous
rate limits and Stage 2 is the volume bottleneck.

### Volume question

Current sources produce ~200-400 articles/day with 55 active sources.
Enabling tier-2 sources (Reuters, BBC, Google News topic feeds) would push
this to ~1,000-2,000/day. Gemini Flash handles this at ~$0.20-0.40/day.

Decision to make: **do you want tier-2 sources (wire services, Google News)?**
- Pro: broader topic coverage, catch stories the gov sources miss
- Con: much higher volume, more noise, filter becomes more important
- Recommendation: keep tier-1 only until the pipeline is stable and the
  filter is well-tuned, then add tier-2 selectively

---

## Stage 3 — Meta Summaries

### The core concept: multiple outputs, not one

The current pipeline produces a single `meta_story` per day. The redesign
produces **a suite of outputs** at different granularities and lengths,
which the site can use to compose different page layouts.

### Output variants

**A. The global meta story**
- ~400 words
- Synthesizes the entire day across all categories
- The interpretive piece — what does today mean, what forces are at work
- Uses `lens.md` as its framework
- Goes on the homepage hero section

**B. Category summaries** (one per active category)
- ~150 words each
- Factual synthesis of that category's top stories for the day
- Answers: "what happened in [energy/geopolitics/tech] today?"
- Goes on category landing pages and as cards on the homepage

**C. Topic briefs** (optional, for high-volume topics)
- ~100 words, more specific than category
- Example: "US-China tensions today", "Nuclear energy this week"
- Triggered when a subcategory has ≥5 articles in a day
- Good for topic-specific pages or newsletter sections

**D. Headline summaries**
- One sentence per article (the `headline` field from Stage 2)
- No additional AI call needed — already generated in Stage 2
- Used for feeds, digest emails, article list views

**E. Extended deep-dives** (future / optional)
- ~600-800 words on the single highest-importance story of the day
- Uses full article text of top 3-5 articles on that story, not just summaries
- One per day maximum, only if importance_score > 0.85 exists
- More like a briefing paper than a summary

### The site voice document

Create `pipeline/processor/site_voice.md`

This is the customer-facing equivalent of `lens.md`. Where `lens.md` says
"here is how to interpret the world", `site_voice.md` says "here is how to
write for the reader of this site."

It should cover:
- **Who the reader is** — expand on lens.md, but written from a publishing
  perspective. What do they want to feel after reading? (Informed, clear-headed,
  not anxious.)
- **Tone** — precise, calm, analytically serious. Not journalistic. Not academic.
  Like a trusted, well-briefed colleague explaining the day.
- **What good looks like** — 2-3 example paragraphs at the right quality bar
- **What to avoid** — hyperbole, passive voice, vague phrases ("amid growing
  concerns"), filler transitions
- **Length discipline** — each variant has a hard word count. Enforced in the
  prompt, not aspirational.
- **Structure rules** — does the meta story open with the biggest event, or
  with the underlying theme? (Answer this explicitly.)

This document gets injected into Stage 3 prompts the same way `lens.md` does.

### Model

**Claude Sonnet 4.6** for all Stage 3 calls.
- Quality is the priority here — this is the product
- Volume is low: ~15 calls/day total regardless of article count
- Cost is minimal: ~$0.10-0.15/day

Do not use Gemini or Groq for Stage 3. The writing quality difference is
noticeable at this length and register.

### DB changes needed

```sql
-- Expand daily_briefings or create new table for output variants
CREATE TABLE briefing_outputs (
    id            SERIAL PRIMARY KEY,
    briefing_id   INTEGER REFERENCES daily_briefings(id) ON DELETE CASCADE,
    output_type   VARCHAR(50) NOT NULL,  -- 'meta_story' | 'category' | 'topic_brief' | 'deep_dive'
    category      VARCHAR(100),          -- NULL for global meta_story
    topic         VARCHAR(200),          -- for topic_briefs
    headline      TEXT,
    body          TEXT,
    word_count    INTEGER,
    article_ids   JSONB DEFAULT '[]',    -- source articles for this output
    model_used    VARCHAR(100),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outputs_briefing  ON briefing_outputs(briefing_id);
CREATE INDEX idx_outputs_type_cat  ON briefing_outputs(output_type, category);
```

---

## Supporting documents to create

These are plain text/markdown files injected into prompts. They are the primary
levers for tuning output quality — change these, not the code.

| File | Stage | Purpose | Status |
|---|---|---|---|
| `pipeline/processor/filter_criteria.md` | 1 | What to keep vs. reject, with examples | Not created |
| `pipeline/processor/summarizer_instructions.md` | 2 | How to write article summaries, scoring rubric | Not created |
| `lens.md` | 3 | Interpretive framework for the meta story | Exists (good) |
| `pipeline/processor/site_voice.md` | 3 | Writing style, tone, structure for customer-facing output | Not created |

All four documents should be versioned in git. Changes to them change the
product — treat them like code.

---

## Revised full pipeline

```
sources.yaml
    → discovery (RSS + Playwright)
    → stub (title, url, meta_description)
    → check rejected_url_hashes          ← skip if previously rejected
    → check articles table               ← skip if already processed
    → STAGE 1: Groq filter               ← filter_criteria.md
        → reject → rejected_url_hashes
        → keep ↓
    → extract full text (httpx or Playwright)
    → STAGE 2: Gemini Flash              ← summarizer_instructions.md
        → article_summaries row (headline, summary, importance_score, entities, etc.)
    → STAGE 3: Claude Sonnet             ← lens.md + site_voice.md
        → global meta story              → briefing_outputs (type=meta_story)
        → category summaries ×N          → briefing_outputs (type=category)
        → topic briefs (if triggered)    → briefing_outputs (type=topic_brief)
    → build_site()
        → renders all output variants into HTML
        → nginx serves
```

---

## Implementation order

### Phase 1 — Groundwork (no user-facing changes)
1. Write `filter_criteria.md` (draft, will iterate)
2. Write `summarizer_instructions.md` (draft)
3. Run filter evaluation test on real scraped data — tune until false negatives ~0
4. Add DB migrations (rejected_url_hashes, filtered_out, briefing_outputs)

### Phase 2 — Wire in filter
5. Build `pipeline/processor/filter.py` (Groq API wrapper)
6. Integrate into `run_scrape()` behind `GROQ_FILTER_ENABLED=true`
7. Run in shadow mode for a week: filter runs but doesn't block, just logs
8. Review logs, tune, flip to active

### Phase 3 — Upgrade summarization
9. Add Gemini Flash as summarization model
10. Expand article_summaries schema (subcategory, entities, time_sensitivity)
11. Parallelize Stage 2 (ThreadPoolExecutor)
12. Update `summarizer_instructions.md` based on first real outputs

### Phase 4 — Expand meta outputs
13. Write `site_voice.md`
14. Build multi-variant Stage 3 (category summaries, topic briefs)
15. Create briefing_outputs table
16. Update site templates to use new output variants

### Phase 5 — Scale (when ready)
17. Enable tier-2 sources selectively
18. Evaluate whether Groq free tier still covers volume (500K tokens/day cap)
19. Add extended deep-dives if highest-importance stories warrant it

---

## Open questions

**Volume:**
- How many articles/day is the target? 200 (tier-1 only) or 1,000+ (with tier-2)?
- This gates whether the Groq free tier is sufficient for Stage 1.

**Meta summary variants:**
- Which variants are needed for v1 of the site? Just global + category?
  Or do topic briefs and deep-dives need to be in v1?
- What are the hard word counts for each? (Need to decide and put in prompts.)

**Article retention:**
- How long do articles stay in the DB? Forever, or rolling 90 days?
- Rejected stubs (rejected_url_hashes): keep forever (small, useful for audit).

**Importance threshold:**
- What score gates inclusion in category synthesis? Suggest: >= 0.25
- What score triggers a topic brief? Suggest: >= 3 articles with score >= 0.6
  in the same subcategory on the same day.

**Site structure (informs what Stage 3 needs to produce):**
- Homepage: meta story + category cards + top article headlines?
- Category pages: category summary + article list?
- Article pages: link out to source, show Stage 2 summary?
- Is there a "today's top story" featured slot?
