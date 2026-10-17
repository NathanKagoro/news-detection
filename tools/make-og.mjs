// Renders tools/og.html to site/og.jpg (1200x630) with the local Chrome.
import { existsSync, statSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import puppeteer from 'puppeteer-core';

const chrome = [process.env.CHROME_PATH, 'C:/Program Files/Google/Chrome/Application/chrome.exe', '/usr/bin/google-chrome']
  .find((p) => p && existsSync(p));
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--allow-file-access-from-files'] });
const page = await browser.newPage();
await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(resolve('tools/og.html')).href, { waitUntil: 'networkidle0' });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: 'site/og.jpg', type: 'jpeg', quality: 84 });
await browser.close();
console.log(`site/og.jpg ${Math.round(statSync('site/og.jpg').size / 1024)} KB`);
