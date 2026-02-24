#!/usr/bin/env python3
"""Fetch S&P Global index data with httpx HTTP/2."""

import httpx
from typing import Any


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
}


def fetch_index_data(
    index_id: str,
    period: str = "tenYearFlag",
    language_id: str = "1",
) -> dict[str, Any]:
    """Fetch index comparison data using HTTP/2."""
    base_url = "https://www.spglobal.com"

    with httpx.Client(http2=True, headers=HEADERS, follow_redirects=True) as client:
        # Visit main page first to get cookies
        print("Visiting main page...")
        resp = client.get(f"{base_url}/spdji/en/")
        print(f"Main page status: {resp.status_code}")
        print(f"Cookies: {list(client.cookies.keys())}")

        # Fetch API
        print("\nFetching API...")
        api_url = f"{base_url}/spdji/en/util/redesign/get-index-comparison-data.dot"
        params = {
            "compareArray": index_id,
            "periodFlag": period,
            "language_id": language_id,
        }
        headers = {
            "Sec-Fetch-Site": "same-origin",
            "Referer": f"{base_url}/spdji/en/",
        }

        resp = client.get(api_url, params=params, headers=headers)
        print(f"API status: {resp.status_code}")

        resp.raise_for_status()
        return resp.json()


def main():
    index_id = "5457755"  # S&P/TSX Composite Index

    print(f"Fetching index data for ID: {index_id}\n")
    data = fetch_index_data(index_id)

    print(f"\nStatus: {data.get('status')}")
    print(f"Messages: {data.get('serviceMessages')}")

    if data.get("status"):
        perf = data["performanceComparisonHolder"]["indexPerformanceForComparison"][0]
        print(f"\nIndex: {perf['indexName']}")
        print(f"Index Value: {perf['indexValue']:.2f}")
        print(f"Daily Return: {perf['dailyReturn']:.4f}%")
        print(f"YTD Return: {perf['yearToDateReturn']:.4f}%")
        print(f"1Y Return: {perf['oneYearReturn']:.4f}%")


if __name__ == "__main__":
    main()
