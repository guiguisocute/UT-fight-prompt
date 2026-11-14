// Camera smoothness check for the 3D shots: node tools/camcheck.cjs <bar0> <bar1>
// Samples the camera (no impacts) at 240 Hz and reports the top speed, and where its speed or
// its look direction jumps (a cut shows as a jump - expected only where a shot begins).
const { chromium, pageUrl, SWIFT } = require('./pw.cjs');
(async () => {
  const [b0 = '9', b1 = '12.75'] = process.argv.slice(2);
  const browser = await chromium.launch({ args: SWIFT });
  const page = await browser.newPage({ viewport: { width: 320, height: 180 } });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(pageUrl('?render=1&w=320&h=180'));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 120000 });
  const r = await page.evaluate(([b0, b1]) => {
    const MV = window.MV, T = MV.T, W3 = MV.W3, M3 = MV.M3, TL = MV.TL;
    const t0 = T.at(+b0), t1 = T.at(+b1), dt = 1 / 240;
    const P = [], F = [], ts = [];
    for (let t = t0; t < t1; t += dt) {
      const tv = TL.vt(t), c = W3.cam(tv, null);
      P.push(c.pos); F.push(c.f); ts.push(t);
    }
    const bar = (i) => +T.barOf(ts[i]).toFixed(4);
    const v = [], w = [];
    for (let i = 1; i < P.length; i++) { v.push(M3.dist(P[i], P[i - 1]) / dt); w.push(Math.acos(Math.min(1, M3.dot(F[i], F[i - 1]))) / dt); }
    const jumps = [];
    for (let i = 2; i < v.length; i++) {
      const dv = Math.abs(v[i] - v[i - 1]), dw = Math.abs(w[i] - w[i - 1]);
      // (a jump: the speed changes by more than 120 u/s or the turn rate by more than 0.6 rad/s in 1/240 s)
      if (dv > 120 || dw > 0.6) jumps.push(`${bar(i)}: dv ${Math.round(dv)} (v ${Math.round(v[i - 1])}->${Math.round(v[i])}) dw ${dw.toFixed(2)}`);
    }
    const vmax = Math.max(...v), wmax = Math.max(...w);
    return { vmax: Math.round(vmax) + ' @' + bar(v.indexOf(vmax)), wmax: wmax.toFixed(2) + ' rad/s @' + bar(w.indexOf(wmax)), jumps: jumps.slice(0, 40), nJumps: jumps.length };
  }, [b0, b1]);
  console.log('top speed', r.vmax, '| top turn', r.wmax);
  console.log(r.nJumps ? `${r.nJumps} jumps:` : 'no jumps');
  for (const j of r.jumps) console.log('  ' + j);
  await browser.close();
})();
