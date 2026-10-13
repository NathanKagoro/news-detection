"""Turn matched articles into the two things a reader wants: a CSV and a digest."""

from __future__ import annotations

import csv
import io
import textwrap
from dataclasses import dataclass
from typing import Iterable

from .extract import Article
from .matcher import Matcher

FIELDS = ["source", "title", "author", "summary", "url", "terms_found"]


@dataclass(frozen=True)
class Item:
    source: str
    article: Article
    terms: tuple[str, ...]


def flag(source: str, article: Article, matcher: Matcher) -> Item | None:
    """Return an item if the headline, summary or body mentions a watched term."""
    haystack = "\n".join([article.title, article.summary, article.text])
    terms = matcher.terms_found(haystack)
    return Item(source, article, tuple(terms)) if terms else None


def to_csv(items: Iterable[Item]) -> str:
    """One row per flagged article.

    The header is written even when nothing matched. The original took its
    column names from the first row, so a quiet morning produced an empty file
    and a morning with mixed sources produced rows that did not fit the header.
    """
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for item in items:
        writer.writerow(
            {
                "source": item.source,
                "title": item.article.title,
                "author": item.article.author,
                "summary": item.article.summary,
                "url": item.article.url,
                "terms_found": "; ".join(item.terms),
            }
        )
    return out.getvalue()


def to_digest(items: Iterable[Item], *, heading: str = "MORNING DIGEST", width: int = 72) -> str:
    """A plain-text digest grouped by source, readable in an email or a terminal."""
    items = list(items)
    lines = [heading, "=" * len(heading), ""]
    if not items:
        lines.append("Nothing on the watch-list this morning.")
        return "\n".join(lines) + "\n"
    by_source: dict[str, list[Item]] = {}
    for item in items:
        by_source.setdefault(item.source, []).append(item)
    for source, group in by_source.items():
        lines.append(source.upper())
        for item in group:
            lines.extend(textwrap.wrap(item.article.title, width, initial_indent="  * ", subsequent_indent="    "))
            lines.extend(textwrap.wrap(item.article.summary, width, initial_indent="    ", subsequent_indent="    "))
            lines.append(f"    Matched: {', '.join(item.terms)}")
            if item.article.url:
                lines.append(f"    {item.article.url}")
            lines.append("")
    count = len(items)
    lines.append(f"{count} item{'s' if count != 1 else ''} flagged.")
    return "\n".join(lines) + "\n"
