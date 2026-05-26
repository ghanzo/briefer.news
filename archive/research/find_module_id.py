"""Find the right ArticleCS module ID for war.gov News-Stories.

Uses curl_cffi directly (bypassing the heavy 90-180s rate limit in
akamai_bypass.py) since these probes return tiny XML responses
unlikely to trigger rate-detection.
"""
from curl_cffi import requests
import re
import time

print("Probing module IDs on war.gov ArticleCS GetList API...")
print()

found = []

# Probe range — common DNN module IDs
ids_to_try = list(range(1, 30)) + list(range(50, 150, 5)) + list(range(900, 1500, 25))

for i, mid in enumerate(ids_to_try):
    url = f'https://www.war.gov/API/ArticleCS/Public/GetList?dpage=0&moduleID={mid}'
    try:
        r = requests.get(url, impersonate='chrome120', timeout=10)
    except Exception as e:
        print(f"  moduleID={mid:>4d} ERROR: {e}")
        continue

    body = r.text
    if r.status_code != 200:
        # Don't print 404s, just count them
        continue
    if '<data></data>' in body or '<data />' in body:
        # Empty
        continue
    # Has content
    found.append(mid)
    data_match = re.search(r'<data>(.*?)</data>', body, re.DOTALL)
    sample = data_match.group(1)[:400] if data_match else body[:400]
    print(f"  >>> moduleID={mid:>4d} returned content (length={len(body)}):")
    print(f"      {sample}")
    print()

    # Stop after finding 3 working module IDs
    if len(found) >= 3:
        break

    # Light delay to avoid hammering
    time.sleep(2)

print()
print(f"Module IDs with content: {found}")
