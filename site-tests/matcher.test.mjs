// Runs the JavaScript matcher against the same cases as the Python one.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createMatcher, mergeSpans, normalise, parseWatchlist, segments } from '../site/js/matcher.js';

const { cases } = JSON.parse(readFileSync(new URL('../tests/cases.json', import.meta.url), 'utf8'));

for (const c of cases) {
  test(`shared case: ${c.name}`, () => {
    const options = c.options ?? {};
    const matcher = createMatcher(parseWatchlist(c.watchlist), {
      caseSensitive: options.case_sensitive ?? false,
      wholeWord: options.whole_word ?? true,
    });
    assert.deepEqual(matcher.find(c.text).map((m) => [m.term, m.text]), c.expect);
  });
}

test('offsets point into the normalised text', () => {
  const text = 'Wavuvi wa ng’ambo walipanda mikoko';
  const clean = normalise(text);
  for (const m of createMatcher(parseWatchlist("ng'ambo\nmikoko")).find(text)) {
    assert.equal(clean.slice(m.start, m.end), m.text);
  }
});

test('termsFound keeps watch-list order and reports each term once', () => {
  const matcher = createMatcher(parseWatchlist('reef\nmangrove | mikoko\nKilwa'));
  const text = 'Kilwa: mikoko and mangrove planting beside the reef. KILWA again.';
  assert.deepEqual(matcher.termsFound(text), ['reef', 'mangrove', 'Kilwa']);
});

test('watch-list variants are kept in order without repeats', () => {
  const [term] = parseWatchlist('  sea turtle |  sea   turtles | kasa | Kasa |  ');
  assert.equal(term.label, 'sea turtle');
  assert.deepEqual(term.variants, ['sea turtle', 'sea turtles', 'kasa']);
});

test('overlapping matches merge into one highlight that names both terms', () => {
  const text = 'The coral reef recovers';
  const matches = createMatcher(parseWatchlist('reef\ncoral reef')).find(text);
  assert.deepEqual(mergeSpans(matches), [{ start: 4, end: 14, terms: ['coral reef', 'reef'] }]);
});

test('segments rebuild the whole text with nothing lost', () => {
  const text = 'Mikoko na matumbawe: reef-building corals near Kilwa.';
  const matches = createMatcher(parseWatchlist('mangrove | mikoko\nreef\nKilwa')).find(text);
  const parts = segments(text, matches);
  assert.equal(parts.map((p) => p.text).join(''), normalise(text));
  assert.deepEqual(parts.filter((p) => p.terms).map((p) => p.text), ['Mikoko', 'reef', 'Kilwa']);
});

test('the example watch-list parses in JavaScript as it does in Python', () => {
  const source = readFileSync(new URL('../examples/keywords.example.txt', import.meta.url), 'utf8');
  const labels = parseWatchlist(source).map((t) => t.label);
  assert.ok(labels.includes('mangrove') && labels.includes('Pemba Channel'));
  assert.equal(new Set(labels.map((l) => l.toLowerCase())).size, labels.length);
});
