"""Debug what whitehouse.gov/briefing-room actually returns."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from urllib.parse import urlparse
from bs4 import BeautifulSoup
from scraper.browser import playwright_fetch, browser_manager

URL = "https://www.whitehouse.gov/briefing-room/"

print(f"Rendering {URL} with Playwright...")
html = playwright_fetch(URL)
if not html:
    print("FAIL: Playwright returned None")
    browser_manager.close()
    sys.exit(1)

print(f"HTML length: {len(html)} chars")

soup = BeautifulSoup(html, "lxml")
title = soup.find("title")
print(f"Page <title>: {title.get_text(strip=True) if title else '(none)'}")

# Sample of body text
body_text = soup.get_text(" ", strip=True)
print(f"Body text length: {len(body_text)} chars")
print(f"First 500 chars of body:\n  {body_text[:500]}")

# All links
all_anchors = soup.find_all("a", href=True)
print(f"\nTotal <a> tags with href: {len(all_anchors)}")

base_domain = urlparse(URL).netloc
same_domain = []
external = []
for a in all_anchors:
    href = a["href"]
    if href.startswith(("/", "#")):
        same_domain.append(href)
    else:
        parsed = urlparse(href)
        if parsed.netloc == base_domain or parsed.netloc == "":
            same_domain.append(href)
        else:
            external.append(href)

print(f"  Same-domain (incl relative): {len(same_domain)}")
print(f"  External:                    {len(external)}")

# Show first 30 same-domain links
print("\nFirst 30 same-domain links:")
for h in same_domain[:30]:
    print(f"  {h}")

# Check for redirect / final URL
print("\nLooking for canonical / og:url meta:")
canonical = soup.find("link", rel="canonical")
og_url = soup.find("meta", attrs={"property": "og:url"})
if canonical:
    print(f"  canonical: {canonical.get('href')}")
if og_url:
    print(f"  og:url:    {og_url.get('content')}")

# Save full HTML for offline review
out = Path(__file__).parent / "whitehouse_debug.html"
out.write_text(html, encoding="utf-8")
print(f"\nFull HTML saved to: {out}")

browser_manager.close()
