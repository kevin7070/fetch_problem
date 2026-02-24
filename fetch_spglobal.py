#!/usr/bin/env python3
"""Fetch S&P Global index data with browser emulation."""

import requests
from typing import Any


def create_browser_session(base_url: str | None = None) -> requests.Session:
    """Create a requests session with browser-like headers."""
    session = requests.Session()

    headers = {
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
        "Priority": "u=0, i",
    }
    session.headers.update(headers)

    if base_url:
        session.get(base_url)

    return session


def fetch_index_data(
    session: requests.Session,
    index_id: str,
    period: str = "tenYearFlag",
    language_id: str = "1",
) -> dict[str, Any]:
    """Fetch index comparison data from S&P Global API."""
    url = "https://www.spglobal.com/spdji/en/util/redesign/get-index-comparison-data.dot"
    params = {
        "compareArray": index_id,
        "periodFlag": period,
        "language_id": language_id,
    }

    # Update headers for same-origin API request
    headers = {
        "Sec-Fetch-Site": "same-origin",
        "Referer": "https://www.spglobal.com/spdji/en/",
    }

    response = session.get(url, params=params, headers=headers)
    response.raise_for_status()

    return response.json()


def main():
    base_url = "https://www.spglobal.com/spdji/en/"
    index_id = "5457755"  # S&P/TSX Composite Index

    print(f"Creating browser session...")
    session = create_browser_session(base_url)

    print(f"Cookies received: {len(session.cookies)}")
    for cookie in session.cookies:
        print(f"  - {cookie.name}: {cookie.value[:30]}...")

    print(f"\nFetching index data for ID: {index_id}")
    data = fetch_index_data(session, index_id)

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
