// Cut audit for the 3D shots (the grammar of the edit, measured): node tools/cutaudit.cjs <out> <bar0> <bar1> [--gpu]
// For every cut between the bars it renders the last frame of the shot before and the first of
// the shot after (out/cut_NN_a.png, _b.png) and writes out/cuts.json with, for each side of it:
//   soul / neo: where they are in the picture (px of 960 x 540; null: not in it)
//   side: which side of the line between them the camera is on (+1 / -1: a change = the line crossed)
//   go: which way the chase heads in the picture (the soul's travel through the world, projected)
//   turn: how far the view turns across the cut (deg; under ~30 with the same subject = a jump cut)
// and the impacts (shake / flash) per bar. tools/cutsheet.py lays the frames out with the numbers.
const { chromium, pageUrl, argsFor } = require('./pw.cjs');
const path = require('path');
const fs = require('fs');
(async () => {
  const args = process.argv.slice(2);
  const opts = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const i = a.indexOf('='); return i < 0 ? [a.slice(2), true] : [a.slice(2, i), a.slice(i + 1)]; }));
  const [out, b0 = '9', b1 = '34'] = args.filter((a) => !a.startsWith('--'));
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: argsFor(opts.gpu) });
  const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(pageUrl('?render=1&w=480&h=270'));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 120000 });
  const r = await page.evaluate(([b0, b1]) => {
    const MV = window.MV, T = MV.T, W3 = MV.W3, M3 = MV.M3, TL = MV.TL;
    const t0 = T.at(+b0), t1 = T.at(+b1);
    const starts = [...new Set(TL.shots.map((s) => s.t0))].filter((t) => t > t0 && t < t1).sort((a, b) => a - b);
    const look = (t) => {
      const vt = TL.vt(t), cam = W3.cam(vt, null);
      const h = W3.heart(vt), n = W3.neo(vt);
      const scr = (p, a) => { if (a < 0.3) return null; const q = W3.project(cam, W3.w(vt, p)); return q && q[0] > -40 && q[0] < 1000 && q[1] > -40 && q[1] < 580 ? [Math.round(q[0]), Math.round(q[1])] : null; };
      const line = M3.sub(n.p, h.p), sideV = M3.norm(M3.cross(line, [0, 1, 0])), mid = M3.lerp(h.p, n.p, 0.5);
      const side = Math.sign(M3.dot(M3.sub(cam.local, mid), sideV));
      // (the chase's heading in the picture: where the soul is going through the world)
      const dt = 0.04, w0 = W3.w(vt, h.p), w1 = W3.w(vt + dt, W3.heart(vt + dt).p);
      const a = W3.project(cam, w0), b = W3.project(cam, M3.add(w0, M3.mul(M3.norm(M3.sub(w1, w0)), 60)));
      const go = a && b ? [Math.round(b[0] - a[0]), Math.round(b[1] - a[1])] : null;
      return { soul: scr(h.p, h.s.a), neo: scr(n.p, n.s.a), side, go, f: cam.f, roll: +(Math.atan2(cam.r[1], cam.u[1]) * 57.3).toFixed(1) };
    };
    const shotDur = (t) => { const s = W3.shotOf(t); return s ? +(T.barOf(s.t1) - T.barOf(s.t0)).toFixed(2) : null; };
    const cuts = starts.map((tc) => {
      const A = look(tc - 0.017), B = look(tc + 0.004);
      return { t: +tc.toFixed(3), bar: +T.barOf(tc).toFixed(3), before: shotDur(tc - 0.017), after: shotDur(tc + 0.004), A, B, turn: Math.round((Math.acos(Math.min(1, M3.dot(A.f, B.f))) * 180) / Math.PI), cam: TL.tv.at(tc + 0.004).cam };
    });
    const per = {};
    for (const m of TL.impacts) if (m.t >= t0 && m.t < t1) { const b = Math.floor(T.barOf(m.t)); per[b] = per[b] || { n: 0, amp: 0, flash: 0 }; per[b].n++; per[b].amp += m.amp; per[b].flash += m.flash || 0; }
    return { cuts, impacts: per };
  }, [b0, b1]);
  // the frames on either side of each cut
  for (const [i, c] of r.cuts.entries()) {
    for (const [k, t] of [['a', c.t - 0.017], ['b', c.t + 0.004]]) {
      const url = await page.evaluate((t) => window.MV.exportFrame(+t, 'image/png'), t);
      fs.writeFileSync(path.join(out, `cut_${String(i).padStart(2, '0')}_${k}.png`), Buffer.from(url.split(',')[1], 'base64'));
    }
  }
  fs.writeFileSync(path.join(out, 'cuts.json'), JSON.stringify(r, null, 1));
  for (const [i, c] of r.cuts.entries()) {
    const cross = c.A.side && c.B.side && c.A.side !== c.B.side ? ' LINE CROSSED' : '';
    const flip = c.A.go && c.B.go && Math.sign(c.A.go[0]) !== Math.sign(c.B.go[0]) && Math.abs(c.A.go[0]) > 15 && Math.abs(c.B.go[0]) > 15 ? ' DIRECTION FLIP' : '';
    console.log(`${String(i).padStart(2)} bar ${c.bar.toFixed(3)} ${c.cam.padEnd(5)} shots ${c.before}->${c.after} bars, turn ${c.turn} deg | soul ${JSON.stringify(c.A.soul)}->${JSON.stringify(c.B.soul)} neo ${JSON.stringify(c.A.neo)}->${JSON.stringify(c.B.neo)} | go ${JSON.stringify(c.A.go)}->${JSON.stringify(c.B.go)} roll ${c.A.roll}->${c.B.roll}${cross}${flip}`);
  }
  console.log('impacts per bar:', Object.entries(r.impacts).map(([b, v]) => `${b}:${v.n}`).join(' '));
  await browser.close();
})();
