#!/usr/bin/env python3
"""Fetch S&P Global index data using Playwright Firefox."""

import json

from playwright.sync_api import sync_playwright


def fetch_index_data(
    index_id: str,
    period: str = "tenYearFlag",
    language_id: str = "1",
) -> dict:
    """Fetch index data using Playwright Firefox to bypass Akamai bot protection."""
    api_url = (
        "https://www.spglobal.com/spdji/en/util/redesign/get-index-comparison-data.dot"
        f"?compareArray={index_id}&periodFlag={period}&language_id={language_id}"
    )

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()

        # Capture API response
        result = {}

        def on_response(response):
            if "get-index-comparison-data" in response.url:
                try:
                    result["data"] = response.json()
                    result["status"] = response.status
                    print(f"  [intercepted] status: {response.status}")
                except Exception as e:
                    result["error"] = str(e)

        page.on("response", on_response)

        try:
            print("Navigating to API URL...")
            page.goto(api_url, timeout=60000, wait_until="domcontentloaded")

            print("Waiting for JS challenge...")
            page.wait_for_timeout(10000)

            print(f"  URL: {page.url}")
            print(f"  Title: {page.title()}")

            if "data" not in result:
                body = page.inner_text("body")
                try:
                    result["data"] = json.loads(body)
                except json.JSONDecodeError:
                    result["data"] = {"error": True, "body": body[:1000]}
        except Exception as e:
            print(f"  Error: {e}")
            result.setdefault("data", {"error": True, "message": str(e)})
        finally:
            browser.close()

    return result.get("data", {"error": True, "message": "no response"})


def main():
    index_id = "5457755"  # S&P/TSX Composite Index

    print(f"Fetching index data for ID: {index_id}")
    print(f"{'='*60}\n")

    data = fetch_index_data(index_id)

    print(f"\n{'='*60}")
    if data.get("error"):
        print("FAILED")
        print(json.dumps(data, indent=2, default=str))
    else:
        print("FULL JSON RESPONSE")
        print(f"{'='*60}")
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
