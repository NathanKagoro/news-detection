"""A small media-monitoring example: watch-list in, digest of matching items out."""

from .digest import Item, flag, to_csv, to_digest
from .extract import Article, extract_article, extract_links
from .matcher import Match, Matcher, Term, normalise, parse_watchlist

__all__ = [
    "Article",
    "Item",
    "Match",
    "Matcher",
    "Term",
    "extract_article",
    "extract_links",
    "flag",
    "normalise",
    "parse_watchlist",
    "to_csv",
    "to_digest",
]
