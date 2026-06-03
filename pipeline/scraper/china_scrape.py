"""
China-government source scraper.

Reads pipeline/config/china_sources.yaml. For each active source:
  1. Discover article URLs (listing page + link_pattern regex)
  2. For each new URL not already in DB:
     - Fetch via curl_cffi Chrome impersonation (proven path)
     - Extract content (trafilatura by default, or per-source custom selector)
     - Save to articles table with language='zh'
  3. Per-source retry logic for flaky sources (MIIT/CAC/CCDI/etc.)
  4. Rate-limited per domain (lighter pacing than Akamai — Chinese gov
     sites are flaky but not aggressively bot-blocking)

Usage:
    python -m scraper.china_scrape                    # all active sources
    python -m scraper.china_scrape --source mfa.gov.cn   # single source by domain
    python -m scraper.china_scrape --dry-run          # discover + extract but no DB writes
    python -m scraper.china_scrape --limit 5          # cap articles per source

Or via main.py:
    python main.py --china-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import yaml
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

import trafilatura

# Make pipeline package importable when run as -m or as script
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from db.models import (  # noqa: E402
    get_engine,
    get_session,
    Source,
    Article,
    ScrapeRun,
)

logger = logging.getLogger(__name__)


# ── Per-domain rate limiting (lighter than Akamai) ──────────────────────────
_DOMAIN_INTERVALS = {
    "default": (8.0, 20.0),       # most china gov sites
    "qstheory.cn": (10.0, 25.0),  # be polite to Party theoretical journal
    "ccdi.gov.cn": (10.0, 25.0),  # politically sensitive
}

_LAST_FETCH: dict[str, float] = {}


def _domain_of(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1) if m else "default"


def _wait_for_rate_limit(url: str) -> None:
    domain = _domain_of(url)
    # Strip leading www.
    keyed = domain.lstrip("www.").replace("www.", "")
    interval = _DOMAIN_INTERVALS.get(keyed, _DOMAIN_INTERVALS["default"])

    last = _LAST_FETCH.get(domain, 0.0)
    now = time.time()
    target = last + random.uniform(*interval)

    if now < target:
        wait = target - now
        logger.debug(f"china rate-limit pacing {domain}: waiting {wait:.1f}s")
        time.sleep(wait)

    _LAST_FETCH[domain] = time.time()


# ── Fetch with retry ────────────────────────────────────────────────────────

def china_fetch(url: str, impersonate: str = "chrome120", timeout: int = 30, retries: int = 1) -> Optional[str]:
    """Fetch URL with curl_cffi Chrome impersonation and per-domain rate limiting."""
    if not CURL_CFFI_AVAILABLE:
        logger.error("curl_cffi unavailable — cannot fetch china sources")
        return None

    _wait_for_rate_limit(url)

    backoff = 5
    for attempt in range(1, retries + 1):
        try:
            r = curl_requests.get(url, impersonate=impersonate, timeout=timeout)
            if r.status_code == 200 and len(r.text) > 200:
                return r.text
            logger.warning(f"  fetch {url} returned HTTP {r.status_code} ({len(r.text)} bytes), attempt {attempt}/{retries}")
        except Exception as e:
            err_class = type(e).__name__
            logger.warning(f"  fetch {url} failed ({err_class}: {str(e)[:80]}), attempt {attempt}/{retries}")

        if attempt < retries:
            time.sleep(backoff)
            backoff *= 2

    return None


# ── Extraction strategies ───────────────────────────────────────────────────

def _extract_trafilatura(html: str) -> Optional[str]:
    text = trafilatura.extract(html, include_links=False, include_images=False, favor_recall=True)
    return text if text and len(text) > 100 else None


def _extract_pages_content(html: str) -> Optional[str]:
    """For State Council, NDRC, NBS — content lives in <div class="pages_content">."""
    soup = BeautifulSoup(html, "html.parser")
    div = soup.find("div", class_="pages_content")
    if div:
        text = div.get_text(separator="\n", strip=True)
        return text if len(text) > 100 else None
    return None


def _extract_detail(html: str) -> Optional[str]:
    """For Xinhua / Qiushi — content lives in <div id="detail">."""
    soup = BeautifulSoup(html, "html.parser")
    div = soup.find("div", id="detail")
    if not div:
        # Some Xinhua pages use main-text class
        div = soup.find("div", class_="main-text")
    if div:
        text = div.get_text(separator="\n", strip=True)
        return text if len(text) > 100 else None
    return None


_EXTRACTORS = {
    "trafilatura": _extract_trafilatura,
    "pages_content": _extract_pages_content,
    "detail": _extract_detail,
}


def china_extract(html: str, extractor: str = "trafilatura") -> tuple[Optional[str], str]:
    """
    Try the named extractor first; fall back to trafilatura with favor_recall.
    Returns (text, method_used).
    """
    fn = _EXTRACTORS.get(extractor, _extract_trafilatura)
    text = fn(html)
    if text:
        return text, extractor

    # Fallback chain: try the others
    for name, alt_fn in _EXTRACTORS.items():
        if name == extractor:
            continue
        text = alt_fn(html)
        if text:
            return text, f"{name}_fallback"

    return None, "failed"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _load_sources_config() -> list[dict]:
    config_path = _HERE.parent / "config" / "china_sources.yaml"
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def _ensure_source_row(session, cfg: dict) -> Optional[int]:
    source = session.query(Source).filter_by(name=cfg["name"]).first()
    if source is None:
        lu = cfg.get("listing_url")
        if isinstance(lu, list):           # multi-URL listing (e.g. per-leader pages)
            lu = lu[0] if lu else None
        source = Source(
            name=cfg["name"],
            type=cfg.get("discovery_type", "html_curl_cffi"),
            url=lu,
            category=cfg.get("category", "china_gov"),
            tier=1 if cfg.get("weight") == "high" else 2,
            active=cfg.get("active", True),
        )
        session.add(source)
        session.commit()
        logger.info(f"Created source row: {source.name} (id={source.id})")
    return source.id


# ── MFA press-conference discovery (bespoke) ────────────────────────────────

def _discover_mfa(listing_url: str, link_pattern: str) -> list[str]:
    """MFA listing page → list of full press-conference URLs."""
    html = china_fetch(listing_url)
    if not html:
        return []
    pattern = re.compile(link_pattern)
    matches = pattern.findall(html)
    # Deduplicate, sorted descending (newest first by date in URL)
    unique = sorted(set(matches), reverse=True)
    # Construct full URLs
    full = [urljoin(listing_url, u.lstrip("./")) for u in unique]
    return full


# ── Generic HTML listing discovery ──────────────────────────────────────────

def _discover_html(listing_url: str, link_pattern: str) -> list[str]:
    """Generic listing page → article URLs matching pattern."""
    html = china_fetch(listing_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(link_pattern)

    candidates = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if pattern.search(href):
            full = urljoin(listing_url, href)
            candidates.add(full)
    return sorted(candidates, reverse=True)


# ── Xinhua homepage discovery (bespoke) ─────────────────────────────────────

def _discover_xinhua_home(listing_url: str, link_pattern: str) -> list[str]:
    """Xinhua homepage as discovery — lots of full URLs in one fetch."""
    html = china_fetch(listing_url)
    if not html:
        return []
    pattern = re.compile(link_pattern)
    matches = pattern.findall(html)
    return sorted(set(matches), reverse=True)


# ── JSON list-endpoint discovery (bespoke) ──────────────────────────────────

def _discover_json_list(listing_url: str, link_pattern: str) -> list[str]:
    """JSON list endpoint → article URLs matching pattern.

    Some gov.cn index pages decayed into JS/AJAX shells that curl_cffi (no JS
    engine) sees as empty, while the real article list is a static JSON the page
    fetches client-side (e.g. gov.cn .../YAOWENLIEBIAO.json). Read that JSON
    directly and keep each item's URL field that matches link_pattern.
    """
    raw = china_fetch(listing_url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning(f"  json_list: response was not valid JSON: {listing_url}")
        return []
    items = data if isinstance(data, list) else (data.get("data") or data.get("list") or [])
    pattern = re.compile(link_pattern)
    urls = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        val = it.get("URL") or it.get("url") or it.get("link")
        if not isinstance(val, str):   # a non-string url field would crash .strip() and zero the whole source
            continue
        u = val.strip()
        if u and pattern.search(u):
            urls.add(urljoin(listing_url, u))
    if not urls:
        # parsed but matched nothing — surface it instead of a silent discovered=0
        # (this is the same blind spot the discovery.py guard kills for RSS).
        keys = list(data)[:8] if isinstance(data, dict) else "array"
        logger.warning(f"  json_list: parsed {len(items)} item(s) but 0 matched — data keys={keys}: {listing_url}")
    return sorted(urls, reverse=True)


_DISCOVERY = {
    "mfa_press_conf": _discover_mfa,
    "html_curl_cffi": _discover_html,
    "xinhua_home": _discover_xinhua_home,
    "json_list": _discover_json_list,
}


# ── Title extraction ────────────────────────────────────────────────────────

def _extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:500]
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:500]
    return ""


# ── Publish-date from URL ───────────────────────────────────────────────────

def _url_publish_date(url: str):
    """Extract the publish date encoded in a China gov URL path; else None.

    China gov pages do NOT expose a publish_date in their HTML, so before this
    every China article stored publish_date=NULL — which forced the synth to
    PARSE the brief's date tag out of the article body, where it grabbed decree
    signing/effective/filing dates and produced stale-looking ("May 5") and even
    future ("Jul 1") stamps (2026-06-03 audit). The URL path is the reliable
    signal:
      fmprc / CCDI / Xinhua : .../t20260603_...  or  .../20260531/...  (YYYYMMDD)
      CAC                    : .../2026-06/03/...                       (YYYY-MM/DD)
      People's Daily        : .../2026/0603/...                        (/YYYY/MMDD/)
    gov.cn content URLs carry only year-month (.../202606/content_...), no day —
    those return None and the caller falls back to the scrape time.
    """
    # YYYYMMDD as 8 consecutive digits at a path/underscore/t boundary
    m = re.search(r'(?:^|[/_t])(\d{4})(\d{2})(\d{2})(?:[_./]|$)', url)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2020 <= y <= 2035 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime(y, mo, d)
            except ValueError:
                pass
    for pat in (r'/(\d{4})-(\d{2})/(\d{2})/', r'/(\d{4})/(\d{2})(\d{2})/'):
        m = re.search(pat, url)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
    return None


# ── Per-source scrape ───────────────────────────────────────────────────────

def scrape_source(session, cfg: dict, run_id: int, dry_run: bool = False, limit: int = 0) -> dict:
    """Scrape a single source. Returns counts dict."""
    name = cfg["name"]
    discovery_type = cfg.get("discovery_type", "html_curl_cffi")
    listing_url = cfg["listing_url"]
    link_pattern = cfg.get("link_pattern", "")
    extractor = cfg.get("extractor", "trafilatura")
    retries = cfg.get("retries", 1)

    logger.info(f"[start] {name} ({discovery_type})")

    discover_fn = _DISCOVERY.get(discovery_type)
    if discover_fn is None:
        logger.error(f"  unknown discovery type: {discovery_type}")
        return {"discovered": 0, "extracted": 0, "existing": 0, "failed": 0, "blocked": False}

    # listing_url may be a single URL or a list (e.g. per-leader index pages
    # where no combined hub exists). Discover across all, union, newest first.
    listing_urls = listing_url if isinstance(listing_url, list) else [listing_url]
    seen = set()
    for lu in listing_urls:
        seen.update(discover_fn(lu, link_pattern))
    urls = sorted(seen, reverse=True)   # global newest-first so a --limit cap samples evenly across listings
    counts = {"discovered": len(urls), "extracted": 0, "existing": 0, "failed": 0, "blocked": False}
    logger.info(f"  discovered {len(urls)} candidate URLs")

    if dry_run:
        for u in urls[:5]:
            logger.info(f"  [dry-run] would fetch: {u}")
        return counts

    source_id = _ensure_source_row(session, cfg)

    n = 0
    for url in urls:
        if limit and n >= limit:
            logger.info(f"  hit per-source limit of {limit}; stopping")
            break

        url_hash = _url_hash(url)
        existing = session.query(Article).filter_by(url_hash=url_hash).first()
        if existing:
            counts["existing"] += 1
            continue

        html = china_fetch(url, retries=retries)
        if not html:
            logger.warning(f"  failed to fetch {url}")
            counts["failed"] += 1
            continue

        text, method = china_extract(html, extractor=extractor)
        if not text:
            logger.warning(f"  failed to extract {url} (method={method})")
            counts["failed"] += 1
            continue

        title = _extract_title(html) or "(no title)"

        article = Article(
            source_id=source_id,
            title=title,
            url=url,
            url_hash=url_hash,
            full_text=text,
            extraction_method=method,
            extraction_failed=False,
            language="zh",
            # Populate publish_date from the URL path (China HTML has none), so the
            # synth dates the brief from a real date instead of body-parsing a
            # decree's signing/effective date. Fall back to now() (~scrape time,
            # accurate for fresh items) so it is NEVER null again.
            publish_date=_url_publish_date(url) or datetime.utcnow(),
            raw_metadata={},
        )
        try:
            session.add(article)
            session.commit()
            counts["extracted"] += 1
            n += 1
            logger.info(f"  [{n}] saved: {title[:60]} ({len(text)} chars, {method})")
        except IntegrityError:
            session.rollback()
            counts["existing"] += 1

    logger.info(
        f"[done]  {name} — discovered={counts['discovered']}, extracted={counts['extracted']}, "
        f"existing={counts['existing']}, failed={counts['failed']}, blocked={counts['blocked']}"
    )
    return counts


# ── Orchestrator ────────────────────────────────────────────────────────────

def run_china_scrape(only_domain: Optional[str] = None, dry_run: bool = False, limit: int = 0):
    if not CURL_CFFI_AVAILABLE:
        logger.error("curl_cffi not available — abort")
        sys.exit(1)

    sources = _load_sources_config()
    active = [s for s in sources if s.get("active", True)]
    if only_domain:
        active = [s for s in active if s.get("domain") == only_domain]
        if not active:
            logger.error(f"no active source matching domain={only_domain}")
            sys.exit(1)

    engine = get_engine()
    session = get_session(engine)

    run = ScrapeRun()
    session.add(run)
    session.commit()

    logger.info("═" * 60)
    logger.info(f"CHINA SCRAPE — {datetime.utcnow().isoformat()} — {len(active)} active sources")

    summary = []
    total_discovered = total_extracted = total_failed = 0

    try:
        for cfg in active:
            try:
                counts = scrape_source(session, cfg, run.id, dry_run=dry_run, limit=limit)
                summary.append((cfg["name"], counts))
                total_discovered += counts["discovered"]
                total_extracted += counts["extracted"]
                total_failed += counts["failed"]
            except Exception as e:
                logger.exception(f"[fail]  {cfg['name']} — {e}")
                summary.append((cfg["name"], {"discovered": 0, "extracted": 0, "existing": 0, "failed": 1, "blocked": False}))

        run.articles_discovered = total_discovered
        run.articles_extracted = total_extracted
        run.articles_failed = total_failed
        run.completed_at = datetime.utcnow()
        run.status = "completed"
        session.commit()

        logger.info("═" * 60)
        logger.info("CHINA SCRAPE SUMMARY")
        for name, c in summary:
            mark = "[ok]" if not c["blocked"] else "[BLOCKED]"
            logger.info(
                f"  {name:42s} d={c['discovered']:>3}  ext={c['extracted']:>3}  "
                f"existing={c['existing']:>3}  failed={c['failed']:>2}  {mark}"
            )

    except Exception as e:
        logger.exception(f"china scrape stage failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()
    finally:
        session.close()


# ── CLI entry ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    p = argparse.ArgumentParser(description="China gov source scraper")
    p.add_argument("--source", type=str, default=None, help="Limit to single source by domain (e.g. mfa.gov.cn)")
    p.add_argument("--dry-run", action="store_true", help="Discover only, no DB writes")
    p.add_argument("--limit", type=int, default=0, help="Cap articles per source (0 = unlimited)")
    args = p.parse_args()
    run_china_scrape(only_domain=args.source, dry_run=args.dry_run, limit=args.limit)
