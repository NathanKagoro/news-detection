# News Detection

A media-monitoring tool, presented as a concept page. A watch-list of names
and phrases goes in; a morning digest of the headlines that mention them comes
out. It was written to read East African news sites and social accounts in
English and Swahili.

Concept page: https://nathankagoro.github.io/news-detection/

## What is real and what is invented

The original was built for a private client brief. Its watch-list, sources and
results are **not** in this repository and never have been.

- **Real:** the approach (sources, fetch, extract, match, digest), the kinds of
  sources it read, the mistakes it made and the lessons drawn from them.
- **Invented:** everything you can see or run. The page and the examples use a
  made-up brief, a conservation charity following coverage of reefs, mangroves
  and coastal fishing. The outlets ("The Coastal Courier", "Gazeti la
  Mwambao" and the rest), headlines, people and social accounts are fictional.
- **Not shown:** any figures from real runs. The counts on the demo board are
  computed live from the invented clippings.

## What is in here

| Path | What it is |
| --- | --- |
| `site/` | The concept page. Static HTML, CSS and JavaScript, no build step. |
| `site/js/matcher.js` | The watch-list matcher, ported from Python, used by the demo. |
| `monitor/` | A small Python package showing the approach with the matcher fixed. Standard library only. |
| `examples/` | An example watch-list, an example sources file (example.org addresses only) and three invented article pages. |
| `tests/` | pytest suites. `tests/cases.json` holds the matcher cases shared by Python and JavaScript. |
| `site-tests/` | `node --test` suite for the JavaScript matcher, run against the same cases. |
| `tools/` | Local server, screenshot script and social preview renderer. |

### The bug the matcher fixes

The first version lower-cased each page and then looked for every keyword
exactly as typed, using a substring test. So:

1. any keyword containing a capital letter (most names of people and places)
   could never match, and
2. short keywords matched inside longer words: `eel` in "steel", and in
   Swahili `kasa` (turtle) in "mikasa" (incidents).

`monitor/matcher.py` ignores case on both sides, matches whole words using
Unicode-aware boundaries, lets the words of a phrase be separated by spaces,
line breaks or hyphens, straightens curly apostrophes, composes accents, and
lets one line hold several spellings of the same term:

```
mangrove | mangroves | mikoko | mkoko
```

## Run it

Python 3.10 or later, no third-party packages needed to run.

```
# Offline, on the invented example pages
python -m monitor --keywords examples/keywords.example.txt "examples/pages/*/*.html"

# Live, from your own sources file (format in examples/sources.example.txt)
python -m monitor --keywords my-keywords.txt --sources my-sources.txt --csv outputs/today.csv
```

The fetcher identifies itself, honours robots.txt and waits between requests
to the same host. Check each site's terms before adding it to a sources file.

## Test it

```
python -m pip install -r requirements-dev.txt
python -m pytest -q        # matcher, extractor, digest, command line
npm ci
npm test                   # the page's JavaScript matcher, same cases
npm run screenshots        # 1440, 390 and 360 px into shots/ (needs Chrome)
```

## Preview the page

```
npm run serve              # http://127.0.0.1:4360/news-detection/
```

The page is served from the `/news-detection/` subfolder, as on GitHub Pages.

## Hosting

`.github/workflows/pages.yml` publishes `site/` to GitHub Pages on every push
to `main`. `.github/workflows/ci.yml` runs both test suites and takes
screenshots on every push and pull request.

Fonts: Libre Caslon Condensed, Cutive Mono and UnifrakturCook, all under the
SIL Open Font License (see `site/fonts/LICENSE.txt`).
