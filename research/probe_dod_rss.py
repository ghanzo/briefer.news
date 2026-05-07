"""Probe DoD subdomains for RSS feeds and API endpoints."""
import sys
sys.path.insert(0, '../pipeline')
from scraper.akamai_bypass import akamai_fetch
import re

html = akamai_fetch('https://www.war.gov/News/News-Stories/')
if not html:
    print("FETCH FAILED")
    sys.exit(1)

print("=== API / RSS hints in war.gov News HTML ===")
seen = set()
patterns = [
    r'/api/[A-Za-z/_-]+',
    r'/_api/[A-Za-z/_-]+',
    r'/RSS/?[A-Za-z/_.?=&-]*',
    r'rss\.ashx[^"\' ]*',
    r'data-(?:api|endpoint|src|url)="([^"]+)"',
    r'feedUrl["\':\s=]+["\']([^"\']+)',
    r'GetItem\?[^"\']+',
    r'DesktopModules/[^"\']+',
]
for pat in patterns:
    for m in re.finditer(pat, html):
        full = m.group(0)
        if full in seen:
            continue
        seen.add(full)
        if any(k in full.lower() for k in ['api', 'rss', 'feed', 'getitem', 'desktopmodules']):
            print("  " + full[:200])

print()
print("=== Direct probe of common DoD RSS paths ===")
candidates = [
    'https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=News',
    'https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?Site=945',
    'https://www.war.gov/News/News-Stories/RSS/',
    'https://www.war.gov/Resources/RSS/',
    'https://www.war.gov/News/News-Stories/?max=10&Format=rss',
    'https://www.defense.gov/News/News-Stories/RSS/',
    'https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=News',
    'https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=News',
    'https://www.centcom.mil/MEDIA/PRESS-RELEASES/RSS/',
]
for url in candidates:
    r = akamai_fetch(url)
    if r is None:
        print(f"  FAIL    {url}")
        continue
    head = r[:500].lower()
    is_xml = r.lstrip().startswith('<?xml') or '<rss' in head or '<feed' in head
    typ = "XML" if is_xml else "HTML"
    print(f"  {len(r):>7}b {typ:4s}  {url}")
