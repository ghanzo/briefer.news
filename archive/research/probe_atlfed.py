"""Quick httpx probe of Atlanta Fed candidate URLs to find which exist."""
import httpx

CANDIDATES = [
    "https://www.atlantafed.org/news",
    "https://www.atlantafed.org/news/press-releases",
    "https://www.atlantafed.org/about/contact/news-press-releases",
    "https://www.atlantafed.org/press-releases",
    "https://www.atlantafed.org/about-us/press-room",
    "https://www.atlantafed.org/research/publications",
    "https://www.atlantafed.org/research",
    "https://www.atlantafed.org/blogs",
    "https://www.atlantafed.org/blogs/macroblog",
    "https://www.atlantafed.org/cqer/research/macroblog",
    "https://www.atlantafed.org/cqer/research/gdpnow",
    "https://www.atlantafed.org/RSS",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

print(f"{'URL':<70} {'Status':<10} {'Size':<10} {'Notes'}")
print("-" * 110)
with httpx.Client(timeout=15, headers=HEADERS, follow_redirects=True) as client:
    for url in CANDIDATES:
        try:
            r = client.get(url)
            ct = r.headers.get("content-type", "?").split(";")[0]
            final = r.url if str(r.url) != url else ""
            notes = f"ct={ct}"
            if final:
                notes += f"  redirected→ {final}"
            print(f"{url:<70} {r.status_code:<10} {len(r.content):<10} {notes}")
        except httpx.TimeoutException:
            print(f"{url:<70} TIMEOUT    -          ")
        except Exception as e:
            print(f"{url:<70} ERROR      -          {type(e).__name__}: {str(e)[:50]}")
