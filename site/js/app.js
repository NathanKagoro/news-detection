// The evidence board: runs the matcher over invented clippings and ties each
// watch-list term to the clippings it flagged with a length of red string.

import { createMatcher, parseWatchlist, segments } from './matcher.js';
import { CLIPPINGS, SAMPLE_WATCHLIST } from './samples.js';

const $ = (id) => document.getElementById(id);
const board = $('board-area');
const svg = $('strings');
const input = $('watchlist');
const ruleCase = $('rule-case');
const ruleWord = $('rule-word');
const tagsEl = $('tags');
const clipsEl = $('clippings');
const tally = $('tally');
const digest = $('digest');
const SVG_NS = 'http://www.w3.org/2000/svg';

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

// ---------------------------------------------------------------- ticker ---
const ticker = $('ticker');
const tickerToggle = $('ticker-toggle');
{
  // Duplicate the list once so the loop has no seam. The copy is decorative.
  const track = ticker.querySelector('.ticker__track');
  const copy = track.cloneNode(true);
  copy.setAttribute('aria-hidden', 'true');
  ticker.append(copy);
  tickerToggle.addEventListener('click', () => {
    const paused = ticker.classList.toggle('is-paused');
    tickerToggle.setAttribute('aria-pressed', String(paused));
    tickerToggle.textContent = paused ? 'Play' : 'Pause';
  });
}

// ----------------------------------------------------------------- board ---
let active = null;   // label of the term whose string is being followed
let links = [];      // [{ term, tag, clip }] one per string
let clipNodes = [];

function fill(node, text, matches) {
  node.textContent = '';
  for (const part of segments(text, matches)) {
    if (part.terms) {
      const mark = el('mark', null, part.text);
      mark.title = `Matched: ${part.terms.join(', ')}`;
      node.append(mark);
    } else {
      node.append(part.text);
    }
  }
}

function buildClippings() {
  clipNodes = CLIPPINGS.map((c) => {
    const li = el('li', 'clip');
    li.lang = c.lang;
    const meta = el('p', 'clip__meta');
    meta.lang = 'en';
    meta.append(el('span', 'clip__outlet', c.outlet), el('span', 'clip__kind', c.kind));
    const head = el('h3', 'clip__head');
    const sum = el('p', 'clip__sum');
    const foot = el('p', 'clip__foot');
    foot.lang = 'en';
    const pin = el('span', 'clip__pin');
    pin.setAttribute('aria-hidden', 'true');
    li.append(pin, meta, head, sum, foot);
    clipsEl.append(li);
    return { data: c, li, head, sum, foot, pin };
  });
}

function plural(n, one, many) {
  return `${n === 0 ? 'No' : n} ${n === 1 ? one : many}`;
}

function run() {
  const terms = parseWatchlist(input.value);
  const matcher = createMatcher(terms, { caseSensitive: !ruleCase.checked, wholeWord: ruleWord.checked });
  const byTerm = new Map(terms.map((t) => [t.label, []]));
  let flagged = 0, missed = 0, alarms = 0;
  const lines = ['ZCZC  MORNING DIGEST', ''];

  for (const node of clipNodes) {
    const { data } = node;
    const headHits = matcher.find(data.headline);
    const sumHits = matcher.find(data.summary);
    fill(node.head, data.headline, headHits);
    fill(node.sum, data.summary, sumHits);
    const found = terms.map((t) => t.label).filter((label) => [...headHits, ...sumHits].some((m) => m.term === label));
    for (const label of found) byTerm.get(label).push(node);

    const isFlagged = found.length > 0;
    const verdict = isFlagged && !data.relevant ? 'alarm' : !isFlagged && data.relevant ? 'missed' : isFlagged ? 'hit' : 'quiet';
    node.li.dataset.verdict = verdict;
    node.terms = found;
    node.foot.textContent = '';
    if (verdict === 'alarm') node.foot.append(el('b', 'verdict verdict--alarm', 'False alarm'), ` Matched ${found.join(', ')}, but the story is about something else.`);
    else if (verdict === 'missed') node.foot.append(el('b', 'verdict verdict--missed', 'Missed'), ' On the brief, but nothing on the list caught it.');
    else if (verdict === 'hit') node.foot.append(`Matched: ${found.join(', ')}`);
    else node.foot.append('Not flagged, and rightly.');

    if (isFlagged) {
      flagged += 1;
      lines.push(data.outlet.toUpperCase(), `  ${data.headline}`, `  MATCHED: ${found.join(', ')}`, '');
    }
    if (verdict === 'missed') missed += 1;
    if (verdict === 'alarm') alarms += 1;
  }

  // Tags: one per term, in watch-list order.
  if (active && !byTerm.has(active)) active = null;
  tagsEl.textContent = '';
  links = [];
  for (const term of terms) {
    const nodes = byTerm.get(term.label);
    const tag = el('button', 'tag');
    tag.type = 'button';
    tag.dataset.term = term.label;
    tag.append(el('span', 'tag__label', term.label), el('span', 'tag__count', nodes.length ? `×${nodes.length}` : 'none'));
    tag.setAttribute('aria-label', `${term.label}: ${plural(nodes.length, 'clipping', 'clippings').toLowerCase()}. Follow its string.`);
    if (!nodes.length) tag.classList.add('tag--idle');
    tag.addEventListener('click', () => {
      active = active === term.label ? null : term.label;
      paint();
    });
    tagsEl.append(tag);
    for (const clip of nodes) links.push({ term: term.label, tag, clip });
  }
  if (!terms.length) tagsEl.append(el('p', 'tags__empty', 'The watch-list is empty. Type a term above, or restore the sample list.'));

  tally.textContent = `${flagged} of ${clipNodes.length} clippings flagged. ${plural(missed, 'story', 'stories')} missed. ${plural(alarms, 'false alarm', 'false alarms')}.`;
  tally.dataset.state = missed || alarms > 1 ? 'bad' : 'good';

  if (flagged) lines.push(`${flagged} ITEM${flagged === 1 ? '' : 'S'} FLAGGED`, 'NNNN');
  else lines.push('NOTHING ON THE WATCH-LIST THIS MORNING', 'NNNN');
  digest.textContent = lines.join('\n');

  paint();
}

// Which term's strings to draw. On a narrow board the strings run down a
// gutter, so only one term is followed at a time.
function followed() {
  if (active) return active;
  if (!isNarrow()) return null;
  const first = links[0];
  return first ? first.term : null;
}

const isNarrow = () => getComputedStyle(board).getPropertyValue('--narrow').trim() === '1';

function paint() {
  const follow = followed();
  for (const tag of tagsEl.querySelectorAll('.tag')) {
    const on = tag.dataset.term === follow;
    tag.setAttribute('aria-pressed', String(tag.dataset.term === active));
    tag.classList.toggle('is-followed', on);
  }
  for (const node of clipNodes) {
    node.li.classList.toggle('is-dimmed', Boolean(active) && !node.terms.includes(active));
  }
  drawStrings();
}

function drawStrings() {
  const box = board.getBoundingClientRect();
  svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
  svg.setAttribute('width', box.width);
  svg.setAttribute('height', box.height);
  svg.textContent = '';
  const follow = followed();
  const narrow = isNarrow();
  const frag = document.createDocumentFragment();

  for (const link of links) {
    if (follow && link.term !== follow) continue;
    const t = link.tag.getBoundingClientRect();
    const p = link.clip.pin.getBoundingClientRect();
    const x2 = p.left + p.width / 2 - box.left;
    const y2 = p.top + p.height / 2 - box.top;
    let d, x1, y1;
    if (narrow) {
      // Down the left gutter, then across to the pin.
      x1 = t.left - box.left + 10;
      y1 = t.bottom - box.top - 4;
      const gutter = 9;
      d = `M${x1} ${y1} L${gutter} ${y1 + 14} L${gutter} ${y2} L${x2} ${y2}`;
    } else {
      x1 = t.right - box.left - 8;
      y1 = t.top + t.height / 2 - box.top;
      const sag = Math.min(46, Math.hypot(x2 - x1, y2 - y1) * 0.1);
      d = `M${x1} ${y1} Q${(x1 + x2) / 2} ${(y1 + y2) / 2 + sag} ${x2} ${y2}`;
    }
    const shadow = document.createElementNS(SVG_NS, 'path');
    shadow.setAttribute('d', d);
    shadow.setAttribute('class', 'string-shadow');
    const string = document.createElementNS(SVG_NS, 'path');
    string.setAttribute('d', d);
    string.setAttribute('class', follow ? 'string string--followed' : 'string');
    frag.append(shadow, string);
    for (const [cx, cy] of [[x1, y1], [x2, y2]]) {
      const knot = document.createElementNS(SVG_NS, 'circle');
      knot.setAttribute('cx', cx);
      knot.setAttribute('cy', cy);
      knot.setAttribute('r', 3.2);
      knot.setAttribute('class', 'knot');
      frag.append(knot);
    }
  }
  svg.append(frag);
}

// Redraw when the layout moves: resize, fonts arriving, or the sticky desk
// sliding while the board scrolls past. One frame at most, and only while the
// board is on screen.
let queued = false;
let onScreen = true;
function queueDraw() {
  if (queued || !onScreen) return;
  queued = true;
  requestAnimationFrame(() => { queued = false; drawStrings(); });
}

buildClippings();
input.value = SAMPLE_WATCHLIST;
run();

input.addEventListener('input', run);
ruleCase.addEventListener('change', run);
ruleWord.addEventListener('change', run);
$('reset').addEventListener('click', () => {
  input.value = SAMPLE_WATCHLIST;
  ruleCase.checked = true;
  ruleWord.checked = true;
  active = null;
  run();
});

new ResizeObserver(queueDraw).observe(board);
new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; if (onScreen) queueDraw(); }).observe(board);
addEventListener('scroll', queueDraw, { passive: true });
document.fonts?.ready.then(queueDraw);
