// Minimal static server for local preview and CI screenshots.
// node tools/serve.mjs <dir> <port> [/base/]
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, extname, normalize, resolve, basename } from 'node:path';

const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2',
  '.json': 'application/json', '.txt': 'text/plain; charset=utf-8', '.jpg': 'image/jpeg', '.webp': 'image/webp',
};

export function serve(dir, port, base = '/') {
  const root = resolve(dir);
  const server = createServer(async (req, res) => {
    let path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (!path.startsWith(base)) {
      res.writeHead(302, { Location: base }).end();
      return;
    }
    path = path.slice(base.length - 1);
    if (path.endsWith('/')) path += 'index.html';
    path = normalize(path);
    const file = join(root, path);
    try {
      if (!file.startsWith(root)) throw new Error('outside root');
      const body = await readFile(file);
      res.writeHead(200, { 'Content-Type': TYPES[extname(file)] || 'application/octet-stream' }).end(body);
    } catch {
      const body = await readFile(join(root, '404.html')).catch(() => 'Not found');
      res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' }).end(body);
    }
  });
  return new Promise((done) => server.listen(port, '127.0.0.1', () => done(server)));
}

if (process.argv[1] && basename(process.argv[1]) === 'serve.mjs') {
  const [dir = 'site', port = '4360', base = '/'] = process.argv.slice(2);
  await serve(dir, Number(port), base);
  console.log(`Serving ${dir} at http://127.0.0.1:${port}${base}`);
}
