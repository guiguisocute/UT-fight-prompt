// Render selected frames to images for review.
// Usage: node tools/frames.cjs <outDir> <t1> <t2> ... [--w=960 --h=540] [--bars] [--gpu] (times as bar numbers,
//        fractional bars allowed: 7.5625 = bar 7, 16th 9; --gpu renders on the graphics card)
const { chromium, pageUrl, argsFor } = require('./pw.cjs');
const path = require('path');
const fs = require('fs');
(async () => {
  const args = process.argv.slice(2);
  // (split on the first '=' only: --pre takes code with '=' in it)
  const opts = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const i = a.indexOf('='); return i < 0 ? [a.slice(2), true] : [a.slice(2, i), a.slice(i + 1)]; }));
  const [out, ...ts] = args.filter((a) => !a.startsWith('--'));
  fs.mkdirSync(out, { recursive: true });
  const w = opts.w || 960, h = opts.h || 540;
  const browser = await chromium.launch({ args: argsFor(opts.gpu) });
  const page = await browser.newPage({ viewport: { width: +w, height: +h } });
  let failed = null;
  page.on('pageerror', (e) => { console.log('[pageerror]', e.message); failed = e; });
  page.on('console', (m) => { if ((m.type() === 'error' || m.type() === 'warning') && !/GPU stall/.test(m.text())) { console.log('[page]', m.text()); if (m.type() === 'error') failed = failed || m.text(); } });
  await page.goto(pageUrl(`?render=1&w=${w}&h=${h}`));
  // (fail fast: a shader or script error never sets MV.ready)
  for (let i = 0; i < 1200 && !(await page.evaluate(() => !!(window.MV && window.MV.ready))); i++) {
    if (failed) { await browser.close(); process.exit(1); }
    await new Promise((r) => setTimeout(r, 100));
  }
  if (opts.gpu) console.log('renderer:', await page.evaluate(() => window.MV.glRenderer || '?'));
  // --pre="js": run in the page before rendering (e.g. MV.W3.debug = {...} for a turntable)
  if (opts.pre) console.log('pre:', await page.evaluate((s) => { try { return String(eval(s)); } catch (e) { return 'ERR ' + e.message; } }, opts.pre));
  const t0 = Date.now();
  for (const s of ts) {
    const t = opts.bars ? await page.evaluate((b) => window.MV.T.at(+b), s) : +s;
    const url = await page.evaluate((t) => window.MV.exportFrame(+t, 'image/png'), t);
    fs.writeFileSync(path.join(out, `f_${(+s).toFixed(4)}.png`), Buffer.from(url.split(',')[1], 'base64'));
  }
  console.log(`${ts.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  await browser.close();
})();
