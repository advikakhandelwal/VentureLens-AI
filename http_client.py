"""External data helpers for LaunchPilot AI: keyless web search + ASI:One client."""

import os
import re
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _resolve_ddg_url(href: str) -> str:
    """Extract the real target URL from a DuckDuckGo redirect link."""
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    if "uddg=" in href:
        try:
            values = parse_qs(urlparse(href).query).get("uddg", [])
            return values[0] if values else ""
        except ValueError:
            return ""
    if href.startswith("http"):
        return href
    return ""


def wikipedia_search(query: str, max_results: int = 3) -> list:
    """Fallback search using the public Wikipedia API (no key required)."""
    try:
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max(1, max_results),
                "format": "json",
            },
            headers=BROWSER_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        hits = response.json().get("query", {}).get("search", [])
        results = []
        for hit in hits:
            title = hit.get("title", "")
            url = "https://en.wikipedia.org/wiki/" + quote_plus(title.replace(" ", "_"))
            snippet = re.sub(r"<[^>]+>", "", hit.get("snippet", ""))
            results.append(
                {"title": title, "url": url, "snippet": snippet[:320], "source": "wikipedia"}
            )
        return results
    except (requests.RequestException, ValueError):
        return []


def web_search(query: str, max_results: int = 5) -> list:
    """Best-effort live web search: DuckDuckGo HTML results with a Wikipedia fallback."""
    results = []
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=BROWSER_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for block in soup.select("div.result")[: max_results * 3]:
            anchor = block.select_one("a.result__a")
            if anchor is None:
                continue
            title = anchor.get_text(" ", strip=True)
            url = _resolve_ddg_url(anchor.get("href") or "")
            if not title or not url:
                continue
            snippet_el = block.select_one("a.result__snippet") or block.select_one(
                ".result__snippet"
            )
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
            results.append({"title": title, "url": url, "snippet": snippet[:320], "source": "web"})
            if len(results) >= max_results:
                break
    except requests.RequestException:
        pass
    if len(results) < max_results:
        results.extend(wikipedia_search(query, max_results=max_results - len(results)))
    return results[:max_results]


def ask_asi1(messages: list, model: str = "asi1", max_tokens: int = 4096) -> str:
    """Call ASI:One using Agentverse-injected credentials and return the reply text."""
    client = OpenAI(
        api_key=os.environ["ASI1_API_KEY"],
        base_url=os.environ["ASI1_BASE_URL"],
    )
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content or ""
