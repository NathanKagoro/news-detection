"""One generic article extractor.

The original tool had a hand-written scraper per outlet, each a near copy of
the last with different CSS classes, and each broke when its site was
redesigned. This is the opposite trade: one extractor that relies on the
metadata almost every news page publishes for link previews, and falls back to
the visible page when that is missing. It uses only the standard library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

# Text inside these elements is never article copy.
_SKIP = {"script", "style", "noscript", "template", "svg", "nav", "footer", "aside", "form", "header"}
_VOID = {"meta", "link", "br", "img", "input", "hr", "source", "area", "base", "col", "embed", "track", "wbr"}
_BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "blockquote", "section", "article", "figcaption"}
_BYLINE_CLASS = re.compile(r"(?<![a-z])(author|byline)(?![a-z])", re.IGNORECASE)
_BY_PREFIX = re.compile(r"^\s*(by|na)\s+", re.IGNORECASE)  # "na" is the Swahili byline word
_MIN_SUMMARY = 60

NO_AUTHOR = "Not listed"
NO_SUMMARY = "No summary available"


@dataclass(frozen=True)
class Article:
    url: str
    title: str
    author: str
    summary: str
    text: str  # visible copy, used for matching


def _squash(text: str) -> str:
    return " ".join(text.split())


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.h1 = ""
        self.byline = ""
        self.paragraphs: list[str] = []
        self.chunks: list[str] = []
        self.links: list[str] = []
        self._stack: list[tuple[str, bool, bool]] = []  # (tag, skipped, is_byline)
        self._buffer: list[str] | None = None
        self._buffer_tag = ""

    # Helpers -----------------------------------------------------------------
    def _skipping(self) -> bool:
        return any(skipped for _, skipped, _ in self._stack)

    def _in_byline(self) -> bool:
        return any(byline for _, _, byline in self._stack)

    # HTMLParser hooks --------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content") and key not in self.meta:
                self.meta[key] = _squash(a["content"])
            return
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in _BLOCK:
            self.chunks.append("\n")
        if tag in _VOID:
            return
        is_byline = bool(
            _BYLINE_CLASS.search(a.get("class", ""))
            or a.get("rel", "").lower() == "author"
            or a.get("itemprop", "").lower() == "author"
        )
        self._stack.append((tag, tag in _SKIP, is_byline))
        if tag in {"title", "h1", "p"} and self._buffer is None:
            self._buffer, self._buffer_tag = [], tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self._buffer_tag and self._buffer is not None:
            text = _squash("".join(self._buffer))
            if tag == "title" and not self.title:
                self.title = text
            elif tag == "h1" and not self.h1:
                self.h1 = text
            elif tag == "p" and text and not self._skipping():
                self.paragraphs.append(text)
            self._buffer, self._buffer_tag = None, ""
        for i in range(len(self._stack) - 1, -1, -1):  # tolerate unclosed tags
            if self._stack[i][0] == tag:
                del self._stack[i:]
                break
        if tag in _BLOCK:
            self.chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._buffer is not None:
            self._buffer.append(data)
        if self._stack and self._stack[-1][0] == "title":
            return
        if self._skipping():
            return
        if self._in_byline() and not self.byline and data.strip():
            self.byline = _squash(data)
        self.chunks.append(data)


def _parse(html: str) -> _PageParser:
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    return parser


def extract_article(html: str, url: str = "") -> Article:
    """Pull title, author, summary and visible text out of one page.

    Order of preference, most reliable first:

    * title: ``og:title``, then the first ``<h1>``, then ``<title>``
    * author: ``<meta name="author">``, then ``article:author`` when it is a
      name rather than a profile link, then the first element marked as a
      byline (``rel="author"``, ``itemprop="author"``, or a class containing
      ``author`` or ``byline``)
    * summary: ``og:description``, then ``<meta name="description">``, then the
      first paragraph long enough to be a sentence
    """
    page = _parse(html)
    meta = page.meta

    title = meta.get("og:title") or page.h1 or page.title or "Untitled"

    author = meta.get("author", "")
    if not author and not meta.get("article:author", "").startswith("http"):
        author = meta.get("article:author", "")
    if not author:
        author = page.byline
    author = _BY_PREFIX.sub("", author).strip() or NO_AUTHOR

    summary = meta.get("og:description") or meta.get("description") or ""
    if not summary:
        summary = next((p for p in page.paragraphs if len(p) >= _MIN_SUMMARY), "")
    if not summary and page.paragraphs:
        summary = page.paragraphs[0]

    lines = (_squash(line) for line in "".join(page.chunks).split("\n"))
    text = "\n".join(line for line in lines if line)

    return Article(url=url, title=title, author=author, summary=summary or NO_SUMMARY, text=text)


def extract_links(html: str, base_url: str, contains: str = "") -> list[str]:
    """Absolute, de-duplicated links on the same host as ``base_url``.

    ``contains`` narrows the result to article paths, for example ``/news/``.
    Order on the page is kept, so the first links are the most prominent.
    """
    host = urlparse(base_url).netloc
    seen: dict[str, None] = {}
    for href in _parse(html).links:
        absolute = urldefrag(urljoin(base_url, href.strip())).url
        parts = urlparse(absolute)
        if parts.scheme not in {"http", "https"} or parts.netloc != host:
            continue
        if contains and contains not in parts.path:
            continue
        seen.setdefault(absolute)
    return list(seen)
