// A still for the cover: one moment of the film rendered without the battle box and HUD, with motion blur from many
// subframes (scene time t0→t1, camera eased from cam0 to cam1 across the shutter).
//   node tools/cover.cjs <out.png> [--w=1920 --h=1080] [--json=work/cover.json]
// The json holds { t0, t1, n, cam0, cam1, center, off, sash, flash, shake, beams, halo, vig, dimBack, pa }: see the
// defaults below (center: camera on the soul, dy shifts it; off: sideways nudges { RG01, RG02, muf }; sash 0 drops the
// torn 保安 sashes; pa 0 drops the 「啪！」 text, beams 0 the three coloured lights, halo 0 the soul's glow).
// A json key replaces the default (pass "center": null / "off": {} to go back to a fixed cam0/cam1 x, y).
const { chromium, pageUrl, argsFor } = require('./pw.cjs');
const path = require('path');
const fs = require('fs');
(async () => {
  const args = process.argv.slice(2);
  const opt = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const i = a.indexOf('='); return i < 0 ? [a.slice(2), true] : [a.slice(2, i), a.slice(i + 1)]; }));
  const out = path.resolve(args.find((a) => !a.startsWith('--')) || 'dist/cover.png');
  const w = +(opt.w || 1920), h = +(opt.h || 1080);
  const C = Object.assign({
    // 48·4: the soul high-fives 01's palm. The camera sits on the soul (centre of the frame), looks up a little, tilts
    // 0.06→0.045 and zooms out 1.82→1.74 over the shutter (radial blur out of the soul); 01, Muffet and 02 stand closer
    t0: 152.335, t1: 152.375, n: 40, center: { dy: 0 }, off: { RG01: 10, RG02: -70, muf: -30 }, sash: 0,
    cam0: { zoom: 1.82, roll: 0.06, pitch: 0.09 }, cam1: { zoom: 1.74, roll: 0.045, pitch: 0.09 },
    flash: 0, shake: 0, beams: 1.7, halo: 1, vig: 0.65, dimBack: 0.5, pa: 1,
  }, opt.json ? JSON.parse(fs.readFileSync(opt.json, 'utf8')) : {});
  const browser = await chromium.launch({ args: argsFor(true) });
  const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(pageUrl(`?render=1&w=${w}&h=${h}`));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 180000 });
  const url = await page.evaluate((C) => {
    const MV = window.MV, TL = MV.TL, U = MV.U, D = MV.D;
    // no box, no HUD: the box frame and everything clipped into it go, the soul and the free battle effects stay
    D.batBox = () => {};
    TL.batEv = TL.batEv.filter((e) => e.clip !== 'box' && (C.pa || e.z !== 22));
    const bat0 = TL.bat.at.bind(TL.bat); TL.bat.at = (t) => Object.assign(bat0(t), { hud: 0, btn: 0 });
    // stand the three closer: a sideways nudge for 01, 02 and Muffet; the soul rides on 01's palm, so it moves with him
    const off = C.off || {};
    if (off.RG01 || off.RG02) { const at0 = MV.RG.at; MV.RG.at = (an, tr, t) => { const m = at0(an, tr, t); m.x += off[an] || 0; return m; }; }
    if (off.muf) { const m0 = TL.muf.at.bind(TL.muf); TL.muf.at = (t) => { const m = m0(t); m.x += off.muf; return m; }; }
    if (off.RG01) { const s0 = TL.batSoul.at.bind(TL.batSoul); TL.batSoul.at = (t) => { const s = s0(t); s.x += off.RG01; return s; }; }
    // the ripped 保安 sashes lie where their guards stood when they tore them off (tl_end.js BAND, z 2, fixed at build):
    // drop that event and lay them again beside the moved guards, in their settled place
    if ((off.RG01 || off.RG02 || C.sash === 0) && MV.SASHOFF) {
      const SPLIT = MV.T.at(46, 0, 12);
      TL.events = TL.events.filter((e) => !(e.z === 2 && Math.abs(e.t0 - SPLIT) < 1e-6));
    }
    if ((off.RG01 || off.RG02) && MV.SASHOFF && C.sash !== 0) {
      const R = Math.round, lay = [['RG01', TL.rg01, 1], ['RG02', TL.rg02, -1]].map(([an, tr, d]) => { const h = MV.COLD.head(an, tr, MV.SASHOFF[an], false); return [h[0] + 84 * d, h[1] + 140]; });
      TL.add({ t0: C.t0 - 1, t1: C.t1 + 1, z: 2, draw: (ctx) => lay.forEach(([x, y]) => {
        ctx.save(); ctx.translate(R(x), R(y)); ctx.fillStyle = '#000'; ctx.fillRect(-22, -10, 44, 20); ctx.fillStyle = '#f2f2f2'; ctx.fillRect(-20, -8, 40, 16);
        D.text(ctx, '保安', 0, -8, { scale: 1, align: 'center', color: '#111' }); ctx.restore();
      }) });
      TL.finalize();
    }
    // the camera follows the shutter, not the timeline; with center it sits on the soul (mid-shutter), so the soul is the
    // middle of the frame and the zoom blur spreads out from it (the soul is on the front plane, z 0, which the camera's
    // look-at point always lands on, whatever the pitch)
    let u = 0;
    const cam0 = TL.cam2.at.bind(TL.cam2), lerp = (a, b) => a + (b - a) * U.eOut(u), mid = C.center ? TL.batSoul.at((C.t0 + C.t1) / 2) : null;
    TL.cam2.at = (t) => { const c = cam0(t); for (const k of ['x', 'y', 'zoom', 'roll', 'pitch']) c[k] = lerp(C.cam0[k] ?? c[k], C.cam1[k] ?? c[k]); if (mid) { c.x = mid.x; c.y = mid.y + (C.center.dy || 0); } return c; };
    const fx0 = TL.fxAt; TL.fxAt = (t) => { const f = fx0(t); f.flash *= C.flash; f.sx *= C.shake; f.sy *= C.shake; f.zoom *= C.shake; f.rot *= C.shake; return f; };
    const po0 = TL.post2.at.bind(TL.post2); TL.post2.at = (t) => Object.assign(po0(t), { vig: C.vig, dimBack: C.dimBack });
    // three judges: a top light behind each of 01, Muffet and 02 in their own colours (01 red, Muffet purple, 02 gold),
    // on the mid plane so it rims the three from behind, plus a soft glow pool where each light lands
    const BEAMS = C.beamAt || [[300, [255, 70, 80]], [480, [205, 120, 255]], [660, [255, 200, 70]]];
    if (C.beams) {
      const beam = (ctx, x, top, w0, w1, y1, col, a) => {
        const rgb = col.join(','), g = ctx.createLinearGradient(0, top, 0, y1); g.addColorStop(0, `rgba(${rgb},${a})`); g.addColorStop(0.75, `rgba(${rgb},${a * 0.45})`); g.addColorStop(1, `rgba(${rgb},0)`);
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x - w0, top); ctx.lineTo(x + w0, top); ctx.lineTo(x + w1, y1); ctx.lineTo(x - w1, y1); ctx.fill();
        const r = ctx.createRadialGradient(x, y1 - 60, 0, x, y1 - 60, w1 * 1.1); r.addColorStop(0, `rgba(${rgb},${a * 0.9})`); r.addColorStop(1, `rgba(${rgb},0)`);
        ctx.fillStyle = r; ctx.fillRect(x - w1 * 1.2, y1 - 60 - w1 * 1.2, w1 * 2.4, w1 * 2.4);
      };
      TL.add({ t0: C.t0 - 1, t1: C.t1 + 1, z: -150, draw: (ctx) => {
        ctx.save(); ctx.globalCompositeOperation = 'lighter';
        BEAMS.forEach(([x, col], i) => beam(ctx, x, -320, i === 1 ? 18 : 14, i === 1 ? 150 : 125, 330, col, (i === 1 ? 0.34 : 0.3) * C.beams));
        ctx.restore();
      } });
      TL.finalize();
    }
    // the soul they judge: a soft red glow round it
    if (C.halo) TL.batEv.push({ t0: C.t0 - 1, t1: C.t1 + 1, z: 30, draw: (ctx, t) => {
      const s = TL.batSoul.at(t), r = 46 * C.halo, g = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, r);
      g.addColorStop(0, 'rgba(255,60,70,0.55)'); g.addColorStop(0.4, 'rgba(255,40,60,0.22)'); g.addColorStop(1, 'rgba(255,40,60,0)');
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.fillRect(s.x - r, s.y - r, 2 * r, 2 * r); ctx.restore();
    } });
    const src = document.getElementById('mv'), acc = document.createElement('canvas'); acc.width = src.width; acc.height = src.height;
    const x = acc.getContext('2d');
    for (let i = 0; i < C.n; i++) {
      u = C.n > 1 ? i / (C.n - 1) : 0;
      MV.renderFrame(C.t0 + (C.t1 - C.t0) * u);
      x.globalAlpha = 1 / (i + 1); x.drawImage(src, 0, 0);
    }
    return acc.toDataURL('image/png');
  }, C);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  console.log('wrote', out, JSON.stringify(C));
  await browser.close();
})();
