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
Level 1: Add browser headers             → Works for basic protection
Level 2: Use session with cookies        → Works for session-based checks
Level 3: HTTP/2 with httpx               → Works for protocol fingerprinting
Level 4: curl_cffi / TLS spoofing        → Works for TLS fingerprinting
Level 5: Playwright Firefox (headless)   → Works for Akamai JS challenges  ✅
Level 6: Playwright Chromium / Selenium  → Last resort (often detected)
```

> **For S&P Global (Akamai Bot Manager), only Level 5 (Playwright Firefox) works reliably.**
> Levels 1-4 and Playwright Chromium are all detected and blocked.

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

## Level 5: Playwright Firefox (This Solution)

For Akamai Bot Manager with JS challenges, **Playwright Firefox** is the only
programmatic approach that works reliably. Chromium-based browsers (including
Chrome, Playwright Chromium, and headless Chrome) are detected and blocked.

### Why Firefox?

| Browser Engine | Akamai Detection | Result |
|---------------|------------------|--------|
| Playwright Chromium | Detected (webdriver flag, TLS fingerprint) | 403 |
| Playwright Chrome (system) | Detected (automation signals) | 403 |
| Playwright Firefox | Not detected | **200** |
| curl_cffi (Chrome impersonation) | Detected (no JS execution) | 403 |
| httpx HTTP/2 | Inconsistent (works initially, then blocked) | 403 |

### Installation

```bash
pip install playwright
playwright install firefox
```

### Implementation

```python
import json
from playwright.sync_api import sync_playwright

def fetch_index_data(index_id, period="tenYearFlag", language_id="1"):
    api_url = (
        "https://www.spglobal.com/spdji/en/util/redesign/get-index-comparison-data.dot"
        f"?compareArray={index_id}&periodFlag={period}&language_id={language_id}"
    )

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()

        # Intercept network response
        result = {}

        def on_response(response):
            if "get-index-comparison-data" in response.url:
                result["data"] = response.json()

        page.on("response", on_response)

        page.goto(api_url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)  # Wait for JS challenge to resolve

        browser.close()

    return result.get("data", {})
```

### Key Techniques

1. **Response interception** — Use `page.on("response", ...)` to capture API JSON
   directly from the network layer, avoiding HTML parsing issues.
2. **Wait for JS challenge** — Akamai injects a `<script>` tag that must execute
   before the real response is returned. A 10-second timeout allows this.
3. **Firefox engine** — Firefox's TLS fingerprint and automation signals differ
   from Chromium, making it harder for Akamai to detect.

## Level 6: Chromium / Selenium (Unreliable)

Chromium-based automation is widely detected by Akamai. Even with stealth
measures (`--disable-blink-features=AutomationControlled`, removing
`navigator.webdriver`), Akamai still blocks the request.

```python
# This does NOT work for Akamai-protected sites
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com/")
    page.wait_for_load_state("networkidle")
    content = page.content()
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

For S&P Global (Akamai Bot Manager):

| Approach | Result | Why |
|----------|--------|-----|
| `requests` + headers | 403 | No HTTP/2, no JS execution |
| `requests.Session()` + cookies | 403 | Same — HTTP/1.1 detected |
| `httpx` + HTTP/2 | 403 (intermittent) | Works initially, then TLS fingerprinted |
| `curl_cffi` (Chrome impersonation) | 403 | No JS execution for challenge |
| Playwright Chromium | 403 | Automation detected |
| Playwright Chrome (system) | 403 | Automation detected |
| **Playwright Firefox** | **200** | **Passes all checks** |

The site uses **Akamai Bot Manager** which combines multiple detection layers:
TLS fingerprinting, HTTP protocol checks, automation flags, and JS challenges.
Only **Playwright Firefox** passes all layers reliably.

## References

- [httpx documentation](https://www.python-httpx.org/)
- [curl_cffi - TLS fingerprint impersonation](https://github.com/yifeikong/curl_cffi)
- [Playwright - Browser automation](https://playwright.dev/python/)
