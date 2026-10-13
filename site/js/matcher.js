// Watch-list matching for the page demo.
//
// A port of monitor/matcher.py. Both are run against tests/cases.json, so the
// demo on the page behaves exactly like the Python package.

const APOSTROPHES = /[‘’ʼ`´]/g;
const SPACES = /[   ]/g;

// What may sit between the words of a phrase: whitespace or a hyphen/dash.
const GAP = '[\\s\\-\\u2010\\u2011\\u2012\\u2013]+';
const GAP_SPLIT = new RegExp(GAP, 'u');

// JavaScript's \b and \w only know a-z, so the edges are spelled out with
// Unicode properties. Python's \w also counts combining marks only when they
// are composed, which normalise() guarantees.
const WORD = '[\\p{L}\\p{N}_]';
const LEFT_EDGE = `(?<!${WORD})(?<!${WORD}')`;
const RIGHT_EDGE = `(?!${WORD})`;

const escape = (s) => s.replace(/[.*+?^${}()|[\]\\\/\-]/g, '\\$&');

/** The form of the text the matcher works on. Offsets refer to this. */
export function normalise(text) {
  return String(text).normalize('NFC').replace(APOSTROPHES, "'").replace(SPACES, ' ');
}

/**
 * Parse watch-list text: one term per line, `|` between spellings of the same
 * term, first spelling is the label. `# ` (hash, space) starts a comment line;
 * `#word` is a hashtag and is kept.
 * @returns {{label: string, variants: string[]}[]}
 */
export function parseWatchlist(source) {
  const terms = [];
  const seen = new Set();
  for (const raw of String(source).split(/\r\n|\r|\n/)) {
    const line = normalise(raw).trim();
    if (!line || line === '#' || line.startsWith('# ')) continue;
    const variants = [];
    for (const part of line.split('|')) {
      const cleaned = part.trim().split(/\s+/u).join(' ');
      if (cleaned && !variants.some((v) => v.toLowerCase() === cleaned.toLowerCase())) variants.push(cleaned);
    }
    if (!variants.length || seen.has(variants[0].toLowerCase())) continue;
    seen.add(variants[0].toLowerCase());
    terms.push({ label: variants[0], variants });
  }
  return terms;
}

function pattern(variant, caseSensitive, wholeWord) {
  const words = variant.split(GAP_SPLIT).filter(Boolean).map(escape);
  if (!words.length) return null;
  let body = words.join(GAP);
  if (wholeWord) body = LEFT_EDGE + body + RIGHT_EDGE;
  return new RegExp(body, caseSensitive ? 'gu' : 'giu');
}

/**
 * @param {{label: string, variants: string[]}[]} terms
 * @param {{caseSensitive?: boolean, wholeWord?: boolean}} [options]
 */
export function createMatcher(terms, { caseSensitive = false, wholeWord = true } = {}) {
  const compiled = [];
  for (const term of terms) {
    for (const variant of term.variants) {
      const re = pattern(variant, caseSensitive, wholeWord);
      if (re) compiled.push({ term, variant, re });
    }
  }

  /** Every occurrence of every variant, in reading order. Spans may overlap. */
  function find(text) {
    const haystack = normalise(text);
    const found = [];
    for (const { term, variant, re } of compiled) {
      for (const hit of haystack.matchAll(re)) {
        found.push({ term: term.label, variant, start: hit.index, end: hit.index + hit[0].length, text: hit[0] });
      }
    }
    // Array.prototype.sort is stable, so ties keep watch-list order.
    return found.sort((a, b) => a.start - b.start || b.end - a.end);
  }

  /** Labels of the terms present, in watch-list order. */
  function termsFound(text) {
    const present = new Set(find(text).map((m) => m.term));
    return terms.filter((t) => present.has(t.label)).map((t) => t.label);
  }

  return { find, termsFound };
}

/**
 * Merge overlapping matches into spans for highlighting.
 * @returns {{start: number, end: number, terms: string[]}[]}
 */
export function mergeSpans(matches) {
  const spans = [];
  for (const m of matches) {
    const last = spans[spans.length - 1];
    if (last && m.start < last.end) {
      last.end = Math.max(last.end, m.end);
      if (!last.terms.includes(m.term)) last.terms.push(m.term);
    } else {
      spans.push({ start: m.start, end: m.end, terms: [m.term] });
    }
  }
  return spans;
}

/**
 * Split normalised text into plain and matched pieces, ready to render.
 * @returns {{text: string, terms: string[] | null}[]}
 */
export function segments(text, matches) {
  const clean = normalise(text);
  const out = [];
  let at = 0;
  for (const span of mergeSpans(matches)) {
    if (span.start > at) out.push({ text: clean.slice(at, span.start), terms: null });
    out.push({ text: clean.slice(span.start, span.end), terms: span.terms });
    at = span.end;
  }
  if (at < clean.length) out.push({ text: clean.slice(at), terms: null });
  return out;
}
