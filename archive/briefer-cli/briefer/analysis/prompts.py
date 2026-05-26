"""All prompts for the AI interpretation layer."""

SERIES_INTERPRETATION_PROMPT = """\
You are an economic analyst. Interpret this data movement concisely.

## Series: {name}
- Source: {source} | Units: {units} | Frequency: {frequency}
- Latest: {latest_value} ({latest_date})
- Previous: {prior_value} ({prior_date})
- Change: {absolute_change} ({percent_change}%)
- Direction: {direction}
- Z-score (vs trailing history): {z_score}
- 52-week range: {min_52w} — {max_52w} (current percentile: {percentile_52w})
- Trend: {trend}

## Recent observations:
{history_table}

Write 2-3 sentences interpreting what this movement means.
Be specific about magnitudes and context.
Do not speculate about causes you cannot infer from the data.
If the z-score is high (>2 or <-2), note that this is an unusual move.
"""

DIGEST_PROMPT = """\
You are writing a daily economic data digest for {date}.

## What moved today (ranked by significance):
{movers_summary}

Write a 3-4 paragraph interpretation of what today's data means.
Lead with the most significant movement. Connect related indicators when relevant.
Note any divergences or confirmations across data sources.
Close with what to watch next.

Respond with ONLY this JSON (no markdown fences):
{{
    "headline": "One sharp headline capturing the key signal (10-15 words)",
    "body": "3-4 paragraphs of interpretation. Use \\n\\n between paragraphs."
}}
"""
