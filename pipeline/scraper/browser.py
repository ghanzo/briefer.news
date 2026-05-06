"""
browser.py — Singleton Playwright browser manager.

Starts one headless Chromium process per pipeline run and reuses it.
Uses the sync Playwright API so all existing code stays synchronous.
"""

import logging
import random
import time
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Per-domain Akamai pacing.
# Default: 4-8s jitter — fine for most sites (WH, DOJ, DOE, ARPA-E, ORNL, GAO).
# war.gov: 30-60s — Akamai there is much stricter. Verified 2026-05-06: rapid
# sequential fetches return 300-char "Access Denied" pages within ~10 attempts,
# then full block for hours. Long-delay scrape can run slowly throughout the
# day without triggering escalation.
_DEFAULT_JITTER = (4.0, 8.0)
_DOMAIN_JITTER_OVERRIDES = {
    "www.war.gov": (30.0, 60.0),
    "war.gov":     (30.0, 60.0),
}
_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


def _jitter_for(url: str) -> tuple[float, float]:
    domain = urlparse(url).netloc
    return _DOMAIN_JITTER_OVERRIDES.get(domain, _DEFAULT_JITTER)


class _BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser = None

    def get_browser(self):
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            logger.info("Playwright browser launched")
        return self._browser

    def close(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._browser = None
        self._playwright = None
        logger.info("Playwright browser closed")


browser_manager = _BrowserManager()  # module-level singleton


def playwright_fetch(url: str, wait_until: str = "networkidle", timeout: int = 30000) -> Optional[str]:
    """Render a URL with Playwright (with stealth + jitter pacing) and return HTML.

    Two layers of bot-protection bypass:
      1. stealth_sync — patches navigator.webdriver and other automation tells
      2. Jittered pre-fetch delay (4-8s) — keeps the request rate under the
         human-browsing threshold so Akamai doesn't escalate

    Verified 2026-05-06 against war.gov (DoD) + gao.gov, both Akamai-protected.
    Without stealth, both return "Access Denied" pages. Without pacing,
    war.gov degrades to ~300-char partial responses after several rapid hits.

    Note: a previous attempt to use a fresh browser context per request made
    war.gov fail entirely — Akamai apparently treats a flurry of "fresh"
    fingerprints from same IP as more suspicious than a single warm session.
    Sticking with the singleton browser context.
    """
    try:
        from playwright_stealth import stealth_sync

        # Per-domain pre-fetch jitter — war.gov needs much longer pacing
        delay = random.uniform(*_jitter_for(url))
        if delay > 15:
            logger.info(f"Long pre-fetch delay {delay:.0f}s for {url[:80]}")
        time.sleep(delay)

        page = browser_manager.get_browser().new_page()
        stealth_sync(page)
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout)
            html = page.content()
            return html
        finally:
            page.close()
    except Exception as e:
        logger.warning(f"Playwright fetch failed for {url}: {e}")
        return None
