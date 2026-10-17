// Full-page and first-screen screenshots at 1440, 390 and 360 px, into shots/.
// Fails if a page logs an error, scrolls sideways, or the demo does not run.
// Uses the Chrome already on the machine (CHROME_PATH overrides the guess).
import { existsSync, mkdirSync } from 'node:fs';
import puppeteer from 'puppeteer-core';
import { serve } from './serve.mjs';

const PAGES = ['index.html', '404.html'];
const WIDTHS = [1440, 390, 360];
const BASE = '/news-detection/';
const PORT = Number(process.env.PORT || 4361);

const chrome = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium-browser',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].find((p) => p && existsSync(p));
if (!chrome) throw new Error('Chrome not found. Set CHROME_PATH.');

mkdirSync('shots', { recursive: true });
const server = await serve('site', PORT, BASE);
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox', '--hide-scrollbars'] });
let problems = 0;
try {
  for (const file of PAGES) {
    for (const width of WIDTHS) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', (e) => errors.push(e.message));
      page.on('console', (m) => { if (m.type() === 'error' && !/404/.test(m.text())) errors.push(m.text()); });
      await page.setViewport({ width, height: width > 700 ? 900 : 800, deviceScaleFactor: 1, isMobile: width < 700, hasTouch: width < 700 });
      await page.goto(`http://127.0.0.1:${PORT}${BASE}${file}`, { waitUntil: 'networkidle0' });
      await page.evaluate(() => document.fonts.ready);
      await new Promise((r) => setTimeout(r, 3500)); // let the wire finish printing
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (overflow > 1) errors.push(`horizontal overflow of ${overflow}px`);
      if (file === 'index.html') {
        const strings = await page.evaluate(() => document.querySelectorAll('#strings path.string').length);
        const clips = await page.evaluate(() => document.querySelectorAll('#clippings .clip').length);
        if (clips !== 12 || strings === 0) errors.push(`demo did not run (${clips} clippings, ${strings} strings)`);
      }
      const name = `shots/${file.replace('.html', '')}-${width}`;
      await page.screenshot({ path: `${name}-fold.png` });
      await page.screenshot({ path: `${name}.png`, fullPage: true });
      problems += errors.length;
      console.log(`${file} @ ${width}: ${errors.length ? errors.join('; ') : 'ok'}`);
      await page.close();
    }
  }
} finally {
  await browser.close();
  server.close();
}
if (problems) {
  console.error(`${problems} problem(s) found while taking screenshots.`);
  process.exit(1);
}
