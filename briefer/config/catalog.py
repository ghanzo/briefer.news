"""Pre-configured series catalog — the default "interesting" series per source.

Organized by predictive function (see COVERAGE.md for full rationale):
  - What signals recession timing?
  - What signals inflation persistence?
  - What signals energy supply stress?
  - What signals credit/financial stress?
  - What signals dollar trajectory?
  - What signals consumer health?
  - What prices hard assets for the portfolio?
  - What signals AI/tech acceleration?          [COVERAGE dim 2]
  - What signals materials/mining stress?       [COVERAGE dim 4]
  - What signals food/climate disruption?       [COVERAGE dim 6]
  - What signals geopolitical power shifts?     [COVERAGE dim 1]
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

        # ── RATES & YIELDS (full curve) ─────────────────────────────────
        "FEDFUNDS":       {"category": "rates",      "name": "Federal Funds Effective Rate"},
        "SOFR":           {"category": "rates",      "name": "Secured Overnight Financing Rate"},
        "DGS3MO":         {"category": "rates",      "name": "3-Month Treasury Yield"},
        "DGS1":           {"category": "rates",      "name": "1-Year Treasury Yield"},
        "DGS2":           {"category": "rates",      "name": "2-Year Treasury Yield"},
        "DGS5":           {"category": "rates",      "name": "5-Year Treasury Yield"},
        "DGS10":          {"category": "rates",      "name": "10-Year Treasury Yield"},
        "DGS30":          {"category": "rates",      "name": "30-Year Treasury Yield"},
        "T10Y2Y":         {"category": "rates",      "name": "10Y-2Y Treasury Spread"},
        "DFII10":         {"category": "rates",      "name": "10-Year Real Yield (TIPS)"},
        "MORTGAGE30US":   {"category": "rates",      "name": "30-Year Fixed Mortgage Rate"},

        # ── CREDIT & FINANCIAL STRESS ────────────────────────────────────
        "BAMLH0A0HYM2":  {"category": "credit",     "name": "High Yield Bond Spread (ICE BofA)"},
        "BAMLC0A4CBBB":  {"category": "credit",     "name": "BBB Corporate Bond Spread"},
        "STLFSI4":       {"category": "credit",     "name": "St. Louis Fed Financial Stress Index"},
        "NFCI":          {"category": "credit",     "name": "Chicago Fed National Financial Conditions"},
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
        "NASDAQCOM":     {"category": "markets",    "name": "Nasdaq Composite"},

        # ── ENERGY ───────────────────────────────────────────────────────
        "DCOILWTICO":    {"category": "energy",     "name": "WTI Crude Oil Price"},
        "DCOILBRENTEU":  {"category": "energy",     "name": "Brent Crude Oil Price"},
        "DHHNGSP":       {"category": "energy",     "name": "Henry Hub Natural Gas Spot Price"},
        "GASREGW":       {"category": "energy",     "name": "Regular Gasoline Price (Weekly)"},
        "IPG2211A2N":    {"category": "energy",     "name": "Electric Power Generation Index"},
        "MCOILWTICO":    {"category": "energy",     "name": "WTI Crude Oil (Monthly Avg)"},

        # ── COMMODITIES ──────────────────────────────────────────────────
        "PCOPPUSDM":     {"category": "commodities", "name": "Global Copper Price"},
        "PWHEAMTUSDM":   {"category": "commodities", "name": "Global Wheat Price"},
        "PCOFFOTMUSDM":  {"category": "commodities", "name": "Global Coffee Price (Arabica)"},
        "WPU10170502":   {"category": "commodities", "name": "PPI — Lumber"},
        "PNICKUSDM":     {"category": "commodities", "name": "Global Nickel Price"},
        "PIORECRUSDM":   {"category": "commodities", "name": "Global Iron Ore Price"},

        # ── FOOD & AGRICULTURE (climate/food security) ──────────────────
        "PFOODINDEXM":   {"category": "food",        "name": "IMF Global Food Price Index"},
        "PNRGINDEXM":    {"category": "food",        "name": "IMF Energy Price Index"},
        "PSOYBUSDM":     {"category": "food",        "name": "Global Soybean Price"},
        "PRICENPQUSDM":  {"category": "food",        "name": "Global Rice Price"},

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

        # ── MANUFACTURING ───────────────────────────────────────────────
        "IPMAN":         {"category": "manufacturing", "name": "Industrial Production: Manufacturing"},
        "AMTMNO":        {"category": "manufacturing", "name": "Manufacturers New Orders (Total)"},
        "DGORDER":       {"category": "manufacturing", "name": "Durable Goods Orders"},
        "NEWORDER":      {"category": "manufacturing", "name": "Manufacturers New Orders (Nondefense)"},

        # ── FISCAL & GOVERNMENT ─────────────────────────────────────────
        "GFDEBTN":       {"category": "fiscal",     "name": "Federal Debt: Total Public Debt"},
        "FYFSD":         {"category": "fiscal",     "name": "Federal Surplus or Deficit"},
        "FDHBFIN":       {"category": "fiscal",     "name": "Federal Debt Held by Foreign Investors"},

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
        "ZS=F":     {"category": "commodities", "name": "Soybean Futures"},

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

        # ── GLOBAL INDICES ──────────────────────────────────────────────
        "^FTSE":    {"category": "global",      "name": "FTSE 100 (UK)"},
        "^N225":    {"category": "global",      "name": "Nikkei 225 (Japan)"},
        "^HSI":     {"category": "global",      "name": "Hang Seng Index (HK/China)"},
        "^GDAXI":   {"category": "global",      "name": "DAX (Germany)"},

        # ── KEY INSTRUMENTS & ETFS ──────────────────────────────────────
        "TLT":      {"category": "bonds",       "name": "20+ Year Treasury Bond ETF"},
        "TIP":      {"category": "bonds",       "name": "TIPS Bond ETF"},
        "HYG":      {"category": "credit",      "name": "iShares High Yield Corporate Bond ETF"},
        "LQD":      {"category": "credit",      "name": "iShares Investment Grade Corp Bond ETF"},
        "GLD":      {"category": "commodities", "name": "SPDR Gold Trust"},
        "USO":      {"category": "energy",      "name": "United States Oil Fund"},
        "UNG":      {"category": "energy",      "name": "United States Natural Gas Fund"},

        # ── AI & TECH CHOKEPOINTS (COVERAGE dim 2) ──────────────────────
        "NVDA":     {"category": "technology",  "name": "Nvidia (AI compute demand)"},
        "TSM":      {"category": "technology",  "name": "TSMC (foundry chokepoint)"},
        "ASML":     {"category": "technology",  "name": "ASML (lithography monopoly)"},
        "MSFT":     {"category": "technology",  "name": "Microsoft (AI infrastructure)"},
        "GOOGL":    {"category": "technology",  "name": "Alphabet (AI infrastructure)"},
        "SMH":      {"category": "technology",  "name": "VanEck Semiconductor ETF"},
        "XLK":      {"category": "sectors",     "name": "Technology Select Sector SPDR"},

        # ── ENERGY TRANSITION (COVERAGE dim 3) ─────────────────────────
        "URA":      {"category": "energy",      "name": "Global X Uranium ETF"},
        "CCJ":      {"category": "energy",      "name": "Cameco (uranium producer)"},
        "TAN":      {"category": "energy",      "name": "Invesco Solar ETF"},
        "ICLN":     {"category": "energy",      "name": "iShares Global Clean Energy ETF"},

        # ── MATERIALS & MINING (COVERAGE dim 4) ────────────────────────
        "LIT":      {"category": "materials",   "name": "Global X Lithium & Battery ETF"},
        "REMX":     {"category": "materials",   "name": "VanEck Rare Earth/Strategic Metals ETF"},
        "MP":       {"category": "materials",   "name": "MP Materials (US rare earth mine)"},
        "ALB":      {"category": "materials",   "name": "Albemarle (lithium producer)"},
        "FCX":      {"category": "materials",   "name": "Freeport-McMoRan (copper/gold mining)"},
        "BHP":      {"category": "materials",   "name": "BHP Group (diversified mining)"},
        "VALE":     {"category": "materials",   "name": "Vale SA (nickel/iron ore mining)"},

        # ── FOOD & AGRICULTURE (COVERAGE dim 6) ────────────────────────
        "DBA":      {"category": "food",        "name": "Invesco DB Agriculture Fund"},
        "MOO":      {"category": "food",        "name": "VanEck Agribusiness ETF"},

        # ── BIOTECH & HEALTH (COVERAGE dim 7) ──────────────────────────
        "XBI":      {"category": "health",      "name": "SPDR S&P Biotech ETF"},
        "LLY":      {"category": "health",      "name": "Eli Lilly (GLP-1 leader)"},
        "NVO":      {"category": "health",      "name": "Novo Nordisk (GLP-1/obesity)"},

        # ── DEFENSE & GEOPOLITICS (COVERAGE dim 1) ─────────────────────
        "ITA":      {"category": "defense",     "name": "iShares US Aerospace & Defense ETF"},
        "LMT":      {"category": "defense",     "name": "Lockheed Martin"},

        # ── SECTOR ROTATION (remaining) ────────────────────────────────
        "XLI":      {"category": "sectors",     "name": "Industrial Select Sector SPDR"},
        "XLB":      {"category": "sectors",     "name": "Materials Select Sector SPDR"},
        "XLV":      {"category": "sectors",     "name": "Health Care Select Sector SPDR"},
        "XLRE":     {"category": "sectors",     "name": "Real Estate Select Sector SPDR"},

        # ── CRYPTO / ALTERNATIVE RAILS ─────────────────────────────────
        "BTC-USD":  {"category": "crypto",      "name": "Bitcoin (liquidity/risk proxy)"},
        "ETH-USD":  {"category": "crypto",      "name": "Ethereum"},

        # ── COUNTRY / EM PROXIES ────────────────────────────────────────
        "EEM":      {"category": "global",      "name": "iShares MSCI Emerging Markets ETF"},
        "FXI":      {"category": "global",      "name": "iShares China Large-Cap ETF"},
        "EWJ":      {"category": "global",      "name": "iShares MSCI Japan ETF"},
        "EWZ":      {"category": "global",      "name": "iShares MSCI Brazil ETF"},
        "INDA":     {"category": "global",      "name": "iShares MSCI India ETF"},
        "VNQ":      {"category": "sectors",     "name": "Vanguard Real Estate ETF"},
    },
}


def get_catalog_series(source: str) -> dict[str, dict]:
    """Return the catalog entries for a source, or empty dict."""
    return CATALOG.get(source, {})
