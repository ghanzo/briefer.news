"""Find the DoD ArticleCS API endpoint embedded in the page."""
import sys
sys.path.insert(0, '../pipeline')
from scraper.akamai_bypass import akamai_fetch
import re

html = akamai_fetch('https://www.war.gov/News/News-Stories/')
print(f"News-Stories page: {len(html)} bytes")

# Search for module ID, ServicesFramework hints, ArticleCS module
print()
print("=== ServicesFramework / Module hints ===")
for pat in [
    r'ServicesFramework\([^)]+\)',
    r'getServiceRoot\([^)]+\)',
    r'moduleId["\':\s=]+\d+',
    r'moduleID["\':\s=]+\d+',
    r'data-mid["\':\s=]+\d+',
    r'mid=\d+',
    r'Site["\':\s=]+\d+',
    r'SiteId["\':\s=]+\d+',
    r'ContentTypeId["\':\s=]+\d+',
    r'/API/[A-Za-z]+/[A-Za-z]+/[A-Za-z]+',
    r'/DesktopModules/ArticleCS/[A-Za-z/]+',
    r'getList[^"\']*"[^"]+',
]:
    for m in re.finditer(pat, html):
        s = m.group(0)
        if len(s) < 200:
            print(f"  {s}")

# Also try the most likely API URL directly
print()
print("=== Probe likely API URLs ===")

# DNN ServicesFramework URLs typically look like:
#   /API/ArticleCS/Public/GetList?moduleID=X&dpage=0&...
# Or with portal prefix:
#   /Portals/0/Skins/.../api/ArticleCS/Public/GetList...

candidates = [
    'https://www.war.gov/API/ArticleCS/Public/GetList?dpage=0&moduleID=1',
    'https://www.war.gov/DesktopModules/ArticleCS/API/Public/GetList?dpage=0&moduleID=1',
    'https://www.war.gov/DesktopModules/ArticleCS/Public/GetList?dpage=0&moduleID=1',
    'https://www.war.gov/api/ArticleCS/Public/GetList?dpage=0',
]
for url in candidates:
    r = akamai_fetch(url)
    if r is None:
        print(f"  FAIL  {url}")
        continue
    is_json = r.lstrip().startswith('{') or r.lstrip().startswith('[')
    print(f"  {len(r):>6}b {'JSON' if is_json else 'HTML':4s}  {url}")
    if is_json and len(r) < 500:
        print("    ->", r[:300])
