"""
Probe DoD .mil subdomains to find their ArticleCS moduleIDs and test
whether they share Akamai defender configuration with war.gov.

For each subdomain:
  1. Fetch the news listing page → look for `storyListing<NUM>_data` Vue var
  2. Try the ArticleCS GetList API with that moduleID
  3. Report whether content was returned, timed out, or blocked

If all .mil sites timeout/block uniformly → shared defender, war.gov flag spreads
If results differ → separate per-subdomain protection
"""
import re
import time

from curl_cffi import requests
from curl_cffi.requests.exceptions import Timeout, RequestException

SITES = [
    ("war.gov",      "https://www.war.gov/News/News-Stories/"),
    ("centcom.mil",  "https://www.centcom.mil/MEDIA/NEWS/News-Article-View/"),
    ("centcom.mil2", "https://www.centcom.mil/MEDIA/PRESS-RELEASES/"),
    ("navy.mil",     "https://www.navy.mil/Press-Office/News-Stories/"),
    ("army.mil",     "https://www.army.mil/news/"),
    ("af.mil",       "https://www.af.mil/News/"),
    ("marines.mil",  "https://www.marines.mil/News/Press-Releases/"),
    ("jcs.mil",      "https://www.jcs.mil/Media/News/"),
]


def fetch(url, timeout=15):
    try:
        r = requests.get(url, impersonate="chrome120", timeout=timeout)
        return r.status_code, r.text, None
    except Timeout:
        return None, None, "timeout"
    except RequestException as e:
        return None, None, f"err:{type(e).__name__}"


def find_module_id(html):
    """Look for `storyListing<NUM>` or `storyListing2_<NUM>` Vue var name."""
    if not html:
        return None
    for pat in [r"storyListing(\d+)_(?:data|methods)", r"storyListing2_(\d+)_(?:data|methods)", r"storyListing[\w]*?_(\d+)"]:
        m = re.search(pat, html)
        if m:
            return int(m.group(1))
    return None


def find_module_id_from_dnnvar(html):
    """Some pages embed sf_tabId — could try probing around that."""
    if not html:
        return None
    m = re.search(r'sf_tabId[`\'\":\s,]+(\d+)', html)
    if m:
        return int(m.group(1))
    return None


def probe_api(domain, mid):
    url = f"https://www.{domain.replace('2','')}/API/ArticleCS/Public/GetList?dpage=0&moduleID={mid}"
    status, body, err = fetch(url, timeout=15)
    if err:
        return f"API: {err}"
    if status != 200:
        return f"API: HTTP {status}"
    # Inspect data block size
    data_match = re.search(r"<data>(.*?)</data>", body or "", re.DOTALL)
    if not data_match:
        return f"API: HTTP 200 but no <data>"
    data_len = len(data_match.group(1))
    if data_len < 50:
        return f"API: empty data ({data_len}b)"
    # Count how many cards
    cards = len(re.findall(r"<(?:story-card|listing-with-preview)\b", data_match.group(1)))
    return f"API: HTTP 200, {data_len}b data, {cards} cards"


def main():
    print(f"{'site':18s}  listing fetch     module-id   API result")
    print("-" * 100)
    for domain, listing_url in SITES:
        status, body, err = fetch(listing_url, timeout=20)
        if err:
            print(f"{domain:18s}  listing: {err:13s}  —          —")
            time.sleep(2)
            continue
        if status != 200:
            print(f"{domain:18s}  HTTP {status}            —          —")
            time.sleep(2)
            continue

        html_size = len(body)
        mid = find_module_id(body)
        if mid is None:
            mid = find_module_id_from_dnnvar(body)
        mid_str = str(mid) if mid else "not found"

        if mid:
            api_result = probe_api(domain, mid)
        else:
            api_result = "(no module ID)"

        print(f"{domain:18s}  HTTP 200, {html_size:>6}b  {mid_str:10s}  {api_result}")

        # Polite pacing — 3 sec between sites
        time.sleep(3)


if __name__ == "__main__":
    main()
