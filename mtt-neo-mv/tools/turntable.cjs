// Turntable of his 3D rig in one form, from several sides (checking the voxel model against
// the concept sheets in work/concept/).
// Usage: node tools/turntable.cjs <outDir> [--jet=1] [--bar=12.5] [--dist=420] [--gpu]
const { chromium, pageUrl, argsFor } = require('./pw.cjs');
const path = require('path');
const fs = require('fs');
(async () => {
  const args = process.argv.slice(2);
  const opts = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const [k, v] = a.slice(2).split('='); return [k, v ?? true]; }));
  const [out] = args.filter((a) => !a.startsWith('--'));
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: argsFor(opts.gpu) });
  const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(pageUrl('?render=1&w=960&h=540'));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 120000 });
  const jet = +(opts.jet ?? 1), bar = +(opts.bar ?? 12.5), dist = +(opts.dist ?? 420);
  // views: name, camera offset direction (from him), up
  const views = [['top', [0, 1, 0.001], [0, 0, 1]], ['side', [1, 0.05, 0], [0, 1, 0]], ['front', [0, 0.05, 1], [0, 1, 0]], ['three', [0.8, 0.5, 0.9], [0, 1, 0]], ['rear', [-0.7, 0.35, -1], [0, 1, 0]], ['under', [0.3, -1, 0.4], [0, 1, 0]]];
  for (const [name, dir, up] of views) {
    const url = await page.evaluate(([jet, bar, dist, dir, up]) => {
      const MV = window.MV, t = MV.T.at(bar);
      const P = [0, -2600, 0];
      const l = Math.hypot(...dir);
      MV.W3.debug = {
        neo: { x: P[0], y: P[1], z: P[2], yaw: 0, pitch: 0, roll: 0, aim: 0, ghost: 0, a: 1, sc: 1, light: 1, thrust: jet, shake: 0 },
        pose: { jet, aC: 0, aB: 0, lL: 0, lR: 0, wL: 0, wR: 0, ws: 1, kL: 0, kR: 0, eC: 0, eB: 0, yC: 0, yB: 0, wf: 0 },
        cam: { pos: [P[0] + dir[0] / l * dist, P[1] + dir[1] / l * dist, P[2] + dir[2] / l * dist], at: P, up },
      };
      return MV.exportFrame(t, 'image/png');
    }, [jet, bar, dist, dir, up]);
    fs.writeFileSync(path.join(out, `${name}.png`), Buffer.from(url.split(',')[1], 'base64'));
  }
  await browser.close();
})();
