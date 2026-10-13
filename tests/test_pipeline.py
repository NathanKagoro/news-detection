"""Extractor, digest and command-line tests, run on the invented example pages."""

import csv
import io
from pathlib import Path

from monitor.__main__ import main
from monitor.digest import FIELDS, flag, to_csv, to_digest
from monitor.extract import NO_AUTHOR, NO_SUMMARY, extract_article, extract_links
from monitor.matcher import Matcher, parse_watchlist

ROOT = Path(__file__).parent.parent
PAGES = ROOT / "examples" / "pages"
KEYWORDS = ROOT / "examples" / "keywords.example.txt"


def page(name: str) -> str:
    return (PAGES / name).read_text(encoding="utf-8")


def example_matcher() -> Matcher:
    return Matcher(parse_watchlist(KEYWORDS.read_text(encoding="utf-8")))


def test_metadata_is_preferred_when_present():
    article = extract_article(page("the-coastal-courier/kilwa-octopus-closure.html"))
    assert article.title == "Kilwa fishers vote to extend octopus closure"
    assert article.author == "Amina Mbwana"
    assert article.summary.startswith("Three villages will keep their reef flats shut")


def test_fallbacks_when_metadata_is_thin():
    article = extract_article(page("gazeti-la-mwambao/mikoko-rufiji.html"))
    assert article.title == "Mikoko elfu kumi yapandwa Rufiji"
    assert article.author == "Juma Shehe"  # Swahili "Na" byline prefix removed
    assert article.summary.startswith("Vikundi vya wanawake vimepanda miche ya mikoko")


def test_bare_page_gets_placeholders_not_errors():
    article = extract_article("<p>Short.</p>")
    assert (article.title, article.author, article.summary) == ("Untitled", NO_AUTHOR, "Short.")
    assert extract_article("").summary == NO_SUMMARY


def test_scripts_navigation_and_footers_are_not_article_text():
    article = extract_article(page("the-coastal-courier/kilwa-octopus-closure.html"))
    assert "analytics" not in article.text
    assert "Steel City" not in article.text
    assert "invented newspaper" not in article.text
    assert "voted to keep their reef flats closed" in article.text


def test_entities_and_unclosed_tags_are_handled():
    html = "<h1>Reef &amp; shore</h1><p>First paragraph, left open<p>Caf&eacute; by the harbour, long enough to be a summary sentence in its own right."
    article = extract_article(html)
    assert article.title == "Reef & shore"
    assert "Café by the harbour" in article.text


def test_links_are_absolute_same_host_and_unique():
    html = """
      <a href="/news/reef-survey">one</a> <a href="/news/reef-survey#comments">same</a>
      <a href="news/kilwa">relative</a> <a href="/sport/final">other section</a>
      <a href="https://elsewhere.example/news/x">other host</a> <a href="mailto:desk@example.org">mail</a>
    """
    assert extract_links(html, "https://example.org/", contains="/news/") == [
        "https://example.org/news/reef-survey",
        "https://example.org/news/kilwa",
    ]


def test_flag_reports_terms_and_skips_unrelated_pages():
    matcher = example_matcher()
    hit = flag("The Coastal Courier", extract_article(page("the-coastal-courier/kilwa-octopus-closure.html")), matcher)
    assert hit is not None
    assert set(hit.terms) == {"octopus closure", "beach management unit", "small-scale fishers", "seaweed farming", "Kilwa"}
    miss = flag("The Coastal Courier", extract_article(page("the-coastal-courier/steel-prices.html")), matcher)
    assert miss is None  # "eel" is on the list; "Steel", "wheel" and "feel" must not trip it


def test_swahili_page_is_flagged_under_the_english_labels():
    hit = flag("Gazeti la Mwambao", extract_article(page("gazeti-la-mwambao/mikoko-rufiji.html")), example_matcher())
    assert hit is not None
    assert hit.terms == ("mangrove", "sea turtle", "small-scale fishers")


def test_csv_always_has_a_header_and_round_trips():
    assert to_csv([]).strip() == ",".join(FIELDS)
    article = extract_article(page("gazeti-la-mwambao/mikoko-rufiji.html"), url="https://example.org/a")
    hit = flag("Gazeti la Mwambao", article, example_matcher())
    rows = list(csv.DictReader(io.StringIO(to_csv([hit]))))
    assert rows[0]["terms_found"] == "mangrove; sea turtle; small-scale fishers"
    assert rows[0]["url"] == "https://example.org/a"


def test_digest_says_so_when_nothing_matched():
    assert "Nothing on the watch-list this morning." in to_digest([])


def test_command_line_offline_run(tmp_path, capsys):
    out = tmp_path / "run" / "today.csv"
    code = main(["--keywords", str(KEYWORDS), "--csv", str(out), str(PAGES / "*" / "*.html")])
    printed = capsys.readouterr().out
    assert code == 0
    assert "GAZETI LA MWAMBAO" in printed and "THE COASTAL COURIER" in printed
    assert "2 items flagged." in printed
    assert "Steel prices" not in printed
    with out.open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 2
