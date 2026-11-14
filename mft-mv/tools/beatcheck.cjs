// The beat check: everything in a span of bars that should land on the music - the camera's hits
// (impacts), the sounds, the camera's cuts and sudden stops / starts, the box's swings, the soul's hops
// between strings - each placed on its 16th, with how far off the grid it is and what the music measurably
// does there (MV.T.acc: digits 0-9, high band | low band). Flags:
//   OFF   off the grid (15 ms; hops 35 ms, the middle of the hop; swings 25 ms; a whoosh leading into a
//         hit - swipe, bombfall - may come up to 60 ms early)
//   HOLE  nothing in the music there (high < 0.3 and low < 0.6)
//   WEAK  a big move (a hard hit, a cut, a camera stop, a swing past 10°) where only the bass plays (in
//         the held bars - 3, 7, 11, 15: next to nothing in the highs - a bass note counts as a beat, and so
//         does any 8th: their melody and harmony go on in 8ths, in the middle register, which the bands
//         here do not catch)
//   FREE  the soul drawn upright in a turned box - not on its strings
// The soul is read off the drawing (any box layer's soul sprite, or the game's own soul) and taken back
// into the box's frame, so a turning box is not counted as hops.
// Usage: node tools/beatcheck.cjs <bar0> <bar1> [--all]   (--all lists every event, not just the flagged)
const { chromium, pageUrl, SWIFT } = require('./pw.cjs');
(async () => {
  const args = process.argv.slice(2), all = args.includes('--all');
  const [b0 = 0, b1 = 16] = args.filter((a) => !a.startsWith('--')).map(Number);
  const browser = await chromium.launch({ args: SWIFT });
  const page = await browser.newPage({ viewport: { width: 320, height: 180 } });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  page.on('console', (m) => { if (m.type() === 'warning' || m.type() === 'error') console.log('[page]', m.text()); });
  await page.goto(pageUrl('?render=1&w=320&h=180'));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 180000 });
  const res = await page.evaluate(([b0, b1]) => {
    const MV = window.MV, T = MV.T, TL = MV.TL, S16 = T.s16, t0 = T.at(b0), t1 = T.at(b1);
    const TOL = { hop: 0.035, swing: 0.025 }, LEAD = /swipe|bombfall/;
    // (a held bar: next to nothing in the highs all bar)
    const held = (bar) => { let s = 0; for (let i = 0; i < 16; i++) s += T.acc(bar * 16 + i, 'high'); return s < 2.5; };
    const ev = [];
    const add = (t, kind, what, big = false) => {
      const p = (t - T.off) / S16, n = Math.round(p), hi = T.acc(n, 'high'), lo = T.acc(n, 'low'), off = (p - n) * S16, flags = [], bar = Math.floor(n / 16);
      const tol = TOL[kind] ?? 0.015, early = kind === 'sfx' && LEAD.test(what) && off < 0 && off > -0.06;
      if (Math.abs(off) > tol && !early) flags.push('OFF');
      if (hi < 0.3 && lo < 0.6) flags.push('HOLE');
      else if (big && hi < 0.5 && (held(bar) ? lo < 0.75 && n % 2 : lo < 0.85)) flags.push('WEAK');
      ev.push({ t, kind, what, bar, s: ((n % 16) + 16) % 16, off: Math.round(off * 1000), hi, lo, flags });
    };
    // ---- hits and sounds
    for (const m of TL.impacts) if (m.t >= t0 && m.t < t1 && (m.amp >= 3 || m.zoom >= 0.03 || m.flash > 0)) add(m.t, 'hit', `amp ${m.amp}${m.zoom ? ' zoom ' + m.zoom : ''}${m.flash ? ' flash' : ''}`, m.amp >= 5 || m.zoom >= 0.03);
    const VOICE = /txt|Txt|BattleText|snd_tem|squeak|Menu|movemenu/;
    for (const e of TL.sfx) if (e.t >= t0 && e.t < t1 && e.vol >= 0.6 && !VOICE.test(e.name)) add(e.t, 'sfx', e.name);
    // ---- the keyframed camera at 60 fps: cuts, dead stops, jump starts, jerks (a frame whose change of
    // speed stands out from its neighbours' - not a smooth ease, however fast); each put at the keyframe
    // boundary that makes it, when there is one in its frame (screen px a frame)
    {
      const F = 1 / 60, cutAt = (t) => TL.cam2.segs.some((g) => g.t1 - g.t0 < 1e-6 && g.t0 > t - F && g.t0 <= t);
      // (speed is measured between frames, so a boundary up to two frames back shows on this one)
      const edge = (t) => { let best = null; for (const g of TL.cam2.segs) for (const e of [g.t0, g.t1]) if (e > t - 2 * F - 1e-9 && e <= t + 1e-9 && (best === null || e > best)) best = e; return best ?? t - F / 2; };
      const vel = (a, b) => [(b.x - a.x) * b.zoom + (b.yaw - a.yaw) * 700 + (b.roll - a.roll) * 300, (b.y - a.y) * b.zoom + (b.pitch - a.pitch) * 700, (b.zoom / a.zoom - 1) * 480];
      const fr = [];
      let pc = TL.cam2.at(t0 - F);
      for (let i = 0; t0 + i * F < t1; i++) { const t = t0 + i * F, c = TL.cam2.at(t), cut = cutAt(t), v = vel(pc, c); fr.push({ t, cut, v, sp: cut ? 0 : Math.hypot(...v) }); pc = c; }
      const dvAt = (i) => (i <= 0 || i >= fr.length || fr[i].cut || fr[i - 1].cut ? 0 : Math.hypot(...fr[i].v.map((x, k) => x - fr[i - 1].v[k])));
      for (let i = 1; i < fr.length; i++) {
        const f = fr[i], p = fr[i - 1];
        if (f.cut) { add(f.t, 'cam', 'cut', true); continue; }
        if (p.cut) continue;
        const dv = dvAt(i);
        if (p.sp > 1.5 && f.sp < 0.1) add(edge(f.t), 'cam', `dead stop (${p.sp.toFixed(1)} px/frame -> 0)`, true);
        else if (p.sp < 0.1 && f.sp > 1.5) add(edge(f.t), 'cam', `jump start (0 -> ${f.sp.toFixed(1)})`, true);
        else if (dv > 4 && dv > 2.5 * Math.max(dvAt(i - 1), dvAt(i + 1))) add(edge(f.t), 'cam', `jerk ${dv.toFixed(1)}`, true);
      }
    }
    // ---- the box: its transform (read off the path it clips with), its swings
    const cv = document.createElement('canvas').getContext('2d');
    const skinM = (t) => {
      const sk = MV.boxSkin && MV.boxSkin(t);
      if (!sk) return null;
      let m = null;
      const grab = (k) => { const f = CanvasRenderingContext2D.prototype[k]; cv[k] = function (...a) { m = m || cv.getTransform(); return f.apply(cv, a); }; };
      grab('moveTo'); grab('rect');
      cv.setTransform(1, 0, 0, 1, 0, 0); cv.beginPath();
      try { sk.path(cv); } finally { delete cv.moveTo; delete cv.rect; }
      return m;
    };
    {
      const F = 1 / 60, A = [];
      let la = null, acc = 0;
      for (let i = 0; t0 + i * F < t1; i++) {
        const m = skinM(t0 + i * F);
        if (!m) { A.push(null); la = null; continue; }
        const a = (Math.atan2(m.b, m.a) * 180) / Math.PI;
        if (la !== null) { let d = a - la; while (d > 180) d -= 360; while (d < -180) d += 360; acc += d; } else acc = a;
        la = a; A.push(acc);
      }
      // (a turn counts when it is a real one - the box at least a degree back from it within a 16th on both
      // sides, the other way each side - and sharp: a few degrees back on one side; a slow sway's turn is no
      // hit, nor a hold that only creeps before the next move; big: past 10° and turning hard)
      const n = 8;
      for (let i = 1; i + 1 < A.length; i++) {
        const [p, q, r] = [A[i - 1], A[i], A[i + 1]];
        if (p === null || q === null || r === null || !((q - p) * (r - q) < 0) || Math.abs(q) <= 3) continue;
        const before = q - (A[i - n] ?? q), after = (A[i + n] ?? q) - q;
        if (Math.sign(before) === Math.sign(after) || Math.min(Math.abs(before), Math.abs(after)) < 1) continue;
        const sharp = Math.max(Math.abs(before), Math.abs(after));
        if (sharp > 2) add(t0 + i * F, 'swing', `${q.toFixed(0)}° (turning ${sharp.toFixed(0)}°)`, Math.abs(q) > 10 && sharp > 6);
      }
    }
    // ---- the soul: where it is drawn (the box's own layers, else the game's soul), in the box's frame
    {
      const F = 1 / 30, SOULS = new Set([MV.SPR.soul, MV.SPR.soulPurple]);
      const rec = document.createElement('canvas'); rec.width = 1200; rec.height = 900;
      const rx = rec.getContext('2d'), di = CanvasRenderingContext2D.prototype.drawImage;
      const soulAt = (t) => {
        let found = null;
        rx.drawImage = function (im, ...a) {
          if (!found && SOULS.has(im)) {
            const [x, y, w, h] = a.length >= 8 ? [a[4], a[5], a[6], a[7]] : a.length >= 4 ? a : [a[0], a[1], im.width, im.height];
            const p = rx.getTransform().transformPoint({ x: x + w / 2, y: y + h / 2 });
            found = [p.x, p.y];
          }
          return di.call(rx, im, ...a);
        };
        try {
          for (const e of TL.batEv) if (e.clip === 'box' && t >= e.t0 && t < e.t1) { rx.save(); rx.setTransform(1, 0, 0, 1, 0, 0); try { e.draw(rx, t); } catch (err) {} rx.restore(); }
        } finally { delete rx.drawImage; }
        if (found) return { p: found, drawn: true };
        const s = TL.batSoul.at(t);
        return s.a > 0.5 && TL.bat.at(t).a > 0.5 ? { p: [s.x, s.y], drawn: false } : null;
      };
      let prev = null, run = null, freeFrom = null;
      for (let i = 0; t0 + i * F < t1; i++) {
        const t = t0 + i * F, s = soulAt(t), m = skinM(t), ang = m ? Math.abs(Math.atan2(m.b, m.a)) : 0;
        // (the game's soul in a turned box: not on its strings)
        const free = s && !s.drawn && ang > 0.02;
        if (free && freeFrom === null) freeFrom = t;
        if (!free && freeFrom !== null) { add(freeFrom, 'soul', `FREE until ${T.barOf(t).toFixed(2)}`, false); ev[ev.length - 1].flags.push('FREE'); freeFrom = null; }
        if (!s) { prev = null; continue; }
        const q = s.drawn && m ? m.inverse().transformPoint({ x: s.p[0], y: s.p[1] }) : { x: s.p[0], y: s.p[1] };
        if (prev) {
          // (a hop: a run of frames moving across the strings; its time is its middle - a turn back the
          // other way is a new hop)
          const dy = q.y - prev.y, d = Math.sign(dy);
          if (run && (Math.abs(dy) <= 8 || d !== run.d)) { add((run.t + prev.t) / 2, 'hop', run.d < 0 ? 'up' : 'down'); run = null; }
          if (Math.abs(dy) > 8 && !run) run = { t: prev.t, d };
        }
        prev = { y: q.y, t };
      }
      if (freeFrom !== null) { add(freeFrom, 'soul', 'FREE to the end', false); ev[ev.length - 1].flags.push('FREE'); }
    }
    ev.sort((a, b) => a.t - b.t);
    const accLine = (b) => { const d = (band) => Array.from({ length: 16 }, (_, s) => Math.min(9, Math.floor(T.acc(b * 16 + s, band) * 10))).join('').replace(/(.{4})(?=.)/g, '$1 '); return `hi ${d('high')}  lo ${d('low')}`; };
    const bars = [];
    for (let b = b0; b < b1; b++) bars.push({ b, acc: accLine(b) });
    return { ev, bars };
  }, [b0, b1]);
  const digit = (v) => Math.min(9, Math.floor(v * 10));
  const count = {};
  for (const { b, acc } of res.bars) {
    const list = res.ev.filter((e) => e.bar === b && (all || e.flags.length));
    console.log(`\nbar ${String(b).padStart(2)}  ${acc}`);
    for (const e of list) {
      console.log(`  ${(e.bar + '·' + e.s).padEnd(6)} ${((e.off > 0 ? '+' : '') + e.off + 'ms').padStart(6)}  ${e.kind.padEnd(5)} ${e.what.padEnd(30)} hi${digit(e.hi)} lo${digit(e.lo)}  ${e.flags.join(' ')}`);
    }
  }
  for (const e of res.ev) for (const f of e.flags) { const k = `${f} ${e.kind}`; count[k] = (count[k] || 0) + 1; }
  console.log('\nflagged:', Object.keys(count).length ? Object.entries(count).map(([k, n]) => `${k} ${n}`).join(', ') : 'none', `(of ${res.ev.length} events)`);
  await browser.close();
})();
