// Validate the choreography: node tools/check.cjs [t0] [t1] [--bars]
//  * no attack ever touches the soul, except the scripted hits (events marked hurts)
//    (blue passes only a still soul, orange only a moving one)
//  * grazes: closest approaches of a beam's edge under 28 px (reported, not errors)
//  * every sound effect exists (a sample in assets.js or a synth recipe)
//  * every character drawn has a glyph (run tools/make_font.py after adding text)
const { chromium, pageUrl, SWIFT } = require('./pw.cjs');
(async () => {
  const argv = process.argv.slice(2);
  const bars = argv.includes('--bars');
  const [a0 = '', a1 = ''] = argv.filter((a) => !a.startsWith('--'));
  const browser = await chromium.launch({ args: SWIFT });
  const page = await browser.newPage({ viewport: { width: 320, height: 180 } });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[console]', m.text()); });
  await page.goto(pageUrl('?render=1&w=320&h=180'));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 120000 });
  const [t0, t1] = await page.evaluate(([a, b, bars]) => {
    const T = window.MV.T, f = (v, d) => (v === '' ? d : bars ? T.at(+v) : +v);
    return [f(a, 0), f(b, T.end)];
  }, [a0, a1, bars]);
  const hits = await page.evaluate(([a, b]) => window.MV.checkHits(a, b), [t0, t1]);
  console.log(hits.length ? `soul: ${hits.length} collisions` : 'OK: no collisions');
  for (const h of hits.slice(0, 40)) console.log(JSON.stringify(h));
  // grazes: per beam (events with gap()), its closest approach to the soul while it is thick
  const grazes = await page.evaluate(([a, b]) => {
    const MV = window.MV, TL = MV.TL, out = new Map();
    for (let t = a; t < b; t += 1 / 240) {
      const s = TL.soul.at(t);
      if (s.a < 0.5) continue;
      for (const e of TL.active(t)) {
        if (!e.gap || !e.hit || e.harmless || (e.live && !e.live(t))) continue;
        const g = e.gap(s.x, s.y);
        const k = e.t0;
        if (!out.has(k) || out.get(k).gap > g) out.set(k, { bar: +MV.T.barOf(e.t0).toFixed(3), gap: Math.round(g) });
      }
    }
    return [...out.values()].filter((g) => g.gap < 28).sort((x, y) => x.bar - y.bar);
  }, [t0, t1]);
  console.log(`grazes (< 28 px from a beam's centre line): ${grazes.length}`);
  for (const g of grazes.slice(0, 30)) console.log('  bar', g.bar, 'gap', g.gap);
  // the sky: closest approach of each 3D beam to the soul while it burns (world units)
  const g3 = await page.evaluate(([a, b]) => {
    const MV = window.MV, TL = MV.TL, out = new Map();
    for (let t = a; t < b; t += 1 / 240) {
      if (TL.w3.at(t).on < 0.5) continue;
      const h = MV.W3.heart(t);
      if (h.s.a < 0.5) continue;
      for (const e of TL.e3) {
        if (t < e.t0 || t >= e.t1 || !e.gap3 || e.harmless || (e.live && !e.live(t))) continue;
        const g = e.gap3(h.p, t) - (e.w || 0);
        if (!out.has(e.t0) || out.get(e.t0).gap > g) out.set(e.t0, { bar: +MV.T.barOf(e.t0).toFixed(3), gap: Math.round(g) });
      }
    }
    return [...out.values()].sort((x, y) => x.bar - y.bar);
  }, [t0, t1]);
  console.log(`3D beams: ${g3.length}, closest edge gaps (units; the soul is 8 across): ${g3.map((g) => g.bar + ':' + g.gap).join('  ')}`);
  // the soul's stream (H3.autoFire) never goes through him (README 规则): each round's closest pass to
  // where he is drawn (his line and his blinks) - under 45 units it goes through his body
  const thru = await page.evaluate(([a, b]) => {
    const MV = window.MV, M3 = MV.M3, W3 = MV.W3, out = [];
    let n = 0, near = 1e9;
    for (const rec of MV.TL.autoFires || []) for (const r of rec.list) {
      if (r.ts + r.life < a || r.ts > b) continue;
      n++;
      let best = 1e9, bt = r.ts;
      for (let tau = 0; tau <= r.life; tau += 1 / 240) { const t = r.ts + tau, d = M3.dist(M3.mad(r.p0, r.v, tau), W3.hisPos(t)); if (d < best) { best = d; bt = t; } }
      near = Math.min(near, best);
      if (best < 45) out.push({ bar: +MV.T.barOf(bt).toFixed(3), d: Math.round(best) });
    }
    return { n, near: Math.round(near), out };
  }, [t0, t1]);
  console.log(thru.out.length ? `stream: ${thru.out.length} of ${thru.n} rounds through him` : `OK: the stream never touches him (${thru.n} rounds, closest ${thru.near})`);
  for (const h of thru.out.slice(0, 20)) console.log('  bar', h.bar, 'dist', h.d);
  const snd = await page.evaluate(() => {
    const MV = window.MV, have = new Set([...Object.keys(window.MV_ASSETS.sfx), ...(window.MV_SYNTH ? window.MV_SYNTH.names : [])]);
    return MV.TL.sfx.filter((e) => !have.has(e.name)).map((e) => ({ name: e.name, t: +e.t.toFixed(2) }));
  });
  console.log(snd.length ? `sound: ${snd.length} unknown effects` : 'OK: every sound effect exists');
  for (const h of snd.slice(0, 20)) console.log(JSON.stringify(h));
  const fs = require('fs'), path = require('path'), dir = path.resolve(__dirname, '../src');
  const have = await page.evaluate(() => Object.keys(window.MV_GLYPHS));
  const used = new Set();
  for (const f of fs.readdirSync(dir)) if (f.endsWith('.js') && !/^(glyphs|assets|analysis)\.js$/.test(f)) for (const ch of fs.readFileSync(path.join(dir, f), 'utf8').match(/[^\x00-\x7f]/g) || []) used.add(ch);
  const noGlyph = [...used].filter((ch) => !have.includes(ch) && !'♥★←→↑↓◀▶●·'.includes(ch) && /\S/.test(ch));
  console.log(noGlyph.length ? `font: no glyph for ${noGlyph.join('')} (run tools/make_font.py)` : 'OK: every character has a glyph');
  await browser.close();
})();
