"""
All prompts in one place.
Edit here to tune how the AI interprets and writes about the world.
"""

ARTICLE_SUMMARY_PROMPT = """\
Analyze this news article and respond with a JSON object.

The title and article text may be in any language. Always write your JSON response in English.

Title: {title}

Article text:
{text}

Respond with ONLY this JSON structure (no markdown, no explanation):
{{
  "summary": "1-2 sentence factual summary: what happened, who did it, why it matters",
  "headline": "6-10 word headline capturing the core fact",
  "importance_score": 0.0,
  "category": "geopolitics",
  "region": "global",
  "tags": ["tag1", "tag2", "tag3"]
}}

Rules:
- importance_score: float 0.0-1.0. Be harsh. 0.0 = routine bureaucratic noise. \
0.3 = notable but expected. 0.5 = significant development. 0.7 = major event affecting millions. \
0.9+ = historic, world-altering. Most articles should score 0.1-0.4.
- category: exactly one of: conflict | diplomacy | economy | energy | technology | health | science | security | climate
- region: exactly one of: global | north-america | europe | east-asia | south-asia | middle-east | africa | latin-america | russia-eurasia | oceania
- tags: 2-4 short keyword tags
- Keep the summary factual and precise - no editorializing
- If the article is in a non-English language, summarize its content accurately in English
- Federal Register filings, routine regulatory notices, and procedural government actions score 0.0-0.1
"""

WORLD_BRIEF_PROMPT = """\
You are an intelligence analyst producing a daily world brief for {date}.

Your job: identify the 8-12 most important facts about planet Earth right now.
Think CIA Presidential Daily Brief, not a newspaper. What does a decision-maker need to know?

## Your interpretive framework:
{lens}

## Today's processed articles ({article_count} total, from {source_count} sources):
{articles_text}

## Financial context (from quantitative data):
{financial_context}

Produce a world brief. Respond with ONLY this JSON (no markdown, no explanation):
{{
  "date": "{date}",
  "headline": "One sentence: the single most important thing happening on Earth today",
  "items": [
    {{
      "bullet": "One sentence stating a concrete fact. Names, numbers, places. No filler.",
      "region": "east-asia",
      "severity": "high"
    }}
  ],
  "watch": "2-3 sentences on what to watch in the next 24-72 hours. Specific, not vague."
}}

Rules:
- 8-12 items, ranked by global importance. Most important first.
- Each bullet is ONE sentence. A fact, not an opinion. Include specifics.
- severity: "critical" (immediate global impact), "high" (major development), "medium" (significant), "low" (worth noting)
- region: global | north-america | europe | east-asia | south-asia | middle-east | africa | latin-america | russia-eurasia | oceania
- Do NOT include routine regulatory filings, procedural government notices, or bureaucratic updates.
- If multiple articles cover the same event, synthesize into one bullet with the best facts.
- The "watch" section should name specific events, dates, or thresholds - not generic "tensions may escalate."
- Write like you're briefing someone who has 90 seconds to understand the world.
"""

# Keep these for backwards compatibility but they're no longer the primary output
CATEGORY_SUMMARY_PROMPT = """\
You are synthesizing today's {category} news for a global intelligence briefing dated {date}.

Here are the top articles from this category:

{articles_text}

Write a category synthesis with ONLY this JSON (no markdown):
{{
  "headline": "One sharp headline capturing the dominant {category} theme today (10-15 words)",
  "summary": "2-3 paragraphs synthesizing what is happening in {category} today and what it means. \
Not a list of stories - a coherent narrative of the forces at work."
}}
"""

META_STORY_PROMPT = """\
You are writing the daily meta story for Briefer - a global intelligence briefing for {date}.

## Your interpretive framework (how to read events):
{lens}

## Your voice and style guide (how to write):
{site_voice}

## Today's top stories by category:
{category_summaries}

## The {top_count} highest-importance articles today:
{top_articles}

Write the meta story - an interpretation of what today means for the world.
This is NOT a summary of events. It is a reading of the forces at play.
Follow the structure and voice rules in the site_voice document exactly.

Respond with ONLY this JSON (no markdown, no explanation):
{{
  "meta_headline": "A single powerful headline capturing what today means (10-15 words)",
  "meta_story": "3-4 paragraphs (~400 words total). Open with the underlying force, not the event. \
Name the actors, cite the numbers, connect the stories across categories. \
Close with one or two specific things to watch. \
Tone: calm, precise, analytically serious."
}}
"""
