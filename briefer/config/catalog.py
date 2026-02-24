"""Pre-configured series catalog — the default "interesting" series per source.

Organized by predictive function:
  - What signals recession timing?
  - What signals inflation persistence?
  - What signals energy supply stress?
  - What signals credit/financial stress?
  - What signals dollar trajectory?
  - What signals consumer health?
  - What prices hard assets for the portfolio?
"""

CATALOG: dict[str, dict[str, dict]] = {
    "fred": {

        # ── GDP & OUTPUT ─────────────────────────────────────────────────
        "GDP":            {"category": "gdp",       "name": "Gross Domestic Product"},
        "A191RL1Q225SBEA":{"category": "gdp",       "name": "Real GDP Growth Rate (quarterly)"},
        "INDPRO":         {"category": "gdp",       "name": "Industrial Production Index"},
        "TCU":            {"category": "gdp",       "name": "Capacity Utilization"},
        "CFNAI":          {"category": "gdp",       "name": "Chicago Fed National Activity Index"},

        # ── RECESSION INDICATORS ─────────────────────────────────────────
        "ICSA":           {"category": "recession",  "name": "Initial Jobless Claims (weekly)"},
        "CCSA":           {"category": "recession",  "name": "Continued Claims (weekly)"},
        "SAHMREALTIME":   {"category": "recession",  "name": "Sahm Rule Recession Indicator"},
        "T10Y3M":         {"category": "recession",  "name": "10Y-3M Treasury Spread"},
        "PERMIT":         {"category": "recession",  "name": "Building Permits (SAAR)"},
        "HOUST":          {"category": "recession",  "name": "Housing Starts (SAAR)"},
        "UMCSENT":        {"category": "recession",  "name": "Michigan Consumer Sentiment"},

        # ── EMPLOYMENT (DEEP) ────────────────────────────────────────────
        "UNRATE":         {"category": "employment", "name": "Unemployment Rate"},
        "PAYEMS":         {"category": "employment", "name": "Total Nonfarm Payrolls"},
        "JTSJOL":         {"category": "employment", "name": "JOLTS Job Openings"},
        "JTSQUR":         {"category": "employment", "name": "JOLTS Quits Rate"},
        "AWHMAN":         {"category": "employment", "name": "Avg Weekly Hours — Manufacturing"},
        "LNS12300060":    {"category": "employment", "name": "Employment-Population Ratio (25-54)"},
        "CIVPART":        {"category": "employment", "name": "Labor Force Participation Rate"},
        "CES0500000003":  {"category": "employment", "name": "Avg Hourly Earnings — Private"},

        # ── INFLATION (DEEP) ─────────────────────────────────────────────
        "CPIAUCSL":       {"category": "inflation",  "name": "CPI (All Urban, Seasonally Adj)"},
        "CPILFESL":       {"category": "inflation",  "name": "Core CPI (ex Food & Energy)"},
        "PCEPI":          {"category": "inflation",  "name": "PCE Price Index"},
        "PCEPILFE":       {"category": "inflation",  "name": "Core PCE (ex Food & Energy)"},
        "T10YIE":         {"category": "inflation",  "name": "10-Year Breakeven Inflation Rate"},
        "T5YIE":          {"category": "inflation",  "name": "5-Year Breakeven Inflation Rate"},
        "PPIACO":         {"category": "inflation",  "name": "PPI — All Commodities"},
        "CUUR0000SAF11":  {"category": "inflation",  "name": "CPI — Food at Home"},

        # ── RATES & YIELDS ───────────────────────────────────────────────
        "FEDFUNDS":       {"category": "rates",      "name": "Federal Funds Effective Rate"},
        "DGS10":          {"category": "rates",      "name": "10-Year Treasury Yield"},
        "DGS2":           {"category": "rates",      "name": "2-Year Treasury Yield"},
        "DGS30":          {"category": "rates",      "name": "30-Year Treasury Yield"},
        "T10Y2Y":         {"category": "rates",      "name": "10Y-2Y Treasury Spread"},
        "DFII10":         {"category": "rates",      "name": "10-Year Real Yield (TIPS)"},
        "MORTGAGE30US":   {"category": "rates",      "name": "30-Year Fixed Mortgage Rate"},

        # ── CREDIT & FINANCIAL STRESS ────────────────────────────────────
        "BAMLH0A0HYM2":  {"category": "credit",     "name": "High Yield Bond Spread (ICE BofA)"},
        "BAMLC0A4CBBB":  {"category": "credit",     "name": "BBB Corporate Bond Spread"},
        "STLFSI2":       {"category": "credit",     "name": "St. Louis Fed Financial Stress Index"},
        "TEDRATE":       {"category": "credit",     "name": "TED Spread (LIBOR-Tbill)"},
        "DRCCLACBS":     {"category": "credit",     "name": "Credit Card Delinquency Rate"},
        "DRSFRMACBS":    {"category": "credit",     "name": "Mortgage Delinquency Rate"},
        "BUSLOANS":      {"category": "credit",     "name": "Commercial & Industrial Loans"},
        "TOTALSL":       {"category": "credit",     "name": "Total Consumer Credit"},

        # ── MONEY & FED BALANCE SHEET ────────────────────────────────────
        "M2SL":          {"category": "money",      "name": "M2 Money Supply"},
        "M1SL":          {"category": "money",      "name": "M1 Money Supply"},
        "WALCL":         {"category": "money",      "name": "Fed Total Assets (Balance Sheet)"},
        "RRPONTSYD":     {"category": "money",      "name": "Overnight Reverse Repo (Daily)"},
        "WTREGEN":       {"category": "money",      "name": "Treasury General Account"},
        "M2V":           {"category": "money",      "name": "Velocity of M2 Money"},
        "BOGMBASE":      {"category": "money",      "name": "Monetary Base"},

        # ── DOLLAR & FOREX ───────────────────────────────────────────────
        "DTWEXBGS":      {"category": "forex",      "name": "Trade Weighted Dollar Index (Broad)"},
        "DEXUSEU":       {"category": "forex",      "name": "USD/EUR Exchange Rate"},
        "DEXCHUS":       {"category": "forex",      "name": "USD/CNY Exchange Rate"},
        "DEXJPUS":       {"category": "forex",      "name": "USD/JPY Exchange Rate"},

        # ── MARKETS ──────────────────────────────────────────────────────
        "SP500":         {"category": "markets",    "name": "S&P 500"},
        "VIXCLS":        {"category": "markets",    "name": "VIX Volatility Index"},
        "WILL5000PR":    {"category": "markets",    "name": "Wilshire 5000 (Total Market)"},
        "NASDAQCOM":     {"category": "markets",    "name": "Nasdaq Composite"},

        # ── ENERGY ───────────────────────────────────────────────────────
        "DCOILWTICO":    {"category": "energy",     "name": "WTI Crude Oil Price"},
        "DCOILBRENTEU":  {"category": "energy",     "name": "Brent Crude Oil Price"},
        "DHHNGSP":       {"category": "energy",     "name": "Henry Hub Natural Gas Spot Price"},
        "GASREGW":       {"category": "energy",     "name": "Regular Gasoline Price (Weekly)"},

        # ── COMMODITIES ──────────────────────────────────────────────────
        "GOLDPMGBD228NLBM":{"category": "commodities","name": "Gold Price (London PM Fix)"},
        "PCOPPUSDM":     {"category": "commodities", "name": "Global Copper Price"},
        "PSILVERUSDM":   {"category": "commodities", "name": "Global Silver Price"},
        "PWHEAMTUSDM":   {"category": "commodities", "name": "Global Wheat Price"},
        "PMAABORTSM":    {"category": "commodities", "name": "Global Coffee Price"},
        "WPU10170502":   {"category": "commodities", "name": "PPI — Lumber"},

        # ── HOUSING ──────────────────────────────────────────────────────
        "CSUSHPISA":     {"category": "housing",    "name": "Case-Shiller Home Price Index"},
        "MSACSR":        {"category": "housing",    "name": "Monthly Supply of New Houses"},
        "EXHOSLUSM495S": {"category": "housing",    "name": "Existing Home Sales"},
        "MSPUS":         {"category": "housing",    "name": "Median Home Sale Price"},

        # ── CONSUMER ─────────────────────────────────────────────────────
        "RSAFS":         {"category": "consumer",   "name": "Retail Sales (Total)"},
        "PSAVERT":       {"category": "consumer",   "name": "Personal Saving Rate"},
        "REVOLSL":       {"category": "consumer",   "name": "Revolving Consumer Credit (Credit Cards)"},
        "PCE":           {"category": "consumer",   "name": "Personal Consumption Expenditures"},

        # ── GLOBAL / TRADE ───────────────────────────────────────────────
        "BOPGSTB":       {"category": "trade",      "name": "US Trade Balance (Goods & Services)"},
        "IEABC":         {"category": "trade",      "name": "US Current Account Balance"},
        "IR3TIB01CNM156N":{"category": "trade",     "name": "China 3-Month Interbank Rate"},
    },

    "yahoo": {
        # ── INDICES ──────────────────────────────────────────────────────
        "^GSPC":    {"category": "markets",     "name": "S&P 500 (real-time)"},
        "^DJI":     {"category": "markets",     "name": "Dow Jones Industrial"},
        "^IXIC":    {"category": "markets",     "name": "Nasdaq Composite (real-time)"},
        "^RUT":     {"category": "markets",     "name": "Russell 2000 (Small Cap)"},
        "^VIX":     {"category": "markets",     "name": "VIX (real-time)"},

        # ── COMMODITIES ──────────────────────────────────────────────────
        "GC=F":     {"category": "commodities", "name": "Gold Futures"},
        "SI=F":     {"category": "commodities", "name": "Silver Futures"},
        "HG=F":     {"category": "commodities", "name": "Copper Futures"},
        "CL=F":     {"category": "commodities", "name": "WTI Crude Oil Futures"},
        "BZ=F":     {"category": "commodities", "name": "Brent Crude Oil Futures"},
        "NG=F":     {"category": "commodities", "name": "Natural Gas Futures"},
        "ZW=F":     {"category": "commodities", "name": "Wheat Futures"},
        "ZC=F":     {"category": "commodities", "name": "Corn Futures"},

        # ── FOREX ────────────────────────────────────────────────────────
        "EURUSD=X": {"category": "forex",       "name": "EUR/USD"},
        "CNY=X":    {"category": "forex",       "name": "USD/CNY"},
        "JPY=X":    {"category": "forex",       "name": "USD/JPY"},
        "DX-Y.NYB": {"category": "forex",       "name": "US Dollar Index (DXY)"},

        # ── SECTOR ETFS (for sector rotation signals) ────────────────────
        "XLE":      {"category": "sectors",     "name": "Energy Select Sector SPDR"},
        "XLF":      {"category": "sectors",     "name": "Financial Select Sector SPDR"},
        "XLY":      {"category": "sectors",     "name": "Consumer Discretionary SPDR"},
        "XLP":      {"category": "sectors",     "name": "Consumer Staples SPDR"},
        "XLU":      {"category": "sectors",     "name": "Utilities SPDR"},

        # ── KEY INSTRUMENTS FROM THE BETS ────────────────────────────────
        "TLT":      {"category": "bonds",       "name": "20+ Year Treasury Bond ETF"},
        "TIP":      {"category": "bonds",       "name": "TIPS Bond ETF"},
        "HYG":      {"category": "credit",      "name": "iShares High Yield Corporate Bond ETF"},
        "GLD":      {"category": "commodities", "name": "SPDR Gold Trust"},
        "USO":      {"category": "energy",      "name": "United States Oil Fund"},
        "UNG":      {"category": "energy",      "name": "United States Natural Gas Fund"},
    },
}


def get_catalog_series(source: str) -> dict[str, dict]:
    """Return the catalog entries for a source, or empty dict."""
    return CATALOG.get(source, {})
