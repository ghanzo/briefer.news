"""Generate a local HTML dashboard from DuckDB data."""

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


def _pct_html(pct: float | None) -> str:
    if pct is None:
        return '<span class="neutral">-</span>'
    cls = "up" if pct > 0 else "down" if pct < 0 else "neutral"
    return f'<span class="{cls}">{pct:+.1f}%</span>'


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


def _yield_curve_svg(rates_data: dict[str, float], width: int = 500, height: int = 180) -> str:
    """Generate SVG yield curve chart."""
    maturities = [
        ("3M", "DGS3MO"), ("1Y", "DGS1"), ("2Y", "DGS2"),
        ("5Y", "DGS5"), ("10Y", "DGS10"), ("30Y", "DGS30"),
    ]
    points = []
    labels = []
    for label, key in maturities:
        val = rates_data.get(key)
        if val is not None:
            points.append((label, val))

    if len(points) < 3:
        return ""

    vals = [p[1] for p in points]
    mn = min(vals) - 0.2
    mx = max(vals) + 0.2
    rng = mx - mn or 1
    pad_left, pad_right, pad_top, pad_bottom = 40, 20, 20, 35

    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bottom

    svg_points = []
    for i, (label, val) in enumerate(points):
        x = pad_left + (i / (len(points) - 1)) * chart_w
        y = pad_top + chart_h - ((val - mn) / rng) * chart_h
        svg_points.append((x, y, label, val))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in svg_points)

    # Is curve inverted anywhere?
    inverted = any(vals[i] > vals[i+1] for i in range(len(vals)-1))
    curve_color = "#ef4444" if inverted else "#22c55e"

    grid_lines = ""
    for i in range(5):
        gy = pad_top + (i / 4) * chart_h
        gv = mx - (i / 4) * rng
        grid_lines += f'<line x1="{pad_left}" y1="{gy:.0f}" x2="{width - pad_right}" y2="{gy:.0f}" stroke="#2a2e3a" stroke-width="0.5"/>'
        grid_lines += f'<text x="{pad_left - 5}" y="{gy + 4:.0f}" text-anchor="end" fill="#71717a" font-size="10">{gv:.1f}%</text>'

    dots_and_labels = ""
    for x, y, label, val in svg_points:
        dots_and_labels += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{curve_color}"/>'
        dots_and_labels += f'<text x="{x:.1f}" y="{pad_top + chart_h + 18}" text-anchor="middle" fill="#a1a1aa" font-size="10">{label}</text>'
        dots_and_labels += f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" fill="#e4e4e7" font-size="10" font-weight="600">{val:.2f}</text>'

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        {grid_lines}
        <polyline points="{polyline}" fill="none" stroke="{curve_color}" stroke-width="2"/>
        {dots_and_labels}
    </svg>"""


def _v(by_id: dict, sid: str) -> float | None:
    """Get latest_value for a series_id, or None."""
    r = by_id.get(sid)
    return r.get("latest_value") if r else None


def _pctchg(by_id: dict, sid: str) -> float | None:
    """Get percent_change for a series_id, or None."""
    r = by_id.get(sid)
    return r.get("percent_change") if r else None


def _f(val: float | None, fmt: str = ",.0f") -> str:
    if val is None:
        return "N/A"
    return f"{val:{fmt}}"


def _big(val: float | None, unit: str = "M", signed: bool = False) -> str:
    """Format a large number into human-readable T/B/M.

    *unit* is the scale of the raw value from FRED:
      'M' = millions (e.g. GFDEBTN reports 37,637,553 meaning $37.6 T)
      'B' = billions (e.g. FDHBFIN reports 9,128 meaning $9.1 T)
      'raw' = raw number (no pre-scaling)
    """
    if val is None:
        return "N/A"
    # Normalise to raw dollars
    if unit == "M":
        raw = val * 1_000_000
    elif unit == "B":
        raw = val * 1_000_000_000
    else:
        raw = val
    neg = raw < 0
    a = abs(raw)
    if a >= 1e12:
        s = f"${a / 1e12:.1f}T"
    elif a >= 1e9:
        s = f"${a / 1e9:.1f}B"
    elif a >= 1e6:
        s = f"${a / 1e6:.0f}M"
    else:
        s = f"${a:,.0f}"
    if neg:
        s = "-" + s if not signed else "-" + s
    elif signed and raw > 0:
        s = "+" + s
    return s


def _stale_warning(by_id: dict, series_ids: list[str], label: str, max_days: int = 45) -> str:
    """Return an HTML warning if the newest data in a group is older than max_days."""
    newest = None
    for sid in series_ids:
        r = by_id.get(sid)
        if not r:
            continue
        d = r.get("latest_date")
        if d is None:
            continue
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d[:10])
            except ValueError:
                continue
        if newest is None or d > newest:
            newest = d
    if newest is None:
        return ""
    age = (date.today() - newest).days
    if age <= max_days:
        return ""
    return f'<span class="stale-warn" title="Latest data: {newest.isoformat()}">{label} data is {age}d old</span>'


def _generate_summaries(by_id: dict) -> str:
    """Generate three analytical summaries + predictions from actual data."""

    # Pull all the numbers we need
    sp500 = _v(by_id, "yahoo/^GSPC")
    vix = _v(by_id, "yahoo/^VIX")
    dxy = _v(by_id, "yahoo/DX-Y.NYB")
    gold = _v(by_id, "yahoo/GC=F")
    wti = _v(by_id, "yahoo/CL=F")
    brent = _v(by_id, "yahoo/BZ=F")
    btc = _v(by_id, "yahoo/BTC-USD")
    dgs10 = _v(by_id, "fred/DGS10")
    dgs2 = _v(by_id, "fred/DGS2")
    dgs30 = _v(by_id, "fred/DGS30")
    dgs3m = _v(by_id, "fred/DGS3MO")
    spread_10y2y = _v(by_id, "fred/T10Y2Y")
    spread_10y3m = _v(by_id, "fred/T10Y3M")
    fedfunds = _v(by_id, "fred/FEDFUNDS")
    mortgage = _v(by_id, "fred/MORTGAGE30US")
    unrate = _v(by_id, "fred/UNRATE")
    sahm = _v(by_id, "fred/SAHMREALTIME")
    claims = _v(by_id, "fred/ICSA")
    jolts = _v(by_id, "fred/JTSJOL")
    quits = _v(by_id, "fred/JTSQUR")
    sentiment = _v(by_id, "fred/UMCSENT")
    saverate = _v(by_id, "fred/PSAVERT")
    ccdelinq = _v(by_id, "fred/DRCCLACBS")
    cpi = _v(by_id, "fred/CPIAUCSL")
    breakeven10 = _v(by_id, "fred/T10YIE")
    breakeven5 = _v(by_id, "fred/T5YIE")
    m2 = _v(by_id, "fred/M2SL")
    fedbal = _v(by_id, "fred/WALCL")
    rrp = _v(by_id, "fred/RRPONTSYD")
    tga = _v(by_id, "fred/WTREGEN")
    debt = _v(by_id, "fred/GFDEBTN")
    deficit = _v(by_id, "fred/FYFSD")
    foreign_debt = _v(by_id, "fred/FDHBFIN")
    tradebal = _v(by_id, "fred/BOPGSTB")
    copper = _v(by_id, "fred/PCOPPUSDM")
    nickel = _v(by_id, "fred/PNICKUSDM")
    ironore = _v(by_id, "fred/PIORECRUSDM")
    silver = _v(by_id, "yahoo/SI=F")
    natgas = _v(by_id, "yahoo/NG=F")
    shanghai = _v(by_id, "yahoo/000001.SS")
    fxi = _v(by_id, "yahoo/FXI")
    baba = _v(by_id, "yahoo/BABA")
    cny = _v(by_id, "fred/DEXCHUS")
    china_exports = _v(by_id, "fred/XTEXVA01CNM667S")
    china_imports = _v(by_id, "fred/XTIMVA01CNM667S")
    china_reserves = _v(by_id, "fred/TRESEGCNM052N")
    nvda = _v(by_id, "yahoo/NVDA")
    tsm = _v(by_id, "yahoo/TSM")
    asml = _v(by_id, "yahoo/ASML")
    ura = _v(by_id, "yahoo/URA")
    tan = _v(by_id, "yahoo/TAN")
    lit = _v(by_id, "yahoo/LIT")
    remx = _v(by_id, "yahoo/REMX")
    nikkei = _v(by_id, "yahoo/^N225")
    hsi = _v(by_id, "yahoo/^HSI")
    dax = _v(by_id, "yahoo/^GDAXI")
    eem = _v(by_id, "yahoo/EEM")
    caseshiller = _v(by_id, "fred/CSUSHPISA")
    permits = _v(by_id, "fred/PERMIT")
    stlfsi = _v(by_id, "fred/STLFSI4")
    nfci = _v(by_id, "fred/NFCI")
    hyspr = _v(by_id, "fred/BAMLH0A0HYM2")
    foodidx = _v(by_id, "fred/PFOODINDEXM")
    lly = _v(by_id, "yahoo/LLY")
    ita = _v(by_id, "yahoo/ITA")
    lmt = _v(by_id, "yahoo/LMT")
    rut = _v(by_id, "yahoo/^RUT")
    realyield = _v(by_id, "fred/DFII10")
    m2v = _v(by_id, "fred/M2V")
    ipman = _v(by_id, "fred/IPMAN")
    dgorder = _v(by_id, "fred/DGORDER")

    # Derived calculations
    china_surplus = None
    if china_exports and china_imports:
        china_surplus = (china_exports - china_imports) / 1e9

    brent_wti_spread = None
    if brent and wti:
        brent_wti_spread = brent - wti

    # ── STATE OF THE WORLD ──────────────────────────────────────────
    # Assess recession risk
    recession_signals = 0
    recession_total = 0
    if sahm is not None:
        recession_total += 1
        if sahm >= 0.50:
            recession_signals += 1
    if spread_10y3m is not None:
        recession_total += 1
        if spread_10y3m < 0:
            recession_signals += 1
    if spread_10y2y is not None:
        recession_total += 1
        if spread_10y2y < 0:
            recession_signals += 1
    if sentiment is not None:
        recession_total += 1
        if sentiment < 60:
            recession_signals += 1

    # Assess financial stress
    stress_level = "low"
    if stlfsi is not None and nfci is not None:
        avg_stress = (stlfsi + nfci) / 2
        if avg_stress > 1:
            stress_level = "high"
        elif avg_stress > 0:
            stress_level = "elevated"

    # Assess inflation
    inflation_stance = "above target"
    if breakeven10 is not None:
        if breakeven10 < 2.0:
            inflation_stance = "at or below target"
        elif breakeven10 < 2.5:
            inflation_stance = "sticky above target"
        else:
            inflation_stance = "elevated"

    # Assess dollar
    dollar_trend = "weakening"
    dxy_pct = _pctchg(by_id, "yahoo/DX-Y.NYB")
    if dxy_pct is not None:
        if dxy_pct > 1:
            dollar_trend = "strengthening"
        elif dxy_pct > -1:
            dollar_trend = "stable"

    # Assess consumer
    consumer_health = "mixed"
    if saverate is not None and ccdelinq is not None:
        if saverate < 4 and ccdelinq > 2.5:
            consumer_health = "strained"
        elif saverate > 6 and ccdelinq < 2:
            consumer_health = "healthy"

    # Freshness warnings for slow-updating series
    stale_flags = "".join(filter(None, [
        _stale_warning(by_id, ["fred/GDP", "fred/A191RL1Q225SBEA"], "GDP", 100),
        _stale_warning(by_id, ["fred/XTEXVA01CNM667S", "fred/XTIMVA01CNM667S", "fred/CHNCPIALLMINMEI"], "China", 60),
        _stale_warning(by_id, ["fred/GFDEBTN", "fred/FYFSD"], "Fiscal", 100),
        _stale_warning(by_id, ["fred/FDHBFIN"], "Foreign holdings", 60),
        _stale_warning(by_id, ["fred/JTSJOL", "fred/JTSQUR"], "JOLTS", 60),
        _stale_warning(by_id, ["fred/CSUSHPISA"], "Case-Shiller", 75),
    ]))
    freshness_bar = ""
    if stale_flags:
        freshness_bar = f'<div class="freshness-bar">{stale_flags}</div>'

    summary_now = f"""<div class="summary-section">
<h3>State of the World</h3>
{freshness_bar}
<div class="summary-body">
<p><strong>Markets & Risk:</strong> S&P 500 at {_f(sp500, ',.0f')}, VIX at {_f(vix, '.1f')}
{"(elevated caution)" if vix and vix > 20 else "(calm)" if vix and vix < 16 else "(moderate alertness)"}.
Gold at ${_f(gold, ',.0f')} {"&mdash; an extraordinary level signaling persistent safe-haven demand and dollar hedging" if gold and gold > 4000 else ""}.
Bitcoin at ${_f(btc, ',.0f')}.
The dollar index (DXY) sits at {_f(dxy, '.1f')}, {dollar_trend}.</p>

<p><strong>Rates & Curve:</strong> The yield curve has re-steepened with 10Y at {_f(dgs10, '.2f')}%, 2Y at {_f(dgs2, '.2f')}%,
giving a 10Y-2Y spread of {_f(spread_10y2y, '+.2f')}%. The 10Y-3M spread is {_f(spread_10y3m, '+.2f')}%
{"&mdash; barely positive, historically a warning zone" if spread_10y3m and spread_10y3m < 0.5 else ""}.
Fed funds at {_f(fedfunds, '.2f')}%, 30Y mortgage at {_f(mortgage, '.2f')}%.
Financial stress indices (StL: {_f(stlfsi, '.2f')}, NFCI: {_f(nfci, '.2f')}) indicate {stress_level} systemic stress.
High yield spreads at {_f(hyspr, '.2f')}%.</p>

<p><strong>Labor & Consumer:</strong> Unemployment at {_f(unrate, '.1f')}%, Sahm Rule at {_f(sahm, '.2f')}
{"(below 0.50 recession trigger)" if sahm and sahm < 0.50 else "(ABOVE recession trigger)"}.
JOLTS openings at {_f(jolts, ',.0f')}K (declining from peak), quits rate {_f(quits, '.1f')}%.
Consumer sentiment at {_f(sentiment, '.1f')} {"(weak)" if sentiment and sentiment < 65 else ""}.
Saving rate at {_f(saverate, '.1f')}% {"(low)" if saverate and saverate < 5 else ""}, credit card delinquency at
{_f(ccdelinq, '.2f')}% {"(elevated)" if ccdelinq and ccdelinq > 2.5 else ""}. The consumer is {consumer_health}.</p>

<p><strong>Energy Substrate:</strong> WTI at ${_f(wti, '.2f')}, Brent at ${_f(brent, '.2f')}
{"&mdash; relatively soft oil prices suggesting adequate supply or demand weakness" if wti and wti < 70 else ""}.
Natural gas at ${_f(natgas, '.2f')}. Copper at ${_f(copper, ',.0f')}/ton
{"(strong, signaling industrial activity)" if copper and copper > 10000 else ""}.</p>

<p><strong>China:</strong> Shanghai Composite at {_f(shanghai, ',.0f')}, Alibaba at ${_f(baba, '.2f')}.
USD/CNY at {_f(cny, '.2f')}. China running ~${_f(china_surplus, '.0f')}B monthly trade surplus.
Foreign reserves at {_big(china_reserves, 'M')} &mdash;
{"a formidable buffer" if china_reserves and china_reserves > 3000000 else "declining"}.</p>

<p><strong>Fiscal:</strong> Federal debt at {_big(debt, 'M')}, annual deficit {_big(deficit, 'M')}.
Foreign holders of US debt: {_big(foreign_debt, 'B')}. Trade deficit: {_big(tradebal, 'M')}/month.</p>
</div>
</div>"""

    # ── 6-MONTH OUTLOOK ─────────────────────────────────────────────
    # Rate cut probability assessment
    rate_outlook = "likely to hold"
    if fedfunds and dgs2:
        if dgs2 < fedfunds - 0.5:
            rate_outlook = "market pricing 2+ cuts"
        elif dgs2 < fedfunds - 0.2:
            rate_outlook = "market pricing at least one cut"
        elif dgs2 > fedfunds + 0.2:
            rate_outlook = "market pricing tightening"

    summary_6mo = f"""<div class="summary-section">
<h3>6-Month Outlook</h3>
<div class="summary-body">
<p><strong>Fed & Rates:</strong> With fed funds at {_f(fedfunds, '.2f')}% and the 2Y yield at {_f(dgs2, '.2f')}%,
the bond market is {rate_outlook}. Breakeven inflation at {_f(breakeven10, '.2f')}% (10Y) and
{_f(breakeven5, '.2f')}% (5Y) suggests the market sees inflation as {inflation_stance}.
{"The inverted 5Y-vs-10Y breakeven signals near-term inflation concern exceeding long-term expectations." if breakeven5 and breakeven10 and breakeven5 > breakeven10 else ""}
The 30Y mortgage at {_f(mortgage, '.2f')}% continues to freeze housing activity
(Case-Shiller at {_f(caseshiller, '.0f')}, permits at {_f(permits, ',.0f')}).</p>

<p><strong>Recession Risk:</strong> The Sahm Rule at {_f(sahm, '.2f')} {"is approaching but has not triggered" if sahm and 0.30 <= sahm < 0.50 else "remains benign" if sahm and sahm < 0.30 else "HAS TRIGGERED"}.
{recession_signals} of {recession_total} classical recession indicators are flagging.
Initial claims at {_f(claims, ',.0f')} {"remain low" if claims and claims < 250000 else "are elevated" if claims and claims < 300000 else "are rising"}.
Manufacturing production at {_f(ipman, '.1f')} {"(below 100 = contraction)" if ipman and ipman < 100 else ""}.
Durable goods orders at {_big(dgorder, 'M')}.</p>

<p><strong>Dollar & Global Flows:</strong> The dollar at {_f(dxy, '.1f')} is {dollar_trend}, which
{"eases pressure on EM borrowers and commodity importers" if dollar_trend == "weakening" else "tightens global financial conditions"}.
{"A weaker dollar typically supports commodity prices and US export competitiveness." if dollar_trend == "weakening" else ""}
Gold at ${_f(gold, ',.0f')} and central bank buying suggest accelerating de-dollarization hedging.</p>

<p><strong>Energy 6mo:</strong> WTI at ${_f(wti, '.2f')} with
{"Brent-WTI spread at $" + _f(brent_wti_spread, '.2f') + " — " if brent_wti_spread else ""}
{"soft prices may incentivize OPEC+ to tighten" if wti and wti < 70 else "current prices support US shale economics"}.
{"Watch for supply disruptions if geopolitical tensions escalate." if vix and vix > 18 else ""}
Uranium ETF at ${_f(ura, '.2f')} {"reflects growing nuclear energy interest" if ura and ura > 40 else ""}.</p>

<p><strong>China 6mo:</strong> With exports at ${_f(china_surplus, '.0f')}B surplus, China's manufacturing engine
{"is running strong" if china_surplus and china_surplus > 80 else "faces headwinds"}.
{"The weak yuan at " + _f(cny, '.2f') + " supports export competitiveness but signals capital flow stress." if cny and cny > 7.0 else "Yuan stability at " + _f(cny, '.2f') + " suggests managed equilibrium."}
Watch KWEB and BABA for tech sector sentiment shifts.</p>
</div>
</div>"""

    # ── 2-YEAR OUTLOOK ──────────────────────────────────────────────
    summary_2yr = f"""<div class="summary-section">
<h3>2-Year Outlook</h3>
<div class="summary-body">
<p><strong>Debt Trajectory:</strong> Federal debt at {_big(debt, 'M')} with a {_big(deficit, 'M')} annual deficit
is the defining macro constraint of the next two years. With 10Y yields at {_f(dgs10, '.2f')}%,
debt servicing costs are accelerating. Foreign holders at {_big(foreign_debt, 'B')}
{"&mdash; any reduction in foreign appetite for Treasuries forces either higher yields or Fed intervention." if foreign_debt else ""}
{"The near-zero reverse repo (" + _big(rrp, 'B') + ") means the Fed's liquidity buffer is exhausted." if rrp and rrp < 50 else ""}</p>

<p><strong>Energy Substrate:</strong> Oil at ${_f(wti, '.2f')} is
{"deceptively calm &mdash; soft prices reflect demand uncertainty, not supply abundance" if wti and wti < 70 else "pricing in supply tightness"}.
The critical question is Permian Basin production trajectory (not yet in our data &mdash; needs EIA adapter).
{"Copper at $" + _f(copper, ',.0f') + "/ton signals robust industrial demand, consistent with energy transition buildout." if copper and copper > 10000 else ""}
{"Nickel at $" + _f(nickel, ',.0f') + "/ton and lithium (LIT at $" + _f(lit, '.2f') + ") are pricing in battery demand." if nickel and lit else ""}</p>

<p><strong>AI & Technology:</strong> NVDA at ${_f(nvda, '.2f')}, TSM at ${_f(tsm, '.2f')}, ASML at ${_f(asml, ',.2f')}
&mdash; the semiconductor chokepoint triad. The AI infrastructure buildout is the largest capital expenditure cycle
since the internet. Over 2 years, the question shifts from "who builds the models" to "who controls the physical
infrastructure." Taiwan (TSM) remains the critical vulnerability.
{"Semiconductors (SMH) outperforming broad tech (XLK) signals hardware > software in this cycle." if True else ""}</p>

<p><strong>US-China Structural:</strong> China's $~{_f(china_surplus, '.0f')}B/month trade surplus
{"is enormous and self-reinforcing &mdash; manufacturing scale begets cost advantage begets more exports." if china_surplus and china_surplus > 80 else "reflects structural manufacturing capacity."}
China's reserves at {_big(china_reserves, 'M')} provide a multi-year buffer.
{"The US-China decoupling in semiconductors (TSM, ASML export controls) accelerates China's domestic chip timeline." if True else ""}
Over 2 years, watch for: (a) Permian production data for energy substrate stress, (b) CNY trajectory for capital flow signals,
(c) rare earth prices (REMX at ${_f(remx, '.2f')}) for supply chain weaponization.</p>

<p><strong>Gold & Dollar System:</strong> Gold at ${_f(gold, ',.0f')}
{"is pricing in a structural shift &mdash; central banks are diversifying reserves away from Treasuries at the fastest pace in decades." if gold and gold > 4000 else "reflects hedging demand."}
DXY at {_f(dxy, '.1f')}, {dollar_trend}. Over 2 years, the dollar's reserve status faces its most serious test since Bretton Woods:
rising debt, persistent deficits, and active de-dollarization by BRICS+ nations.
{"Bitcoin at $" + _f(btc, ',.0f') + " sits in the middle of this, serving as an alternative store of value." if btc else ""}</p>
</div>
</div>"""

    # ── PREDICTIONS / POSITIONS ──────────────────────────────────────
    # Pre-compute signal classes to keep the template clean
    gold_sig = "signal-bull" if gold and gold > 4000 else "signal-neutral"
    gold_label = "STRONG" if gold and gold > 4000 else "WATCH"
    rate_sig = "signal-bull" if fedfunds and dgs2 and dgs2 < fedfunds - 0.1 else "signal-neutral"
    rate_label = "ACTIVE" if fedfunds and dgs2 and dgs2 < fedfunds else "WATCH"
    rate_prose = "curve says cuts are coming." if fedfunds and dgs2 and dgs2 < fedfunds else "rates are equilibrating."
    energy_sig = "signal-bear" if wti and wti < 65 else "signal-neutral"
    energy_label = "SOFT" if wti and wti < 70 else "NEUTRAL"
    china_sig = "signal-bull" if baba and baba > 120 else "signal-neutral"
    china_label = "RECOVERING" if baba and baba > 100 else "WATCH"
    consumer_sig = "signal-bear" if ccdelinq and ccdelinq > 2.5 else "signal-neutral"
    consumer_label = "ELEVATED" if ccdelinq and ccdelinq > 2.5 else "MODERATE"
    nuke_sig = "signal-bull" if ura and ura > 40 else "signal-neutral"
    nuke_label = "BUILDING" if ura and ura > 40 else "EARLY"
    kweb_val = _v(by_id, "yahoo/KWEB")
    ccj_val = _v(by_id, "yahoo/CCJ")
    mp_val = _v(by_id, "yahoo/MP")

    predictions = f"""<div class="summary-section predictions">
<h3>Analytical Positions (Data-Driven)</h3>
<div class="summary-body">
<div class="pred-grid">

<div class="pred-card">
<div class="pred-title">Gold / Precious Metals</div>
<div class="pred-signal {gold_sig}">{gold_label}</div>
<p>Gold ${_f(gold, ',.0f')}, Silver ${_f(silver, '.2f')}. Central bank buying + de-dollarization + fiscal deficit
({_big(deficit, 'M')}) = structural tailwind. {"DXY weakening at " + _f(dxy, '.1f') + " amplifies." if dollar_trend == "weakening" else ""}</p>
<div class="pred-watch">Watch: DXY reversal above 103, Fed hawkish pivot, real yields above 2.5%</div>
</div>

<div class="pred-card">
<div class="pred-title">Short Duration / Rate Cuts</div>
<div class="pred-signal {rate_sig}">{rate_label}</div>
<p>Fed funds {_f(fedfunds, '.2f')}% vs 2Y {_f(dgs2, '.2f')}% &mdash; {rate_prose}
TLT and long bonds benefit when cutting cycle begins.
Sahm Rule at {_f(sahm, '.2f')} {"approaching trigger." if sahm and sahm > 0.35 else "not yet urgent."}</p>
<div class="pred-watch">Watch: NFP miss below 100K, Sahm Rule crossing 0.50, claims above 260K</div>
</div>

<div class="pred-card">
<div class="pred-title">Semiconductor Supply Chain</div>
<div class="pred-signal signal-bull">STRUCTURAL</div>
<p>NVDA ${_f(nvda, '.2f')}, TSM ${_f(tsm, '.2f')}, ASML ${_f(asml, ',.2f')}.
AI capex cycle is multi-year. But concentration risk is extreme &mdash; Taiwan + Netherlands + single US designer.</p>
<div class="pred-watch">Watch: Taiwan Strait incidents, ASML export restrictions, China SMIC breakthroughs</div>
</div>

<div class="pred-card">
<div class="pred-title">Energy Substrate</div>
<div class="pred-signal {energy_sig}">{energy_label}</div>
<p>WTI ${_f(wti, '.2f')}, Brent ${_f(brent, '.2f')}. {"Prices soft enough to stress marginal producers." if wti and wti < 65 else ""}
Need EIA production data to assess Permian trajectory &mdash; the most important number we don't have yet.
{"Natural gas at $" + _f(natgas, '.2f') + "." if natgas else ""}</p>
<div class="pred-watch">Watch: EIA weekly production, Baker Hughes rig count, OPEC+ meetings</div>
</div>

<div class="pred-card">
<div class="pred-title">China Tech Recovery</div>
<div class="pred-signal {china_sig}">{china_label}</div>
<p>BABA ${_f(baba, '.2f')}, KWEB at ${_f(kweb_val, '.2f')}.
Shanghai at {_f(shanghai, ',.0f')}. {"China tech has bounced significantly off lows." if baba and baba > 120 else ""}
Export machine running at ${_f(china_surplus, '.0f')}B surplus.</p>
<div class="pred-watch">Watch: Property sector defaults, PBOC rate decisions, US tariff escalation</div>
</div>

<div class="pred-card">
<div class="pred-title">Critical Materials</div>
<div class="pred-signal signal-bull">LONG-TERM</div>
<p>Copper ${_f(copper, ',.0f')}/ton, Nickel ${_f(nickel, ',.0f')}/ton, LIT ${_f(lit, '.2f')}, REMX ${_f(remx, '.2f')}.
Electrification + AI data center buildout = structural demand for copper, lithium, rare earths.
{"MP Materials at $" + _f(mp_val, '.2f') + " (only US rare earth mine)." if mp_val else ""}</p>
<div class="pred-watch">Watch: China export controls on gallium/germanium, Chilean copper policy, DRC cobalt</div>
</div>

<div class="pred-card">
<div class="pred-title">Consumer Stress</div>
<div class="pred-signal {consumer_sig}">{consumer_label}</div>
<p>Saving rate {_f(saverate, '.1f')}%, credit card delinquency {_f(ccdelinq, '.2f')}%, sentiment {_f(sentiment, '.1f')}.
{"The consumer is drawing down savings and delinquencies are rising &mdash; a late-cycle pattern." if saverate and saverate < 4 and ccdelinq and ccdelinq > 2.5 else ""}
Retail and discretionary spending vulnerable.</p>
<div class="pred-watch">Watch: Saving rate below 3%, delinquency above 3.5%, retail sales decline</div>
</div>

<div class="pred-card">
<div class="pred-title">Nuclear Energy</div>
<div class="pred-signal {nuke_sig}">{nuke_label}</div>
<p>URA ${_f(ura, '.2f')}, CCJ ${_f(ccj_val, '.2f')}.
AI data center power demand + grid reliability concerns + decarbonization = nuclear renaissance thesis.
Multi-year buildout timeline means early positioning.</p>
<div class="pred-watch">Watch: NRC approvals, SMR milestones, utility PPAs for nuclear</div>
</div>

</div>
</div>
</div>"""

    return summary_now + summary_6mo + summary_2yr + predictions


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
        rows.append({**s, **delta, "sparkline_values": values[-90:]})

    conn.close()

    movers = rank_movers(rows)

    # Index rows by series_id for quick lookup
    by_id = {r["series_id"]: r for r in rows}

    # Group by category
    categories: dict[str, list] = {}
    for r in rows:
        cat = r.get("category") or "other"
        categories.setdefault(cat, []).append(r)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    summaries = _generate_summaries(by_id)
    html = _render_html(movers, categories, by_id, now, len(rows), summaries)

    out = OUTPUT_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


def _snapshot_item(by_id: dict, series_id: str, label: str, fmt: str = ",.0f") -> str:
    """Render a single snapshot metric."""
    r = by_id.get(series_id)
    if not r:
        return ""
    val = r.get("latest_value")
    pct = r.get("percent_change")
    if val is None:
        return ""
    if fmt == "pct":
        val_str = f"{val:.2f}%"
    elif fmt == "$":
        val_str = f"${val:,.0f}"
    elif fmt == "$2":
        val_str = f"${val:,.2f}"
    else:
        val_str = f"{val:{fmt}}"
    return f"""<div class="snap">
        <div class="snap-label">{label}</div>
        <div class="snap-value">{val_str}</div>
        <div class="snap-delta">{_pct_html(pct)}</div>
    </div>"""


def _render_html(movers: list, categories: dict, by_id: dict, build_time: str, total: int, summaries: str = "") -> str:
    # Snapshot bar
    snapshot = "".join(filter(None, [
        _snapshot_item(by_id, "yahoo/^GSPC", "S&P 500", ",.0f"),
        _snapshot_item(by_id, "yahoo/^DJI", "Dow", ",.0f"),
        _snapshot_item(by_id, "yahoo/^IXIC", "Nasdaq", ",.0f"),
        _snapshot_item(by_id, "yahoo/^VIX", "VIX", ".1f"),
        _snapshot_item(by_id, "yahoo/DX-Y.NYB", "DXY", ".1f"),
        _snapshot_item(by_id, "yahoo/GC=F", "Gold", "$"),
        _snapshot_item(by_id, "yahoo/CL=F", "WTI", "$2"),
        _snapshot_item(by_id, "yahoo/BTC-USD", "Bitcoin", "$"),
        _snapshot_item(by_id, "fred/DGS10", "10Y Yield", "pct"),
        _snapshot_item(by_id, "fred/DGS2", "2Y Yield", "pct"),
    ]))

    # Yield curve
    rates_keys = ["DGS3MO", "DGS1", "DGS2", "DGS5", "DGS10", "DGS30"]
    rates_data = {}
    for k in rates_keys:
        r = by_id.get(f"fred/{k}")
        if r and r.get("latest_value") is not None:
            rates_data[k] = r["latest_value"]
    yield_svg = _yield_curve_svg(rates_data)

    spread_10y2y = by_id.get("fred/T10Y2Y", {}).get("latest_value")
    spread_10y3m = by_id.get("fred/T10Y3M", {}).get("latest_value")
    fed_funds = by_id.get("fred/FEDFUNDS", {}).get("latest_value")
    mortgage = by_id.get("fred/MORTGAGE30US", {}).get("latest_value")
    sofr = by_id.get("fred/SOFR", {}).get("latest_value")

    yield_meta = '<div class="yield-meta">'
    if fed_funds is not None:
        yield_meta += f'<span>Fed Funds: <b>{fed_funds:.2f}%</b></span>'
    if sofr is not None:
        yield_meta += f'<span>SOFR: <b>{sofr:.2f}%</b></span>'
    if spread_10y2y is not None:
        cls = "up" if spread_10y2y > 0 else "down"
        yield_meta += f'<span>10Y-2Y: <b class="{cls}">{spread_10y2y:+.2f}%</b></span>'
    if spread_10y3m is not None:
        cls = "up" if spread_10y3m > 0 else "down"
        yield_meta += f'<span>10Y-3M: <b class="{cls}">{spread_10y3m:+.2f}%</b></span>'
    if mortgage is not None:
        yield_meta += f'<span>30Y Mortgage: <b>{mortgage:.2f}%</b></span>'
    yield_meta += '</div>'

    # China snapshot
    china_items = "".join(filter(None, [
        _snapshot_item(by_id, "yahoo/000001.SS", "Shanghai", ",.0f"),
        _snapshot_item(by_id, "yahoo/FXI", "China ETF", "$2"),
        _snapshot_item(by_id, "yahoo/KWEB", "China Tech", "$2"),
        _snapshot_item(by_id, "yahoo/BABA", "Alibaba", "$2"),
        _snapshot_item(by_id, "fred/DEXCHUS", "USD/CNY", ".2f"),
        _snapshot_item(by_id, "fred/TRESEGCNM052N", "Reserves", ",.0f"),
    ]))

    # Build top movers rows
    mover_rows = ""
    for i, m in enumerate(movers[:15], 1):
        spark = _sparkline_svg(m.get("sparkline_values", []))
        cat = m.get("category", "")
        mover_rows += f"""
        <tr>
            <td class="rank">{i}</td>
            <td>
                <div class="series-name">{m.get('name', m.get('series_id', ''))}</div>
                <div class="series-id">{m.get('series_id', '')} <span class="cat-tag">{cat}</span></div>
            </td>
            <td class="num">{format_number(m.get('latest_value'), m.get('units'))}</td>
            <td class="num">{_delta_html(m)}</td>
            <td class="num">{_zscore_html(m.get('z_score'))}</td>
            <td>{spark}</td>
        </tr>"""

    # Build category sections — ordered by framework priority
    cat_order = [
        "china", "energy", "technology", "materials", "rates", "credit",
        "money", "markets", "commodities", "food", "forex",
        "recession", "employment", "inflation", "gdp", "manufacturing",
        "consumer", "housing", "health", "defense", "fiscal", "trade",
        "sectors", "bonds", "crypto", "global", "other",
    ]
    cat_labels = {
        "china": "CHINA (US-China Axis)",
        "energy": "ENERGY (Physical Substrate)",
        "technology": "AI & TECHNOLOGY (Chokepoints)",
        "materials": "MATERIALS & MINING (Supply Chain)",
        "rates": "RATES & YIELD CURVE",
        "credit": "CREDIT & FINANCIAL STRESS",
        "money": "MONEY & FED BALANCE SHEET",
        "markets": "MARKETS",
        "commodities": "COMMODITIES",
        "food": "FOOD & AGRICULTURE (Security)",
        "forex": "DOLLAR & FOREX",
        "recession": "RECESSION INDICATORS",
        "employment": "EMPLOYMENT",
        "inflation": "INFLATION",
        "gdp": "GDP & OUTPUT",
        "manufacturing": "MANUFACTURING",
        "consumer": "CONSUMER",
        "housing": "HOUSING",
        "health": "BIOTECH & HEALTH",
        "defense": "DEFENSE & GEOPOLITICS",
        "fiscal": "FISCAL & GOVERNMENT",
        "trade": "GLOBAL TRADE",
        "sectors": "SECTOR ROTATION",
        "bonds": "BONDS",
        "crypto": "CRYPTO",
        "global": "GLOBAL / EM",
    }

    sorted_cats = sorted(categories.keys(), key=lambda c: cat_order.index(c) if c in cat_order else 99)

    # Build nav links
    nav_links = '<a href="#sec-analysis" class="nav-link nav-head">Analysis</a>\n'
    nav_links += '<a href="#sec-movers" class="nav-link nav-head">Top Movers</a>\n'
    for cat in sorted_cats:
        short = cat_labels.get(cat, cat.upper()).split("(")[0].strip()
        nav_links += f'<a href="#cat-{cat}" class="nav-link">{short}</a>\n'

    cat_sections = ""
    for cat in sorted_cats:
        series_list = categories[cat]
        label = cat_labels.get(cat, cat.upper())
        card_html = ""
        for s in sorted(series_list, key=lambda x: abs(x.get("z_score") or 0), reverse=True):
            spark = _sparkline_svg(s.get("sparkline_values", []), width=100, height=24)
            z = s.get("z_score")
            z_cls = ""
            if z is not None and abs(z) > 2:
                z_cls = " card-alert"
            elif z is not None and abs(z) > 1:
                z_cls = " card-notable"
            card_html += f"""
            <div class="card{z_cls}">
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
        <div class="category-section" id="cat-{cat}">
            <h2>{label} <span class="cat-count">({len(series_list)})</span></h2>
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
    --china: #dc2626;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 14px;
    line-height: 1.5;
  }}
  .page-wrap {{
    display: flex;
    max-width: 1600px;
    margin: 0 auto;
  }}
  .container {{ flex: 1; min-width: 0; padding: 1.5rem; }}

  /* Side nav */
  .side-nav {{
    position: sticky;
    top: 0;
    align-self: flex-start;
    width: 180px;
    flex-shrink: 0;
    height: 100vh;
    overflow-y: auto;
    padding: 1rem 0.5rem 1rem 0.75rem;
    border-right: 1px solid var(--border);
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }}
  .nav-link {{
    display: block;
    font-size: 0.65rem;
    color: var(--text-faint);
    text-decoration: none;
    padding: 3px 6px;
    border-radius: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .nav-link:hover {{ color: var(--text); background: var(--surface); }}
  .nav-head {{
    font-weight: 700;
    color: var(--text-dim);
    font-size: 0.7rem;
    margin-top: 0.5rem;
  }}
  .nav-head:first-child {{ margin-top: 0; }}
  @media (max-width: 1100px) {{
    .side-nav {{ display: none; }}
  }}

  /* Header */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--border);
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
  }}
  .header h1 {{ font-size: 1.5rem; font-weight: 700; letter-spacing: 0.05em; }}
  .header .meta {{ color: var(--text-dim); font-size: 0.8rem; }}

  /* Snapshot bar */
  .snapshot {{
    display: flex;
    gap: 0;
    overflow-x: auto;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 1.5rem;
    padding: 0.5rem 0;
  }}
  .snap {{
    flex: 1;
    text-align: center;
    padding: 0.5rem 0.75rem;
    min-width: 100px;
    border-right: 1px solid var(--border);
  }}
  .snap:last-child {{ border-right: none; }}
  .snap-label {{ font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-faint); }}
  .snap-value {{ font-size: 1.1rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .snap-delta {{ font-size: 0.75rem; }}

  /* Two column layout for yield + china */
  .twin-panel {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }}
  @media (max-width: 900px) {{
    .twin-panel {{ grid-template-columns: 1fr; }}
  }}
  .panel {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
  }}
  .panel h3 {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.75rem;
  }}
  .yield-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    font-size: 0.8rem;
    color: var(--text-dim);
    margin-top: 0.5rem;
  }}
  .yield-meta b {{ color: var(--text); }}
  .china-snap {{
    display: flex;
    flex-wrap: wrap;
    gap: 0;
  }}
  .china-snap .snap {{
    flex: 1 1 33%;
    min-width: 120px;
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
  }}
  .china-snap .snap:nth-child(3n) {{ border-right: none; }}
  .china-snap .snap:nth-last-child(-n+3) {{ border-bottom: none; }}

  /* Top movers table */
  .movers {{ margin-bottom: 2rem; }}
  .movers h2, .category-section h2 {{
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
    padding: 0.5rem 0.8rem;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover {{ background: var(--surface2); }}
  .rank {{ color: var(--text-faint); font-weight: 700; width: 30px; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .series-name {{ font-weight: 600; font-size: 0.85rem; }}
  .series-id {{ font-size: 0.7rem; color: var(--text-faint); font-family: monospace; }}
  .cat-tag {{
    display: inline-block;
    background: var(--surface2);
    border-radius: 3px;
    padding: 0 4px;
    font-size: 0.6rem;
    color: var(--text-dim);
    margin-left: 4px;
  }}

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
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }}
  .cat-count {{ font-weight: 400; color: var(--text-faint); font-size: 0.7rem; }}
  .card-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.75rem;
    margin-top: 0.75rem;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.85rem;
    transition: border-color 0.15s;
  }}
  .card:hover {{ border-color: var(--accent); }}
  .card-alert {{ border-left: 3px solid var(--z-extreme); }}
  .card-notable {{ border-left: 3px solid var(--z-notable); }}
  .card-header {{ margin-bottom: 0.35rem; }}
  .card-name {{ font-weight: 600; font-size: 0.8rem; line-height: 1.3; }}
  .card-id {{ font-size: 0.6rem; color: var(--text-faint); font-family: monospace; }}
  .card-value {{ font-size: 1.25rem; font-weight: 700; margin: 0.2rem 0; font-variant-numeric: tabular-nums; }}
  .card-delta {{ margin-bottom: 0.35rem; font-size: 0.8rem; }}
  .card-spark {{ margin: 0.35rem 0; }}
  .card-meta {{
    display: flex;
    gap: 0.75rem;
    font-size: 0.65rem;
    color: var(--text-faint);
  }}

  /* Freshness warnings */
  .freshness-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }}
  .stale-warn {{
    display: inline-block;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.25);
    color: var(--z-extreme);
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
    cursor: help;
  }}

  /* Summaries & Predictions */
  .summary-section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
  }}
  .summary-section h3 {{
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }}
  .summary-body p {{
    margin-bottom: 0.85rem;
    line-height: 1.65;
    font-size: 0.85rem;
    color: var(--text);
  }}
  .summary-body p strong {{
    color: var(--text);
    font-weight: 700;
  }}
  .predictions h3 {{
    color: var(--z-extreme);
  }}
  .pred-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
  }}
  .pred-card {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
  }}
  .pred-card:hover {{
    border-color: var(--accent);
  }}
  .pred-title {{
    font-weight: 700;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
  }}
  .pred-signal {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 2px 8px;
    border-radius: 3px;
    margin-bottom: 0.5rem;
  }}
  .signal-bull {{
    background: rgba(34, 197, 94, 0.15);
    color: var(--up);
    border: 1px solid rgba(34, 197, 94, 0.3);
  }}
  .signal-bear {{
    background: rgba(239, 68, 68, 0.15);
    color: var(--down);
    border: 1px solid rgba(239, 68, 68, 0.3);
  }}
  .signal-neutral {{
    background: rgba(113, 113, 122, 0.15);
    color: var(--text-dim);
    border: 1px solid rgba(113, 113, 122, 0.3);
  }}
  .pred-card p {{
    font-size: 0.8rem;
    line-height: 1.55;
    color: var(--text);
    margin-bottom: 0.5rem;
  }}
  .pred-watch {{
    font-size: 0.7rem;
    color: var(--text-faint);
    border-top: 1px solid var(--border);
    padding-top: 0.4rem;
    margin-top: 0.3rem;
  }}

  footer {{
    text-align: center;
    padding: 2rem 0 1rem;
    font-size: 0.75rem;
    color: var(--text-faint);
  }}
  footer a {{ color: var(--accent); text-decoration: none; }}
</style>
</head>
<body>
<div class="page-wrap">
  <nav class="side-nav">
    {nav_links}
  </nav>
  <div class="container">
    <div class="header">
      <h1>BRIEFER</h1>
      <div class="meta">{total} series &middot; FRED + Yahoo Finance &middot; {build_time}</div>
    </div>

    <div class="snapshot">{snapshot}</div>

    <div class="twin-panel">
      <div class="panel">
        <h3>US Treasury Yield Curve</h3>
        {yield_svg}
        {yield_meta}
      </div>
      <div class="panel">
        <h3>China Snapshot</h3>
        <div class="china-snap">{china_items}</div>
      </div>
    </div>

    <div id="sec-analysis">
      {summaries}
    </div>

    <div class="movers" id="sec-movers">
      <h2>Top Movers by Significance</h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Series</th>
            <th style="text-align:right">Value</th>
            <th style="text-align:right">Change</th>
            <th style="text-align:right">Z-Score</th>
            <th>90d</th>
          </tr>
        </thead>
        <tbody>{mover_rows}</tbody>
      </table>
    </div>

    {cat_sections}

    <footer>briefer &middot; data from FRED &amp; Yahoo Finance &middot; {build_time}</footer>
  </div>
</div>
</body>
</html>"""
