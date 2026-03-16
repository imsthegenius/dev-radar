#!/usr/bin/env python3
"""Fetch GitHub trending repos. Scrapes github.com/trending with API fallback.

Usage:
    python3 github_trending.py                              # All languages, weekly
    python3 github_trending.py --languages=python,typescript
    python3 github_trending.py --since=daily
    python3 github_trending.py --no-cache
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from lib.cache import load_cache, save_cache, get_cache_key, ensure_cache_dir
from lib.http import get, get_json, HTTPError, log


# ---------------------------------------------------------------------------
# HTML parser for github.com/trending
# ---------------------------------------------------------------------------

class TrendingParser(HTMLParser):
    """Extract repo data from GitHub trending page HTML."""

    def __init__(self):
        super().__init__()
        self.repos = []
        self._in_article = False
        self._in_repo_link = False
        self._in_description = False
        self._in_stars_today = False
        self._in_language = False
        self._in_total_stars = False
        self._current = {}
        self._depth = 0
        self._capture_text = ""
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        if tag == "article" and "Box-row" in cls:
            self._in_article = True
            self._current = {}

        if not self._in_article:
            return

        # Repo name link: h2 > a with href like /owner/repo
        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            if tag == "a" and href.count("/") == 2 and href.startswith("/"):
                # Check parent is h2 by looking at class pattern
                if not self._current.get("name"):
                    parts = href.strip("/").split("/")
                    if len(parts) == 2:
                        self._current["name"] = f"{parts[0]}/{parts[1]}"
                        self._current["url"] = f"https://github.com{href}"

        # Description paragraph
        if tag == "p":
            self._in_description = True
            self._capture_text = ""

        # Language span (inside a small with specific class)
        if tag == "span" and "d-inline-block" in cls and "ml-0" in cls:
            self._in_language = True
            self._capture_text = ""

        # Stars today (float-sm-right)
        if tag == "span" and "float-sm-right" in cls:
            self._in_stars_today = True
            self._capture_text = ""

        # Total stars: svg with octicon-star, next sibling text
        if tag == "svg" and "octicon-star" in cls:
            self._in_total_stars = True
            self._capture_text = ""

        # Also catch the <a> that wraps total stars count
        if tag == "a" and self._in_article and "href" in attrs_dict:
            href = attrs_dict["href"]
            if href.endswith("/stargazers"):
                self._in_total_stars = True
                self._capture_text = ""

    def handle_endtag(self, tag):
        if tag == "p" and self._in_description:
            self._in_description = False
            desc = self._capture_text.strip()
            if desc and not self._current.get("description"):
                self._current["description"] = desc

        if tag == "span" and self._in_language:
            self._in_language = False
            lang = self._capture_text.strip()
            if lang:
                self._current["language"] = lang

        if tag == "span" and self._in_stars_today:
            self._in_stars_today = False
            text = self._capture_text.strip()
            match = re.search(r"([\d,]+)", text)
            if match:
                self._current["stars_today"] = int(match.group(1).replace(",", ""))

        if tag == "a" and self._in_total_stars:
            self._in_total_stars = False
            text = self._capture_text.strip()
            match = re.search(r"([\d,]+)", text)
            if match:
                self._current["stars"] = int(match.group(1).replace(",", ""))

        if tag == "article" and self._in_article:
            self._in_article = False
            if self._current.get("name"):
                repo = {
                    "name": self._current.get("name", ""),
                    "url": self._current.get("url", ""),
                    "description": self._current.get("description", ""),
                    "language": self._current.get("language", ""),
                    "stars": self._current.get("stars", 0),
                    "stars_today": self._current.get("stars_today", 0),
                    "forks": self._current.get("forks", 0),
                }
                self.repos.append(repo)
            self._current = {}

    def handle_data(self, data):
        if self._in_description or self._in_language or self._in_stars_today or self._in_total_stars:
            self._capture_text += data


def scrape_trending(since: str = "weekly", languages: list = None) -> list:
    """Scrape github.com/trending and return list of repo dicts."""
    repos = []

    urls = []
    if languages:
        for lang in languages:
            urls.append(f"https://github.com/trending/{lang.lower()}?since={since}")
    else:
        urls.append(f"https://github.com/trending?since={since}")

    for url in urls:
        log(f"Scraping {url}")
        try:
            html = get(url, headers={"Accept": "text/html"})
            parser = TrendingParser()
            parser.feed(html)
            repos.extend(parser.repos)
        except HTTPError as e:
            log(f"Scrape failed for {url}: {e}")
            continue

    # Deduplicate by name (if multiple language pages)
    seen = set()
    unique = []
    for r in repos:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
    return unique


# ---------------------------------------------------------------------------
# Fallback: GitHub Search API
# ---------------------------------------------------------------------------

def api_fallback(since: str = "weekly", languages: list = None) -> list:
    """Use GitHub Search API as fallback when scraping fails."""
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 7)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    query_parts = [f"created:>{cutoff}"]
    if languages:
        lang_query = " ".join(f"language:{l}" for l in languages)
        query_parts.append(lang_query)

    query = " ".join(query_parts)
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=25"

    log(f"API fallback: {url}")
    try:
        data = get_json(url, headers={"Accept": "application/vnd.github.v3+json"})
    except HTTPError as e:
        log(f"API fallback failed: {e}")
        return []

    repos = []
    for item in data.get("items", [])[:25]:
        repos.append({
            "name": item.get("full_name", ""),
            "url": item.get("html_url", ""),
            "description": item.get("description", "") or "",
            "language": item.get("language", "") or "",
            "stars": item.get("stargazers_count", 0),
            "stars_today": 0,  # API doesn't provide this
            "forks": item.get("forks_count", 0),
        })
    return repos


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub trending repos")
    parser.add_argument("--languages", default="", help="Comma-separated languages (e.g. python,typescript)")
    parser.add_argument("--since", default="weekly", choices=["daily", "weekly", "monthly"], help="Time range")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    args = parser.parse_args()

    languages = [l.strip() for l in args.languages.split(",") if l.strip()] if args.languages else []
    since = args.since
    use_cache = not args.no_cache

    ensure_cache_dir()

    # Check cache
    cache_key = get_cache_key(",".join(sorted(languages)), since)
    if use_cache:
        cached = load_cache(cache_key)
        if cached:
            cached["cached"] = True
            json.dump(cached, sys.stdout, indent=2)
            return

    # Try scraping first
    repos = scrape_trending(since, languages or None)
    source = "scrape"

    # Fallback to API if scraping returned nothing
    if not repos:
        log("Scraping returned 0 repos, trying API fallback")
        repos = api_fallback(since, languages or None)
        source = "api_fallback"

    result = {
        "source": source,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cached": False,
        "repos": repos,
    }

    # Cache result
    if repos:
        save_cache(cache_key, result)

    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
