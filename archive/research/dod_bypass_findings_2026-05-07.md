# DoD Akamai Bypass — Findings (2026-05-07)

> Proved we can scrape war.gov and centcom.mil for free, from this
> residential IP, using curl_cffi's TLS impersonation. No paid proxy
> service needed.

---

## TL;DR

**Yes, free bypass works.** Use `curl_cffi` with `impersonate="chrome120"`
from a residential IP, with conservative rate limiting (90–180s between
requests per Akamai-protected domain).

The IP **is not perma-banned**. The earlier failure was session-level
flagging from rapid-succession requests in a previous session — it
cleared itself.

---

## What we proved

### 1. curl_cffi defeats Akamai TLS fingerprinting
All five test URLs returned **HTTP 200 with substantive content**:

| URL | Status | Bytes |
|---|---:|---:|
| `https://www.war.gov/` | 200 | 197,664 |
| `https://www.war.gov/News/` | 200 | 191,057 |
| `https://www.war.gov/News/News-Stories/Article/Article/4477864/.../project-freedom...` | 200 | 190,250 |
| `https://www.centcom.mil/MEDIA/PRESS-RELEASES/` | 200 | 68,517 |
| `https://www.centcom.mil/MEDIA/PRESS-RELEASES/Press-Release-View/.../project-freedom...` | 200 | 61,124 |

### 2. Article extraction works
The Project Freedom article (war.gov) extracted with full content:

- Title: *"'Project Freedom' Aims to Get Thousands of Commercial Ships Safely Through Strait of Hormuz"*
- Date: May 5, 2026
- Multiple substantive Hegseth quotes
- Operational details (MH-60 Sea Hawks, AH-64 Apaches, F-16s, 100+ aircraft)
- Pentagon briefing context, CENTCOM execution details
- 12+ "Project Freedom" mentions throughout body

This is exactly the operational detail we were missing. A real war brief day-of would now include things like:

> *"Project Freedom — defensive in nature, focused in scope, temporary in duration. Mission: protecting innocent commercial shipping from Iranian aggression."* — Sec. of War Pete Hegseth, May 5

### 3. Discovery API found
DoD sites use **DotNetNuke ArticleCS** module. The article list lives at:

```
/API/ArticleCS/Public/GetList?dpage=0&moduleID={MID}
```

Returns XML with full article metadata (title, URL, image, publish date) — no scraping the rendered DOM needed.

We confirmed `moduleID=1200` works (returns historic content), and identified `moduleID=2842` as the likely current war.gov News-Stories module (derived from Vue var name `storyListing2842_data` in the page HTML). A retry probe of 2842 timed out — likely Akamai rate-limiting after our many probes — but the discovery method is sound.

### 4. Article URL pattern
URLs follow:
```
https://www.war.gov/News/News-Stories/Article/Article/{article-id}/{slug}/
```

The API returns `article-url-or-link-absolute` directly so no construction needed.

---

## What's needed for production integration

### a. Settle moduleIDs (5 min once IP cools)
- war.gov news-stories: probably 2842 (need to confirm with retry)
- centcom.mil press releases: TBD — same probe technique

### b. Wire into `pipeline/scraper/discovery.py`
Add a discovery path that calls the ArticleCS GetList API directly when `extractor: "akamai"` is set in `sources.yaml`. The API returns the article URLs directly.

### c. Wire into `pipeline/scraper/extractor.py`
Add an `extractor: "akamai"` dispatch that calls `akamai_bypass.akamai_extract()`.

### d. Add `curl_cffi` to `pipeline/requirements.txt`
One line.

### e. Update `sources.yaml`
```yaml
- name: "DOD War.gov News"
  type: web_scrape
  url: "https://www.war.gov/News/News-Stories/"
  api_url: "https://www.war.gov/API/ArticleCS/Public/GetList?dpage=0&moduleID=2842"
  category: defense
  tier: 1
  extractor: akamai
  active: true

- name: "CENTCOM Press Releases"
  type: web_scrape
  url: "https://www.centcom.mil/MEDIA/PRESS-RELEASES/"
  api_url: "https://www.centcom.mil/API/ArticleCS/Public/GetList?dpage=0&moduleID={TBD}"
  category: defense
  tier: 1
  extractor: akamai
  active: true
```

### f. Rate-limit pacing
Already built into `akamai_bypass.py`:
- war.gov / www.war.gov: 90–180s between any requests
- centcom.mil / www.centcom.mil: 90–180s
- navy.mil: 60–120s (less strict — Akamai protection appears lighter)

For ~30 articles/day across both domains: ~75–150 minutes per source. Fits in a 4-6am cron window.

---

## Operational caveats

1. **Don't hammer the discovery API** — even though the bypass works, repeated rapid requests will trigger session flagging. The pacing in `akamai_bypass.py` is conservative on purpose.

2. **Cookies and TLS fingerprint must match Chrome exactly** — `chrome120` impersonation handles this. If Akamai updates their detection, we'd update the impersonate string (chrome121, etc.). curl_cffi tracks Chrome versions.

3. **Residential IP is load-bearing** — this works because we're coming from a home ISP, not a cloud datacenter. AWS/GCP IPs would still get blocked even with curl_cffi. The M4 mini at home is exactly the right deployment target.

4. **Graceful degradation** — if Akamai blocks for a session, the pipeline must continue with other sources. `akamai_fetch` returns `None` on block; the pipeline treats this as a failed source and proceeds.

5. **Daily failure budget** — expect ~5–15% of days where Akamai blocks unexpectedly. The brief still publishes; just without DoD content that day.

---

## What's in `pipeline/scraper/akamai_bypass.py`

A reusable module with:
- `akamai_fetch(url)` — curl_cffi GET with chrome120 impersonation + per-domain rate limiting
- `akamai_extract(url)` — fetch + extract article body via trafilatura → DoD-specific BS4 → generic BS4 fallback chain
- `akamai_discover_links(listing_url, link_pattern)` — for sources where the listing is plain HTML (CENTCOM may be — TBD)

Adding API-based discovery (`akamai_discover_via_api(api_url)`) is the next 30-line addition once we confirm moduleIDs.
