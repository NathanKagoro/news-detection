"""Polite fetching with the standard library.

The original fetched with no pause, no identification and a bare ``except``
that hid every failure. This version identifies itself, honours robots.txt,
waits between requests to the same host, and reports why a fetch failed.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

USER_AGENT = "news-detection-example/1.0 (+https://github.com/NathanKagoro/news-detection)"


@dataclass(frozen=True)
class FetchResult:
    url: str
    html: str | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.html is not None


class Fetcher:
    def __init__(self, *, delay_seconds: float = 2.0, timeout_seconds: float = 10.0) -> None:
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last_request: dict[str, float] = {}

    def _allowed(self, url: str) -> bool:
        parts = urlparse(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            rules = urllib.robotparser.RobotFileParser(origin + "/robots.txt")
            try:
                rules.read()
            except (OSError, ValueError):
                rules = None  # no readable robots.txt: nothing is disallowed
            self._robots[origin] = rules
        rules = self._robots[origin]
        return rules is None or rules.can_fetch(USER_AGENT, url)

    def _wait(self, host: str) -> None:
        elapsed = time.monotonic() - self._last_request.get(host, float("-inf"))
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self._last_request[host] = time.monotonic()

    def get(self, url: str) -> FetchResult:
        if urlparse(url).scheme not in {"http", "https"}:
            return FetchResult(url, None, "not an http(s) address")
        if not self._allowed(url):
            return FetchResult(url, None, "disallowed by robots.txt")
        self._wait(urlparse(url).netloc)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return FetchResult(url, response.read().decode(charset, errors="replace"))
        except urllib.error.HTTPError as exc:
            return FetchResult(url, None, f"HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return FetchResult(url, None, str(getattr(exc, "reason", exc)))
