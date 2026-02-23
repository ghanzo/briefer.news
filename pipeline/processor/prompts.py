"""
All Claude prompts in one place.
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
  "summary": "2-3 sentence factual summary of what happened and why it matters",
  "headline": "Compelling 8-12 word headline capturing the core event",
  "importance_score": 0.0,
  "category": "geopolitics",
  "tags": ["tag1", "tag2", "tag3"]
}}

Rules:
- importance_score: float 0.0–1.0 where 0.0 = routine/trivial, 0.5 = notable, 1.0 = historically significant
- category: exactly one of: geopolitics | technology | finance | energy | science | health | innovation
- tags: 2–5 short keyword tags
- Keep the summary factual and precise — no editorializing
- If the article is in a non-English language, summarize its content accurately in English
"""

CATEGORY_SUMMARY_PROMPT = """\
You are synthesizing today's {category} news for a global intelligence briefing dated {date}.

Here are the top articles from this category:

{articles_text}

Write a category synthesis with ONLY this JSON (no markdown):
{{
  "headline": "One sharp headline capturing the dominant {category} theme today (10-15 words)",
  "summary": "2-3 paragraphs synthesizing what is happening in {category} today and what it means. \
Not a list of stories — a coherent narrative of the forces at work."
}}
"""

META_STORY_PROMPT = """\
You are writing the daily meta story for Briefer — a global intelligence briefing for {date}.

## Your interpretive framework:
{lens}

## Today's top stories by category:
{category_summaries}

## The {top_count} highest-importance articles today:
{top_articles}

Write the meta story — an interpretation of what today means for the world.
This is NOT a summary of events. It is a reading of the forces at play.

Respond with ONLY this JSON (no markdown, no explanation):
{{
  "meta_headline": "A single powerful headline capturing what today means (10-15 words)",
  "meta_story": "3-4 paragraphs. What is the world saying today? \
What underlying forces do these events reveal? \
Where is tension building? What does this moment tell us about the trajectory ahead? \
Tone: calm, precise, analytically serious — like a private memo from a clear-eyed analyst."
}}
"""
