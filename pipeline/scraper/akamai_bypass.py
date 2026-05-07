"""
Akamai-protected source bypass using curl_cffi (BoringSSL TLS fingerprinting).

DoD subdomains (war.gov, centcom.mil, navy.mil) sit behind Akamai bot
protection that blocks standard httpx and Playwright clients on the
TLS / browser-fingerprint layer. curl_cffi uses BoringSSL — Chrome's
TLS stack — so JA3/JA4 fingerprints match real Chrome exactly.

Confirmed working from a residential IP, 2026-05-07.

Usage:
    from scraper.akamai_bypass import akamai_extract

    text, method = akamai_extract("https://www.war.gov/News/.../article/")
    if text:
        print(text)
"""

import logging
import random
import re
import time
from typing import Optional

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ── Rate limiting per domain ─────────────────────────────────────────────────
# Akamai's flag-the-IP behavior triggers when too many requests hit the same
# domain in a short window. These intervals are conservative; tune downward
# only after weeks of reliable scraping.
_DOMAIN_INTERVALS = {
    "war.gov": (90.0, 180.0),
    "www.war.gov": (90.0, 180.0),
    "centcom.mil": (90.0, 180.0),
    "www.centcom.mil": (90.0, 180.0),
    "navy.mil": (60.0, 120.0),
    "www.navy.mil": (60.0, 120.0),
    "default": (30.0, 60.0),
}

_LAST_FETCH: dict[str, float] = {}


def _domain_of(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1) if m else "default"


def _wait_for_rate_limit(url: str) -> None:
    """Block until the per-domain rate-limit window has passed."""
    domain = _domain_of(url)
    interval = _DOMAIN_INTERVALS.get(domain, _DOMAIN_INTERVALS["default"])

    last = _LAST_FETCH.get(domain, 0.0)
    now = time.time()
    target = last + random.uniform(*interval)

    if now < target:
        wait = target - now
        logger.info(f"akamai_bypass rate-limit pacing {domain}: waiting {wait:.1f}s")
        time.sleep(wait)

    _LAST_FETCH[domain] = time.time()


# ── Core fetch ───────────────────────────────────────────────────────────────

def akamai_fetch(url: str, impersonate: str = "chrome120", timeout: int = 30) -> Optional[str]:
    """
    Fetch URL through curl_cffi with Chrome TLS impersonation.

    Returns the response text if status 200 and content looks valid,
    None if blocked or failed. Honors per-domain rate limit.
    """
    if not CURL_CFFI_AVAILABLE:
        logger.error("curl_cffi not installed — pip install curl_cffi")
        return None

    _wait_for_rate_limit(url)

    try:
        r = curl_requests.get(url, impersonate=impersonate, timeout=timeout)
    except Exception as e:
        logger.warning(f"akamai_fetch {url} threw {type(e).__name__}: {e}")
        return None

    if r.status_code != 200:
        logger.warning(f"akamai_fetch {url} returned HTTP {r.status_code}")
        return None

    # Detect Akamai block pages — these are short responses with specific markers.
    body = r.text
    if len(body) < 5000 and ("Access Denied" in body or "Reference #" in body):
        logger.warning(f"akamai_fetch {url} returned an Access Denied page — IP may be flagged")
        return None

    return body


# ── Article extraction ───────────────────────────────────────────────────────

def akamai_extract(url: str) -> tuple[Optional[str], str]:
    """
    Fetch an Akamai-protected URL and extract article body text.

    Returns (text, method) where method is one of:
        'curl_cffi_trafilatura' — extracted via trafilatura
        'curl_cffi_dod_news'    — extracted via DoD-specific BS4 path
        'curl_cffi_bs4'         — generic BS4 paragraph fallback
        'failed'                — fetch or extraction failed
    """
    html = akamai_fetch(url)
    if not html:
        return None, "failed"

    # 1) Try trafilatura first — works for many simpler DoD pages.
    try:
        text = trafilatura.extract(html, include_comments=False, no_fallback=False)
        if text and len(text) > 500:
            return text, "curl_cffi_trafilatura"
    except Exception as e:
        logger.warning(f"trafilatura failed on {url}: {e}")

    # 2) DoD News-specific extraction — the article lives in the
    #    <div data-content-type="News"> container, with header + body paragraphs.
    try:
        soup = BeautifulSoup(html, "lxml")
        content_div = soup.find("div", attrs={"data-content-type": "News"})
        if content_div:
            # Title + dateline + body
            title_tag = content_div.find("h1", class_="maintitle")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Body paragraphs
            body_paragraphs = []
            # The actual article body is inside <p> tags in the content wrap;
            # filter out social-share, navigation, gallery captions
            for p in content_div.find_all("p"):
                txt = p.get_text(strip=True)
                if not txt or len(txt) < 30:
                    continue
                # Skip common non-body patterns
                if "Share:" in txt or txt.startswith("$"):
                    continue
                body_paragraphs.append(txt)

            if body_paragraphs:
                full = (title + "\n\n" if title else "") + "\n\n".join(body_paragraphs)
                if len(full) > 500:
                    return full, "curl_cffi_dod_news"
    except Exception as e:
        logger.warning(f"DoD-specific extraction failed on {url}: {e}")

    # 3) Generic fallback — all paragraph tags, filter short / nav-like.
    try:
        soup = BeautifulSoup(html, "lxml")
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        body = "\n\n".join(p for p in paragraphs if p and len(p) > 50)
        if len(body) > 500:
            return body, "curl_cffi_bs4"
    except Exception as e:
        logger.warning(f"bs4 fallback failed on {url}: {e}")

    return None, "failed"


# ── Discovery: find article URLs from a listing page ─────────────────────────

def akamai_discover_links(listing_url: str, link_pattern: str) -> list[str]:
    """
    Fetch a listing page and find all article URLs matching the pattern.

    Args:
        listing_url: the news/press-release listing URL (e.g. https://www.war.gov/News/News-Stories/)
        link_pattern: substring that must appear in article URLs
                      (e.g. "/News/News-Stories/Article/Article/")

    Returns: list of fully-qualified article URLs, deduplicated.
    """
    html = akamai_fetch(listing_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    base_match = re.match(r"(https?://[^/]+)", listing_url)
    base = base_match.group(1) if base_match else ""

    seen = set()
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if link_pattern not in href:
            continue
        # Resolve relative URL
        if href.startswith("/"):
            href = base + href
        elif not href.startswith("http"):
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append(href)

    return out


# ── Discovery: DNN ArticleCS GetList API ─────────────────────────────────────

def akamai_discover_via_dnn_api(api_url: str) -> list[dict]:
    """
    Fetch a DotNetNuke ArticleCS GetList endpoint and extract article cards.

    DNN ArticleCS module is used by war.gov, centcom.mil, navy.mil, and most
    other DoD subdomains. The endpoint returns XML with HTML-encoded Vue
    <story-card> components containing article-url-or-link-absolute,
    article-title, publish-date-jss, and other metadata.

    Args:
        api_url: e.g. "https://www.war.gov/API/ArticleCS/Public/GetList?dpage=0&moduleID=2842"

    Returns: list of dicts with keys
        url           — canonical article URL
        title         — article title
        publish_date  — ISO 8601 string (or None)
        image_url     — hero image URL (or None)
    """
    body = akamai_fetch(api_url)
    if not body:
        return []

    import html as html_lib
    data_match = re.search(r"<data>(.*?)</data>", body, re.DOTALL)
    if not data_match:
        return []

    inner = html_lib.unescape(data_match.group(1))

    out = []
    seen_urls = set()
    # DoD pages use either <story-card> or <listing-with-preview>. Both have
    # attribute values containing embedded HTML (with > inside double quotes),
    # so we can't use a simple `[^>]+` pattern. Instead split on each opening
    # tag and parse attribute pairs out of the span until the next element.
    elements = re.split(r'(?=<(?:story-card|listing-with-preview)\b)', inner)
    # Quote-aware attribute pattern: value is everything between double quotes
    # except an unescaped quote. Allows >, <, single quotes inside.
    attr_pattern = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"', re.DOTALL)

    for el in elements:
        s = el.lstrip()
        if not (s.startswith("<story-card") or s.startswith("<listing-with-preview")):
            continue

        attrs = {}
        for m in attr_pattern.finditer(el):
            key = m.group(1)
            if key not in attrs:
                attrs[key] = m.group(2)

        url = (
            attrs.get("article-url-or-link-absolute")
            or attrs.get("article-url-or-link")
            or attrs.get("article-url")
        )
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        out.append({
            "url": url,
            "title": attrs.get("article-title", ""),
            "publish_date": attrs.get("publish-date-jss"),
            "image_url": attrs.get("article-image-url") or attrs.get("image-url"),
        })

    return out
