"""Command line: ``python -m monitor``.

Two ways to use it.

Offline, on saved pages (nothing leaves your machine)::

    python -m monitor --keywords examples/keywords.example.txt examples/pages/*.html

Live, from a sources file (see ``examples/sources.example.txt``)::

    python -m monitor --keywords my-keywords.txt --sources my-sources.txt --csv outputs/today.csv
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from .digest import Item, flag, to_csv, to_digest
from .extract import extract_article, extract_links
from .fetch import Fetcher
from .matcher import Matcher, parse_watchlist


def read_sources(path: Path) -> list[tuple[str, str, str]]:
    """Lines of ``name, front page address, article path fragment`` (the last is optional)."""
    sources = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            raise SystemExit(f"{path}: expected 'name, address[, path fragment]' but got: {line}")
        sources.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return sources


def run_offline(patterns: list[str], matcher: Matcher) -> list[Item]:
    items = []
    for pattern in patterns:
        for name in sorted(glob.glob(pattern)) or [pattern]:
            path = Path(name)
            article = extract_article(path.read_text(encoding="utf-8"), url=path.as_posix())
            item = flag(article_source(path), article, matcher)
            if item:
                items.append(item)
    return items


def article_source(path: Path) -> str:
    folder = path.parent.name
    return folder.replace("-", " ") if folder not in {"", "."} else "local file"


def run_live(sources: list[tuple[str, str, str]], matcher: Matcher, limit: int, delay: float) -> list[Item]:
    fetcher = Fetcher(delay_seconds=delay)
    items = []
    for name, address, fragment in sources:
        front = fetcher.get(address)
        if not front.ok:
            print(f"[skip] {name}: {front.error}", file=sys.stderr)
            continue
        for link in extract_links(front.html, address, contains=fragment)[:limit]:
            page = fetcher.get(link)
            if not page.ok:
                print(f"[skip] {link}: {page.error}", file=sys.stderr)
                continue
            item = flag(name, extract_article(page.html, url=link), matcher)
            if item:
                items.append(item)
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="monitor", description="Flag news items that mention a watch-list.")
    parser.add_argument("pages", nargs="*", help="saved HTML pages to check offline")
    parser.add_argument("--keywords", required=True, type=Path, help="watch-list file, one term per line")
    parser.add_argument("--sources", type=Path, help="sources file for a live run")
    parser.add_argument("--csv", type=Path, help="also write the flagged items to this CSV file")
    parser.add_argument("--limit", type=int, default=10, help="articles to read per source (default 10)")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between requests to one host")
    parser.add_argument("--case-sensitive", action="store_true")
    parser.add_argument("--substring", action="store_true", help="match inside longer words (not recommended)")
    args = parser.parse_args(argv)

    if not args.pages and not args.sources:
        parser.error("give saved pages to check, or --sources for a live run")

    terms = parse_watchlist(args.keywords.read_text(encoding="utf-8"))
    matcher = Matcher(terms, case_sensitive=args.case_sensitive, whole_word=not args.substring)

    items = run_offline(args.pages, matcher)
    if args.sources:
        items += run_live(read_sources(args.sources), matcher, args.limit, args.delay)

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        args.csv.write_text(to_csv(items), encoding="utf-8", newline="")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(to_digest(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
