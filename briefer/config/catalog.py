"""Pre-configured series catalog — the default "interesting" series per source."""

CATALOG: dict[str, dict[str, dict]] = {
    "fred": {
        "GDP":       {"category": "gdp",        "name": "Gross Domestic Product"},
        "CPIAUCSL":  {"category": "inflation",   "name": "CPI (All Urban, Seasonally Adj)"},
        "UNRATE":    {"category": "employment",  "name": "Unemployment Rate"},
        "FEDFUNDS":  {"category": "rates",       "name": "Federal Funds Effective Rate"},
        "M2SL":      {"category": "money",       "name": "M2 Money Supply"},
        "T10Y2Y":    {"category": "rates",       "name": "10Y-2Y Treasury Spread"},
        "DGS10":     {"category": "rates",       "name": "10-Year Treasury Yield"},
        "DEXUSEU":   {"category": "forex",       "name": "USD/EUR Exchange Rate"},
        "PAYEMS":    {"category": "employment",  "name": "Total Nonfarm Payrolls"},
        "PCEPI":     {"category": "inflation",   "name": "PCE Price Index"},
        "DCOILWTICO":{"category": "energy",      "name": "WTI Crude Oil Price"},
        "DCOILBRENTEU":{"category": "energy",    "name": "Brent Crude Oil Price"},
        "GOLDAMGBD228NLBM": {"category": "commodities", "name": "Gold Price (London Fix)"},
        "VIXCLS":    {"category": "markets",     "name": "VIX Volatility Index"},
        "SP500":     {"category": "markets",     "name": "S&P 500"},
        "BAMLH0A0HYM2": {"category": "credit",  "name": "High Yield Bond Spread"},
    },
}


def get_catalog_series(source: str) -> dict[str, dict]:
    """Return the catalog entries for a source, or empty dict."""
    return CATALOG.get(source, {})
