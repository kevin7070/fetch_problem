# Bypassing Bot Protection for Web Scraping

A practical guide to fetching data from websites with anti-bot protection.

## Problem Statement

When fetching data from `https://www.spglobal.com/spdji/en/util/redesign/get-index-comparison-data.dot`, a browser successfully returns JSON data, but Python `requests` returns **403 Forbidden**.

## Understanding Bot Protection

### How Websites Detect Bots

| Detection Method | What It Checks |
|-----------------|----------------|
| User-Agent | Missing or generic UA = bot |
| HTTP Version | HTTP/1.1 vs HTTP/2 fingerprinting |
| TLS Fingerprint | JA3/JA4 signatures differ between libraries |
| Headers Order | Browsers send headers in specific order |
| Cookies/Session | Bot management cookies (e.g., `bm_*` from Akamai) |
| JavaScript | Cloudflare/Akamai challenges require JS execution |

### Identifying Protection Type

Check cookies after visiting the main page:

| Cookie Prefix | Protection |
|---------------|------------|
| `bm_*` | Akamai Bot Manager |
| `cf_*`, `__cf*` | Cloudflare |
| `_px*` | PerimeterX |
| `datadome` | DataDome |

## Solution Hierarchy

Try these approaches in order (simplest to most complex):

```
Level 1: Add browser headers        → Works for basic protection
Level 2: Use session with cookies   → Works for session-based checks
Level 3: HTTP/2 with httpx          → Works for protocol fingerprinting
Level 4: curl_cffi / TLS spoofing   → Works for TLS fingerprinting
Level 5: Browser automation         → Works for JavaScript challenges
```

## Level 1: Browser Headers

Basic header spoofing with `requests`:

```python
import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

response = requests.get(url, headers=headers)
```

## Level 2: Session with Cookies

Visit the main page first to obtain session cookies:

```python
import requests

session = requests.Session()
session.headers.update(headers)

# Step 1: Get cookies from main page
session.get("https://example.com/")

# Step 2: API request with cookies attached
response = session.get("https://example.com/api/data")
```

## Level 3: HTTP/2 with httpx (This Solution)

Some bot protection checks HTTP protocol version. Browsers use HTTP/2, but `requests` only supports HTTP/1.1.

### Installation

```bash
pip install 'httpx[http2]'
```

### Implementation

```python
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

with httpx.Client(http2=True, headers=HEADERS, follow_redirects=True) as client:
    # Visit main page for cookies
    client.get("https://www.spglobal.com/spdji/en/")

    # Fetch API with same-origin headers
    response = client.get(
        "https://www.spglobal.com/spdji/en/util/redesign/get-index-comparison-data.dot",
        params={"compareArray": "5457755", "periodFlag": "tenYearFlag", "language_id": "1"},
        headers={"Sec-Fetch-Site": "same-origin", "Referer": "https://www.spglobal.com/spdji/en/"},
    )
    data = response.json()
```

### Why HTTP/2 Works

| Feature | HTTP/1.1 (requests) | HTTP/2 (httpx) |
|---------|---------------------|----------------|
| Multiplexing | No | Yes |
| Header Compression | No | HPACK |
| Binary Protocol | No | Yes |
| Bot Detection | Flagged as suspicious | Matches browser |

## Level 4: TLS Fingerprint Spoofing

If HTTP/2 is not enough, the site may check TLS fingerprints (JA3/JA4).

### Installation

```bash
pip install curl_cffi
```

### Implementation

```python
from curl_cffi import requests

# Impersonate Chrome browser's TLS fingerprint
response = requests.get(
    url,
    impersonate="chrome",
    headers=headers,
)
```

Supported impersonation targets:
- `chrome110`, `chrome116`, `chrome120`
- `safari15_5`, `safari17_0`
- `edge101`

## Level 5: Browser Automation

For JavaScript challenges (Cloudflare turnstile, etc.), use real browser:

### Installation

```bash
pip install playwright
playwright install chromium
```

### Implementation

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Navigate and wait for JS execution
    page.goto("https://example.com/")
    page.wait_for_load_state("networkidle")

    # Extract data
    content = page.content()
    # or intercept API responses

    browser.close()
```

## Debugging Tips

### 1. Compare Request Headers

Use browser DevTools (Network tab) to capture exact headers:

```python
# Print what you're sending
import httpx
response = httpx.get(url, headers=headers)
print(response.request.headers)
```

### 2. Check Response Details

```python
print(f"Status: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Body preview: {response.text[:500]}")
```

### 3. Verify HTTP Version

```python
print(f"HTTP Version: {response.http_version}")  # Should be "HTTP/2"
```

## Summary

For S&P Global specifically:

| Approach | Result |
|----------|--------|
| `requests` + headers | 403 Forbidden |
| `requests.Session()` + cookies | 403 Forbidden |
| `httpx` + HTTP/2 | **Success** |

The site uses **Akamai Bot Manager** which fingerprints HTTP protocol version. Using `httpx` with HTTP/2 bypasses this check.

## References

- [httpx documentation](https://www.python-httpx.org/)
- [curl_cffi - TLS fingerprint impersonation](https://github.com/yifeikong/curl_cffi)
- [Playwright - Browser automation](https://playwright.dev/python/)
