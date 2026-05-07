"""Inspect the war.gov ArticleCS GetList API response structure."""
from curl_cffi import requests
import re

r = requests.get(
    'https://www.war.gov/API/ArticleCS/Public/GetList?dpage=0&moduleID=1200',
    impersonate='chrome120',
    timeout=20,
)
print(f"Status {r.status_code}, body {len(r.text)} bytes")
print()

# The body contains XML with HTML-encoded Vue components. Decode the data block.
body = r.text
data_match = re.search(r'<data>(.*?)</data>', body, re.DOTALL)
if not data_match:
    print("No <data> block found")
    print(body[:2000])
    exit(1)

import html as html_lib
inner = html_lib.unescape(data_match.group(1))
print(f"Decoded data block: {len(inner)} bytes")
print()
print("=== First story-card ===")
# Extract first 2000 chars of decoded content to see structure
print(inner[:3500])
print()

# Find all article-id and article-title attributes
print("=== All articles found ===")
for m in re.finditer(r'article-id="(\d+)"\s+article-title="([^"]+)"', inner):
    print(f"  id={m.group(1)}  title={m.group(2)[:80]}")

# Also look for any URL-like attributes
print()
print("=== URL-like attributes ===")
for m in re.finditer(r'(?:href|src|url|article-href|to)="([^"]+)"', inner):
    u = m.group(1)
    if u.startswith('/News/News-Stories'):
        print(f"  {u}")
