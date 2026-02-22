"""
browser.py — Singleton Playwright browser manager.

Starts one headless Chromium process per pipeline run and reuses it.
Uses the sync Playwright API so all existing code stays synchronous.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    """Render a URL with Playwright and return the full HTML."""
    try:
        page = browser_manager.get_browser().new_page()
        page.goto(url, wait_until=wait_until, timeout=timeout)
        html = page.content()
        page.close()
        return html
    except Exception as e:
        logger.warning(f"Playwright fetch failed for {url}: {e}")
        return None
