"""Generate a local HTML dashboard from DuckDB data."""

import webbrowser
from datetime import date, datetime
from pathlib import Path

from briefer.analysis.deltas import compute_series_delta, rank_movers
from briefer.db.connection import get_connection
from briefer.db.queries import get_all_series, get_observations
from briefer.display.formatters import format_number

OUTPUT_DIR = Path.home() / ".briefer"


def _sparkline_svg(values: list[float], width: int = 120, height: int = 30) -> str:
    """Generate an inline SVG sparkline."""
    if len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    points = []
    for i, v in enumerate(values):
        x = (i / (len(values) - 1)) * width
        y = height - ((v - mn) / rng) * (height - 2) - 1
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    # Color based on trend
    first, last = values[0], values[-1]
    color = "#22c55e" if last > first else "#ef4444" if last < first else "#888"
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
    )


def _delta_html(delta: dict) -> str:
    change = delta.get("absolute_change")
    pct = delta.get("percent_change")
    if change is None:
        return '<span class="neutral">-</span>'
    if change > 0:
        arrow = "&#9650;"
        cls = "up"
    elif change < 0:
        arrow = "&#9660;"
        cls = "down"
    else:
        arrow = "&#8211;"
        cls = "neutral"
    text = f"{arrow} {change:+,.2f}"
    if pct is not None:
        text += f" ({pct:+.1f}%)"
    return f'<span class="{cls}">{text}</span>'


def _zscore_html(z: float | None) -> str:
    if z is None:
        return '<span class="neutral">-</span>'
    if abs(z) > 2:
        cls = "z-extreme"
    elif abs(z) > 1:
        cls = "z-notable"
    else:
        cls = "z-normal"
    return f'<span class="{cls}">{z:+.2f}</span>'


def build_dashboard(db_path: str | None = None) -> Path:
    """Build the HTML dashboard and return the file path."""
    conn = get_connection(db_path)
    all_series = get_all_series(conn)

    rows = []
    for s in all_series:
        obs = get_observations(conn, s["series_id"], limit=260)
        if not obs:
            continue
        delta = compute_series_delta(obs)
        values = [o["value"] for o in reversed(obs) if o["value"] is not None]
        rows.append({**s, **delta, "sparkline_values": values[-60:]})

    conn.close()

    movers = rank_movers(rows)

    # Group by category
    categories: dict[str, list] = {}
    for r in rows:
        cat = r.get("category") or "other"
        categories.setdefault(cat, []).append(r)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    html = _render_html(movers, categories, now)

    out = OUTPUT_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


def _render_html(movers: list, categories: dict, build_time: str) -> str:
    # Build top movers rows
    mover_rows = ""
    for i, m in enumerate(movers[:10], 1):
        spark = _sparkline_svg(m.get("sparkline_values", []))
        mover_rows += f"""
        <tr>
            <td class="rank">{i}</td>
            <td>
                <div class="series-name">{m.get('name', m.get('series_id', ''))}</div>
                <div class="series-id">{m.get('series_id', '')}</div>
            </td>
            <td class="num">{format_number(m.get('latest_value'), m.get('units'))}</td>
            <td class="num">{_delta_html(m)}</td>
            <td class="num">{_zscore_html(m.get('z_score'))}</td>
            <td>{spark}</td>
        </tr>"""

    # Build category sections
    cat_sections = ""
    cat_order = ["rates", "markets", "employment", "inflation", "gdp", "energy",
                 "commodities", "money", "forex", "credit", "other"]
    sorted_cats = sorted(categories.keys(), key=lambda c: cat_order.index(c) if c in cat_order else 99)

    for cat in sorted_cats:
        series_list = categories[cat]
        card_html = ""
        for s in series_list:
            spark = _sparkline_svg(s.get("sparkline_values", []), width=100, height=24)
            card_html += f"""
            <div class="card">
                <div class="card-header">
                    <div class="card-name">{s.get('name', '')}</div>
                    <div class="card-id">{s.get('series_id', '')}</div>
                </div>
                <div class="card-value">{format_number(s.get('latest_value'), s.get('units'))}</div>
                <div class="card-delta">{_delta_html(s)}</div>
                <div class="card-spark">{spark}</div>
                <div class="card-meta">
                    <span>Z: {_zscore_html(s.get('z_score'))}</span>
                    <span class="freq">{s.get('frequency', '')}</span>
                    <span class="date">{s.get('latest_date', '')}</span>
                </div>
            </div>"""

        cat_sections += f"""
        <div class="category-section">
            <h2>{cat.upper()}</h2>
            <div class="card-grid">{card_html}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Briefer Dashboard</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #232733;
    --border: #2a2e3a;
    --text: #e4e4e7;
    --text-dim: #71717a;
    --text-faint: #52525b;
    --up: #22c55e;
    --down: #ef4444;
    --accent: #3b82f6;
    --z-extreme: #f59e0b;
    --z-notable: #a78bfa;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 14px;
    line-height: 1.5;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem; }}

  /* Header */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--border);
    padding-bottom: 1rem;
    margin-bottom: 2rem;
  }}
  .header h1 {{
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }}
  .header .meta {{ color: var(--text-dim); font-size: 0.8rem; }}

  /* Top movers table */
  .movers {{ margin-bottom: 2.5rem; }}
  .movers h2 {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.75rem;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
    border-radius: 8px;
    overflow: hidden;
  }}
  th {{
    text-align: left;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-faint);
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--border);
  }}
  td {{
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover {{ background: var(--surface2); }}
  .rank {{ color: var(--text-faint); font-weight: 700; width: 30px; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .series-name {{ font-weight: 600; font-size: 0.85rem; }}
  .series-id {{ font-size: 0.7rem; color: var(--text-faint); font-family: monospace; }}

  /* Delta colors */
  .up {{ color: var(--up); font-weight: 600; }}
  .down {{ color: var(--down); font-weight: 600; }}
  .neutral {{ color: var(--text-dim); }}
  .z-extreme {{ color: var(--z-extreme); font-weight: 700; }}
  .z-notable {{ color: var(--z-notable); font-weight: 600; }}
  .z-normal {{ color: var(--text-dim); }}

  /* Category sections */
  .category-section {{ margin-bottom: 2rem; }}
  .category-section h2 {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }}
  .card-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 0.75rem;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    transition: border-color 0.15s;
  }}
  .card:hover {{ border-color: var(--accent); }}
  .card-header {{ margin-bottom: 0.5rem; }}
  .card-name {{ font-weight: 600; font-size: 0.85rem; line-height: 1.3; }}
  .card-id {{ font-size: 0.65rem; color: var(--text-faint); font-family: monospace; }}
  .card-value {{ font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0; font-variant-numeric: tabular-nums; }}
  .card-delta {{ margin-bottom: 0.5rem; font-size: 0.85rem; }}
  .card-spark {{ margin: 0.5rem 0; }}
  .card-meta {{
    display: flex;
    gap: 0.75rem;
    font-size: 0.7rem;
    color: var(--text-faint);
  }}

  /* Footer */
  footer {{
    text-align: center;
    padding: 2rem 0 1rem;
    font-size: 0.75rem;
    color: var(--text-faint);
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>BRIEFER</h1>
    <div class="meta">Built {build_time} &middot; {sum(len(v) for v in categories.values())} series tracked</div>
  </div>

  <div class="movers">
    <h2>Top Movers</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Series</th>
          <th style="text-align:right">Value</th>
          <th style="text-align:right">Change</th>
          <th style="text-align:right">Z-Score</th>
          <th>60d</th>
        </tr>
      </thead>
      <tbody>{mover_rows}</tbody>
    </table>
  </div>

  {cat_sections}

  <footer>briefer &middot; data from FRED &middot; {build_time}</footer>
</div>
</body>
</html>"""
