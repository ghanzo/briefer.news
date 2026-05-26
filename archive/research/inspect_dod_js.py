"""Inspect the war.gov ArticleCS.js to find AJAX URL endpoints."""
import sys
sys.path.insert(0, '../pipeline')
from scraper.akamai_bypass import akamai_fetch

js = akamai_fetch('https://www.war.gov/DesktopModules/ArticleCS/Resources/ArticleCS/js/ArticleCS.js?cdv=2020')
if not js:
    sys.exit(1)

lines = js.split('\n')
print(f"JS file: {len(lines)} lines, {len(js)} bytes")
print()

# Find each line containing $.ajax( and print 10 lines of context
for i, line in enumerate(lines):
    if '$.ajax' in line:
        print(f"--- $.ajax at line {i+1} ---")
        for j in range(i, min(i+12, len(lines))):
            print(f"  {j+1:4d}: {lines[j].rstrip()}")
        print()

# Also list any line containing .ashx or /News/ or /_api/
print("=== Lines mentioning .ashx, /_api, or /News ===")
for i, line in enumerate(lines):
    s = line.strip()
    if any(k in s for k in ['.ashx', '/_api', '/News/']) and 'http' not in s.lower():
        print(f"  {i+1:4d}: {s[:200]}")
