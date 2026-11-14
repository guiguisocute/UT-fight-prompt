// Dump pictures the page makes (packed sprites and the ones drawn in src/sprites.js) to PNGs for
// review, enlarged on a dark ground.
// Usage: node tools/sprdump.cjs <outDir> <key> [key ...] [--scale=8]   e.g. ow/echo kid/17
const { chromium, pageUrl, argsFor } = require('./pw.cjs');
const fs = require('fs'), path = require('path');
(async () => {
  const args = process.argv.slice(2), keys = args.filter((a) => !a.startsWith('--'));
  const out = keys.shift(), sc = +((args.find((a) => a.startsWith('--scale=')) || '--scale=8').split('=')[1]);
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: argsFor(true) });
  const p = await b.newPage();
  p.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await p.goto(pageUrl('?render=1&w=480&h=270'));
  await p.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 60000 });
  for (const k of keys) {
    const url = await p.evaluate(([k, sc]) => {
      const s = window.MV.IMG[k];
      if (!s) return null;
      const c = document.createElement('canvas'); c.width = s.width * sc; c.height = s.height * sc;
      const x = c.getContext('2d'); x.imageSmoothingEnabled = false;
      x.fillStyle = '#100c28'; x.fillRect(0, 0, c.width, c.height); x.drawImage(s, 0, 0, c.width, c.height);
      return c.toDataURL();
    }, [k, sc]);
    if (!url) { console.log('no picture', k); continue; }
    fs.writeFileSync(path.join(out, k.replace(/\//g, '_') + '.png'), Buffer.from(url.split(',')[1], 'base64'));
  }
  await b.close();
})();
