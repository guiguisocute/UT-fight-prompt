// The soul and what is thrown at it: node tools/check.cjs [bar0] [bar1]
// Samples the battle at 240 Hz (the picture's own time) and measures, for the red soul, how near each
// blade that can cut it comes (MV.RD.dangers: round 4's spears, the rings', the floor's, the charged
// ones, the thrown-down ones, the gale's ... - each a segment with a half width). A touch (nearer than
// the soul's radius) is wrong unless the soul is hit there on purpose (TL.hurts, H.hurt). Also how fast
// the soul goes (the original's pace: ~140 px / s), and per bar how dense it is: blades thrown at the red
// soul, arrows met by the green soul's glass, near misses.
const { chromium, pageUrl, SWIFT } = require('./pw.cjs');
(async () => {
  const [b0 = '12', b1 = '60'] = process.argv.slice(2);
  const browser = await chromium.launch({ args: SWIFT });
  const page = await browser.newPage({ viewport: { width: 320, height: 180 } });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(pageUrl('?render=1&w=320&h=180'));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 120000 });
  const r = await page.evaluate(([b0, b1]) => {
    const MV = window.MV, T = MV.T, TL = MV.TL, RD = MV.RD;
    const SR = 6, dt = 1 / 240;
    const near = {}, bad = [], fast = [];
    // (a hit meant, and the invincible frames after it)
    const meant = (t) => TL.hurts.some((h) => t > h.t - 0.08 && t < h.t + h.inv);
    let prev = null, run = null;
    for (let t = T.at(+b0); t < T.at(+b1); t += dt) {
      if (TL.soulMode.at(t) !== 'red') { prev = null; continue; }
      const s = TL.batSoul.at(t);
      if (s.a < 0.5) { prev = null; continue; }
      const p = [s.x, s.y];
      // (its pace: runs of frames faster than the original's, each with its top speed and length -
      // the soul pulled off the menu into her box is a jump, ~0.1 s)
      if (prev) {
        const v = Math.hypot(p[0] - prev[0], p[1] - prev[1]) / dt;
        if (v > 260) { if (!run) run = { b: T.barOf(t), v: 0, n: 0 }; run.v = Math.max(run.v, v); run.n++; }
        else if (run) { fast.push(`${run.b.toFixed(3)} ${Math.round(run.v)} px/s ${(run.n * dt).toFixed(2)} s`); run = null; }
      }
      prev = p;
      for (const g of RD.dangers(t)) {
        const d = RD.segDist(p, g.a, g.b)[0] - g.w;
        if (!(g.kind in near) || d < near[g.kind]) near[g.kind] = d;
        if (d < SR && !meant(t)) { const own = g.id.t ?? g.id.t0 ?? (g.id.g && g.id.g.t); bad.push(`${g.kind} ${T.barOf(t).toFixed(3)} d ${d.toFixed(1)}${own !== undefined ? ` (its time ${T.barOf(own).toFixed(3)})` : ''}`); }
      }
    }
    // density per bar: what is thrown (by when it is hot first), the glass's blocks, the near misses
    const per = {};
    const bar = (t) => Math.floor(T.barOf(t) + 1e-6), add = (t, k) => { const b = bar(t); if (b < +b0 || b >= +b1) return; (per[b] = per[b] || { red: 0, green: 0, graze: 0 })[k]++; };
    for (const s of RD.spears) add(s.t, 'red');
    for (const g of RD.rings) for (let i = 0; i < g.n; i++) add(g.t, 'red');
    for (const b of RD.bigs) add(b.t, 'red');
    for (const p of RD.pillars) add(p.t, 'red');
    for (const c of RD.covers) add(c.t, 'red');
    for (const d of RD.drifts) add(d.t0, 'red');
    for (const c of RD.cells || []) add(c.t, 'red');
    for (const a of RD.blocks) add(a.t, 'green');
    for (const g of RD.grazes) add(g.t, 'graze');
    const dens = Object.entries(per).map(([b, v]) => `${b}: ${v.red ? v.red + ' red' : ''}${v.green ? ' ' + v.green + ' blocks' : ''}${v.graze ? ' ' + v.graze + ' grazes' : ''}`);
    return { near, bad: bad.slice(0, 40), nBad: bad.length, fast: fast.slice(0, 20), nFast: fast.length, dens, hurts: TL.hurts.map((h) => `${T.barOf(h.t).toFixed(3)} -${h.dmg} -> ${h.hp}`) };
  }, [b0, b1]);
  console.log('nearest (px):', Object.entries(r.near).map(([k, v]) => `${k} ${v.toFixed(1)}`).join(', '));
  console.log(r.nBad ? `${r.nBad} touches not meant:` : 'no touches but the meant ones');
  for (const b of r.bad) console.log('  ' + b);
  console.log(r.nFast ? `${r.nFast} frames faster than 260 px/s: ${r.fast.join(' | ')}` : 'pace ok');
  console.log('per bar:', r.dens.join(' | '));
  console.log('hits:', r.hurts.join(' | '));
  await browser.close();
})();
