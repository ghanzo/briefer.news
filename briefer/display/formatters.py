"""Number formatting, colored deltas, sparklines."""

import sys

from rich.text import Text

# Use ASCII-safe characters on Windows legacy consoles
_SPARK_CHARS_UNICODE = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
_SPARK_CHARS_ASCII = " .:-=+#@"

def _get_spark_chars() -> str:
    try:
        _SPARK_CHARS_UNICODE.encode(sys.stdout.encoding or "utf-8")
        return _SPARK_CHARS_UNICODE
    except (UnicodeEncodeError, LookupError):
        return _SPARK_CHARS_ASCII


def format_delta(value: float | None, percent: float | None = None) -> Text:
    """Return a Rich Text with colored arrow + delta."""
    if value is None:
        return Text("-", style="dim")
    if value > 0:
        arrow = "^"
        style = "green"
    elif value < 0:
        arrow = "v"
        style = "red"
    else:
        arrow = "-"
        style = "dim"

    parts = f"{arrow} {value:+,.2f}"
    if percent is not None:
        parts += f" ({percent:+.1f}%)"
    return Text(parts, style=style)


def format_number(value: float | None, units: str | None = None) -> str:
    """Format a number with context-appropriate precision."""
    if value is None:
        return "-"
    units_lower = (units or "").lower()

    if "percent" in units_lower or "rate" in units_lower:
        return f"{value:.2f}%"
    if "dollar" in units_lower and abs(value) >= 1_000:
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.1f}M"
        if abs(value) >= 1_000:
            return f"${value:,.0f}"
    if "index" in units_lower:
        return f"{value:,.1f}"
    if abs(value) < 1:
        return f"{value:.4f}"
    if abs(value) >= 10_000:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def sparkline(values: list[float], width: int = 20) -> str:
    """Generate a sparkline string from a list of values."""
    chars = _get_spark_chars()
    if not values:
        return ""
    if len(values) == 1:
        return chars[4]

    vals = values[-width:]
    mn, mx = min(vals), max(vals)
    rng = mx - mn
    if rng == 0:
        return chars[4] * len(vals)

    return "".join(
        chars[min(int((v - mn) / rng * 7), 7)]
        for v in vals
    )
