"""Watch-list matching.

The first version of this tool lower-cased the page text and then looked for
each watch-list entry *as typed* with ``in``. Two things went wrong:

* an entry containing a capital letter (most names of people and places) could
  never match, because the text it was compared with had no capitals left;
* ``in`` is a substring test, so a short entry such as ``eel`` also "matched"
  ``steel`` and ``wheel``.

This module replaces that with one compiled pattern per variant that is

* case-insensitive by default (both sides, not one),
* anchored on word boundaries that understand letters outside ASCII,
* phrase-aware: the words of ``marine protected area`` may be separated by any
  run of spaces, line breaks or hyphens,
* tolerant of the typographic noise found in scraped pages (curly apostrophes,
  non-breaking spaces, decomposed accents).

``site/js/matcher.js`` is a line-for-line port. Both are run against
``tests/cases.json`` so the page demo and this package cannot drift apart.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

# Characters that scraped pages use in place of a plain apostrophe or space.
_APOSTROPHES = "‘’ʼ`´"
_SPACES = "   "
_TRANSLATE = {ord(c): "'" for c in _APOSTROPHES} | {ord(c): " " for c in _SPACES}

# What may sit between the words of a phrase: whitespace or a hyphen/dash.
_GAP = r"[\s\-‐‑‒–]+"
_GAP_SPLIT = re.compile(_GAP)

# "Not a letter, digit or underscore" on each side. Python's \w is Unicode-aware
# for str patterns, so accented and non-Latin letters are handled like a-z.
# The left edge also refuses a letter followed by an apostrophe, so "ambo" is
# not found inside the Swahili "ng'ambo". The right edge allows an apostrophe,
# so "reef" is still found in "the reef's edge".
_LEFT_EDGE = r"(?<!\w)(?<!\w')"
_RIGHT_EDGE = r"(?!\w)"


def normalise(text: str) -> str:
    """Return ``text`` in the form the matcher works on.

    Composes accents (NFC) and straightens apostrophes and non-breaking spaces.
    Offsets reported by :meth:`Matcher.find` refer to this normalised text, so
    highlight that rather than the raw input.
    """
    return unicodedata.normalize("NFC", text).translate(_TRANSLATE)


@dataclass(frozen=True)
class Term:
    """One line of the watch-list: a label and the spellings that count as it."""

    label: str
    variants: tuple[str, ...]


@dataclass(frozen=True)
class Match:
    """One occurrence of a variant in a piece of text."""

    term: str      # the label of the watch-list line
    variant: str   # the spelling that was found
    start: int     # offsets into normalise(text)
    end: int
    text: str      # the matched characters, as they appear in the source


def parse_watchlist(source: str) -> list[Term]:
    """Parse watch-list text.

    One term per line. ``|`` separates spellings of the same term, which is how
    an English and a Swahili form are tied together::

        mangrove | mangroves | mikoko | mkoko

    The first spelling is the label used in reports. Blank lines are ignored, and so
    are comment lines: a ``#`` followed by a space. A ``#`` followed directly by
    a word is a hashtag and is kept. A repeated label is kept once.
    """
    terms: list[Term] = []
    seen: set[str] = set()
    for raw in source.splitlines():
        line = normalise(raw).strip()
        if not line or line == "#" or line.startswith("# "):
            continue
        variants: list[str] = []
        for part in line.split("|"):
            cleaned = " ".join(part.split())
            if cleaned and cleaned.lower() not in (v.lower() for v in variants):
                variants.append(cleaned)
        if not variants or variants[0].lower() in seen:
            continue
        seen.add(variants[0].lower())
        terms.append(Term(label=variants[0], variants=tuple(variants)))
    return terms


def _pattern(variant: str, *, case_sensitive: bool, whole_word: bool) -> re.Pattern[str]:
    words = [re.escape(w) for w in _GAP_SPLIT.split(variant) if w]
    body = _GAP.join(words)
    if whole_word:
        body = _LEFT_EDGE + body + _RIGHT_EDGE
    return re.compile(body, 0 if case_sensitive else re.IGNORECASE)


class Matcher:
    """Find watch-list terms in text.

    >>> m = Matcher(parse_watchlist("eel\\nmangrove | mikoko"))
    >>> [hit.term for hit in m.find("Steel prices rise as MIKOKO planting begins")]
    ['mangrove']
    """

    def __init__(
        self,
        terms: Iterable[Term],
        *,
        case_sensitive: bool = False,
        whole_word: bool = True,
    ) -> None:
        self.terms: Sequence[Term] = tuple(terms)
        self.case_sensitive = case_sensitive
        self.whole_word = whole_word
        self._compiled = [
            (term, variant, _pattern(variant, case_sensitive=case_sensitive, whole_word=whole_word))
            for term in self.terms
            for variant in term.variants
            if _GAP_SPLIT.sub("", variant)
        ]

    def find(self, text: str) -> list[Match]:
        """Every occurrence of every variant, in reading order.

        Matches of different terms may overlap (``reef`` inside ``coral reef``);
        callers that highlight should merge overlapping spans.
        """
        haystack = normalise(text)
        found: list[Match] = []
        for term, variant, pattern in self._compiled:
            for hit in pattern.finditer(haystack):
                found.append(Match(term.label, variant, hit.start(), hit.end(), hit.group(0)))
        found.sort(key=lambda m: (m.start, -m.end))  # stable: ties keep watch-list order
        return found

    def terms_found(self, text: str) -> list[str]:
        """Labels of the terms present in ``text``, in watch-list order."""
        present = {m.term for m in self.find(text)}
        return [t.label for t in self.terms if t.label in present]


def naive_terms_found(keywords: Iterable[str], text: str) -> list[str]:
    """The original behaviour, kept only so the tests can show what it got wrong.

    Lower-cases the text, leaves the keywords alone, and uses a substring test.
    """
    body = text.lower()
    return [kw for kw in keywords if kw in body]
