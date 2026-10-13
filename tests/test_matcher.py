"""Matcher tests. The table-driven cases are shared with the JavaScript port."""

import json
from pathlib import Path

import pytest

from monitor.matcher import Matcher, naive_terms_found, normalise, parse_watchlist

CASES = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_shared_case(case):
    options = case.get("options", {})
    matcher = Matcher(
        parse_watchlist(case["watchlist"]),
        case_sensitive=options.get("case_sensitive", False),
        whole_word=options.get("whole_word", True),
    )
    assert [[m.term, m.text] for m in matcher.find(case["text"])] == case["expect"]


def test_offsets_point_into_normalised_text():
    text = "Wavuvi wa ng’ambo walipanda mikoko"
    matcher = Matcher(parse_watchlist("ng'ambo\nmikoko"))
    clean = normalise(text)
    for match in matcher.find(text):
        assert clean[match.start : match.end] == match.text


def test_terms_found_keeps_watchlist_order_and_reports_each_term_once():
    matcher = Matcher(parse_watchlist("reef\nmangrove | mikoko\nKilwa"))
    text = "Kilwa: mikoko and mangrove planting beside the reef. KILWA again."
    assert matcher.terms_found(text) == ["reef", "mangrove", "Kilwa"]


def test_watchlist_variants_are_kept_in_order_without_repeats():
    (term,) = parse_watchlist("  sea turtle |  sea   turtles | kasa | Kasa |  ")
    assert term.label == "sea turtle"
    assert term.variants == ("sea turtle", "sea turtles", "kasa")


def test_original_behaviour_missed_capitalised_keywords():
    """Why the rewrite exists: the old code could never match a keyword with a capital."""
    text = "Fishers in Kilwa extend the closure"
    assert naive_terms_found(["Kilwa"], text) == []
    assert Matcher(parse_watchlist("Kilwa")).terms_found(text) == ["Kilwa"]


def test_original_behaviour_matched_inside_longer_words():
    text = "Steel prices rise for a third month"
    assert naive_terms_found(["eel"], text) == ["eel"]
    assert Matcher(parse_watchlist("eel")).terms_found(text) == []


def test_example_watchlist_parses():
    source = (Path(__file__).parent.parent / "examples" / "keywords.example.txt").read_text(encoding="utf-8")
    labels = [t.label for t in parse_watchlist(source)]
    assert "mangrove" in labels and "Pemba Channel" in labels
    assert len(labels) == len({label.lower() for label in labels})
