const { chromium, pageUrl, argsFor } = require('./pw.cjs');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const opt = Object.fromEntries(process.argv.slice(2).map((a) => { const [k, ...v] = a.replace(/^--/, '').split('='); return [k, v.length ? v.join('=') : true]; }));
const FFMPEG = process.env.FFMPEG || 'ffmpeg';
const FPS = +(opt.fps || 60), W = +(opt.w || 1920), H = +(opt.h || 1080), WORKERS = +(opt.workers || 2);
const OUT = path.resolve(ROOT, opt.out || `dist/mv_${H}p${FPS}.mp4`);
const LIMIT = opt.limit !== undefined && opt.limit !== '0';
const TMP = path.join(ROOT, 'dist', '.tmp');
const VCODEC = opt.vcodec || 'libx264';
const VOPTS = (opt.vopts || (VCODEC === 'libx264' ? '-preset medium -crf 20 -tune animation' : VCODEC.includes('nvenc') ? '-preset p5 -rc vbr -cq 19 -b:v 0' : '-b:v 40M')).split(/\s+/).filter(Boolean);
const AR = 48000;
const MUSIC_GAIN = 0.85;
const SFX_GAIN = 0.85;
const CEILING = 10 ** (-1 / 20);
function aacArgs() {
  try {
    const list = execFileSync(FFMPEG, ['-hide_banner', '-encoders'], { encoding: 'utf8' });
    if (/\baac_mf\b/.test(list)) return ['-c:a', 'aac_mf', '-b:a', '320k'];
  } catch (_) {}
  return ['-c:a', 'aac', '-b:a', '320k', '-aac_coder', 'twoloop'];
}
const AAC = aacArgs();
fs.mkdirSync(TMP, { recursive: true });
fs.mkdirSync(path.dirname(OUT), { recursive: true });

const ARGS = argsFor(opt.gpu);
const QUERY = `?render=1&w=${W}&h=${H}` + (opt.lab && opt.lab !== true ? `&lab=${opt.lab}` : '');

async function openPage() {
  const browser = await chromium.launch({ args: ARGS, headless: !opt.headful, channel: opt.channel || undefined });
  const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto(pageUrl(QUERY));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 120000 });
  return { browser, page };
}

function decode(file) {
  const raw = execFileSync(FFMPEG, ['-v', 'error', '-i', file, '-af', 'aresample=resampler=soxr', '-f', 'f32le', '-ac', '2', '-ar', String(AR), '-'], { maxBuffer: 1 << 30 });
  return new Float32Array(raw.buffer, raw.byteOffset, raw.length / 4);
}
function limit(x, ceiling) {
  const N = x.length / 2, Wn = Math.round(AR * 0.005), rel = Math.exp(-1 / (AR * 0.08));
  const need = new Float32Array(N);
  for (let i = 0; i < N; i++) { const p = Math.max(Math.abs(x[2 * i]), Math.abs(x[2 * i + 1])); need[i] = p > ceiling ? ceiling / p : 1; }
  const g1 = new Float32Array(N), dq = new Int32Array(N);
  let h = 0, tl = 0;
  for (let i = 0; i < N; i++) {
    while (tl > h && need[dq[tl - 1]] >= need[i]) tl--;
    dq[tl++] = i;
    if (dq[h] <= i - Wn) h++;
    g1[i] = need[dq[h]];
  }
  let sum = 0, g = 1, reduced = 0;
  for (let i = 0; i < Wn && i < N; i++) sum += g1[i];
  for (let i = 0; i < N; i++) {
    const g2 = sum / Wn;
    sum += (i + Wn < N ? g1[i + Wn] : 1) - g1[i];
    g = Math.min(g2, 1 - (1 - g) * rel);
    if (g < 0.999) reduced++;
    x[2 * i] *= g; x[2 * i + 1] *= g;
  }
  return reduced / AR;
}
function mixAudio(sfx, wavPath, o) {
  const src = fs.readFileSync(path.join(ROOT, 'src/assets.js'), 'utf8');
  const assets = JSON.parse(src.slice(src.indexOf('{'), src.lastIndexOf('}') + 1));
  const bank = {};
  for (const name of new Set(sfx.map((e) => e.name))) {
    const url = assets.sfx[name];
    if (!url) continue;
    const f = path.join(TMP, name.replace(/[^\w.-]+/g, '_') + '.snd');
    fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64'));
    bank[name] = decode(f);
  }
  const dec = {}, fade = Math.round(0.03 * AR);
  const tracks = o.music.map((m) => {
    const all = dec[m.src] || (dec[m.src] = decode(path.join(ROOT, m.src))), a = Math.round((m.off || 0) * AR) * 2, n = m.dur ? Math.round(m.dur * AR) * 2 : all.length - a, pcm = all.slice(a, a + n);
    if (m.off) for (let i = 0; i < fade * 2 && i < pcm.length; i++) pcm[i] *= Math.floor(i / 2) / fade;
    if (m.dur) for (let i = 0; i < fade * 2 && i < pcm.length; i++) pcm[pcm.length - 1 - i] *= Math.floor(i / 2) / fade;
    return { pcm, m0: Math.round(m.t0 * AR) * 2 };
  });
  const mix = new Float32Array(Math.max(...tracks.map((k) => k.m0 + k.pcm.length), Math.ceil(o.dur * AR) * 2));
  for (const k of tracks) for (let i = 0; i < k.pcm.length && k.m0 + i < mix.length; i++) if (k.m0 + i >= 0) mix[k.m0 + i] += k.pcm[i] * MUSIC_GAIN;
  const resampled = {};
  const at = (name, r) => {
    const k = name + '@' + r;
    if (resampled[k]) return resampled[k];
    const s = bank[name], n = Math.floor(s.length / 2 / r) - 1, out = new Float32Array(Math.max(0, n) * 2);
    for (let i = 0; i < n; i++) { const p = i * r, j = Math.floor(p), f = p - j; out[2 * i] = s[2 * j] * (1 - f) + s[2 * j + 2] * f; out[2 * i + 1] = s[2 * j + 1] * (1 - f) + s[2 * j + 3] * f; }
    return (resampled[k] = out);
  };
  for (const e of sfx) {
    if (!bank[e.name]) { console.warn('missing sound', e.name); continue; }
    const s = e.rate ? at(e.name, e.rate) : bank[e.name];
    const i0 = Math.round(e.t * AR) * 2;
    const g = e.vol * SFX_GAIN;
    const n = e.end !== undefined ? Math.min(s.length, Math.max(0, Math.round((e.end + (e.fade || 0) - e.t) * AR)) * 2) : s.length;
    const c0 = e.end !== undefined ? Math.round((e.end - e.t) * AR) * 2 : n, cn = Math.max(2, Math.round((e.fade || 0) * AR) * 2);
    for (let i = 0; i < n && i0 + i < mix.length; i++) {
      if (i0 + i < 0) continue;
      const k = i < c0 ? 1 : 0.5 + 0.5 * Math.cos(Math.PI * Math.min(1, (i - c0) / cn));
      mix[i0 + i] += s[i] * g * k;
    }
  }
  if (o.fadeIn > 0) {
    const a = Math.round(o.fadeIn * AR), n = Math.round(0.012 * AR);
    for (let i = 0; i < n && (a + i) * 2 + 1 < mix.length; i++) { mix[(a + i) * 2] *= i / n; mix[(a + i) * 2 + 1] *= i / n; }
  }
  let limited = 0;
  if (o.limit) limited = limit(mix, CEILING * 0.98);
  let peak = 0;
  for (let i = 0; i < mix.length; i++) {
    const a = Math.abs(mix[i]);
    if (a > peak) peak = a;
  }
  const scale = peak > CEILING ? CEILING / peak : 1;
  if (o.limit) console.log(`limiter active for ${limited.toFixed(2)} s`);
  const bytes = mix.length * 4;
  const pcm = Buffer.alloc(bytes);
  for (let i = 0; i < mix.length; i++) pcm.writeFloatLE(mix[i] * scale, i * 4);
  const hdr = Buffer.alloc(44);
  hdr.write('RIFF', 0); hdr.writeUInt32LE(36 + bytes, 4); hdr.write('WAVE', 8); hdr.write('fmt ', 12);
  hdr.writeUInt32LE(16, 16); hdr.writeUInt16LE(3, 20); hdr.writeUInt16LE(2, 22); hdr.writeUInt32LE(AR, 24);
  hdr.writeUInt32LE(AR * 8, 28); hdr.writeUInt16LE(8, 32); hdr.writeUInt16LE(32, 34); hdr.write('data', 36); hdr.writeUInt32LE(bytes, 40);
  fs.mkdirSync(path.dirname(wavPath), { recursive: true });
  fs.writeFileSync(wavPath, Buffer.concat([hdr, pcm]));
  console.log(`mixed ${sfx.length} sfx -> ${wavPath}  peak ${peak.toFixed(3)}  scale ${scale.toFixed(3)}  ${AR} Hz float`);
}

const MB = +(opt.mb || 8);
function grab([t, n, dt]) {
  const MV = window.MV, B = MV.MB;
  if (n < 2 || !B || !B.spans.some(([a, b]) => t >= a && t < b) || B.off.some(([a, b]) => t >= a - 1e-6 && t < b)) return MV.exportFrame(t, 'image/jpeg', 0.95);
  const src = document.getElementById('mv'), cut = B.cuts.find((c) => c > t + 1e-6 && c < t + dt);
  const c = MV._mb || (MV._mb = document.createElement('canvas')); c.width = src.width; c.height = src.height;
  const x = c.getContext('2d');
  for (let i = 0, k = 0; i < n; i++) {
    const s = t + (i / n) * dt; if (cut && s >= cut) break;
    MV.renderFrame(s); x.globalAlpha = 1 / ++k; x.drawImage(src, 0, 0);
  }
  return c.toDataURL('image/jpeg', 0.95);
}
async function worker(id, f0, f1) {
  const { browser, page } = await openPage();
  let ff = null, seg = null;
  if (!opt.frames) {
    seg = path.join(TMP, `seg_${String(id).padStart(2, '0')}.mp4`);
    ff = spawn(FFMPEG, ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', VCODEC, ...VOPTS, '-pix_fmt', 'yuv420p', '-r', String(FPS), seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  }
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    const url = await page.evaluate(grab, [f / FPS, MB, 1 / FPS]);
    const buf = Buffer.from(url.slice(url.indexOf(',') + 1), 'base64');
    if (ff) { if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r)); }
    else fs.writeFileSync(path.join(opt.frames, String(f).padStart(5, '0') + '.jpg'), buf);
    if ((f - f0) % 120 === 0) {
      const done = f - f0 + 1, rate = done / ((Date.now() - t0) / 1000);
      console.log(`[w${id}] ${done}/${f1 - f0} frames  ${rate.toFixed(1)} fps  eta ${((f1 - f) / rate / 60).toFixed(1)} min`);
    }
  }
  if (ff) {
    const code = await new Promise((r) => { ff.on('close', r); ff.stdin.end(); });
    if (code) throw new Error(`ffmpeg worker ${id} exited ${code}`);
  }
  await browser.close();
  return seg;
}

(async () => {
  const { browser, page } = await openPage();
  const info = await page.evaluate(() => ({ music: window.MV.MUSIC, end: window.MV.T.end, cut: window.MV.T.cut, sfx: window.MV.TL.sfx }));
  await browser.close();
  const t0 = +(opt.t0 ?? info.cut.t0), t1 = +(opt.t1 ?? info.cut.t1);
  const F0 = Math.round(t0 * FPS), F1 = Math.round(t1 * FPS);
  if (opt.frames) opt.frames = path.resolve(ROOT, opt.frames);
  const wav = opt.frames
    ? path.join(path.dirname(opt.frames), 'mix.wav')
    : (opt['audio-only']
      ? (String(opt.out || '').toLowerCase().endsWith('.wav') ? OUT : path.join(ROOT, 'dist/mix_hq.wav'))
      : path.join(TMP, 'mix.wav'));
  if (opt.frames) fs.mkdirSync(opt.frames, { recursive: true });
  mixAudio(info.sfx, wav, { music: info.music, dur: Math.max(info.end, t1), limit: LIMIT, fadeIn: t0 });
  if (opt['audio-only']) return;
  console.log(`rendering ${F1 - F0} frames (${t0}s-${t1}s) at ${W}x${H}@${FPS}, ${WORKERS} workers, ${opt.gpu ? 'GPU' : 'SwiftShader'}`);
  const per = Math.ceil((F1 - F0) / WORKERS), jobs = [];
  for (let i = 0; i < WORKERS; i++) {
    const a = F0 + i * per, b = Math.min(F1, a + per);
    if (a < b) jobs.push(worker(i, a, b));
  }
  const segs = await Promise.all(jobs);
  if (opt.frames) {
    const rel = (p) => path.relative(ROOT, p).replace(/\\/g, '/');
    console.log('\nframes written. encode with e.g.:');
    console.log(`ffmpeg -framerate ${FPS} -start_number ${F0} -i ${rel(opt.frames)}/%05d.jpg -ss ${t0} -i ${rel(wav)} -map 0:v -map 1:a -c:v libx264 -preset medium -crf 20 -tune animation -pix_fmt yuv420p ${AAC.join(' ')} -shortest -movflags +faststart ${rel(OUT)}`);
    return;
  }
  const list = path.join(TMP, 'segs.txt');
  fs.writeFileSync(list, segs.filter(Boolean).map((s) => `file '${path.resolve(s).replace(/\\/g, '/')}'`).join('\n'));
  execFileSync(FFMPEG, ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-ss', String(t0), '-t', String(t1 - t0), '-i', wav,
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', ...AAC, '-shortest', '-movflags', '+faststart', OUT], { stdio: 'inherit' });
  console.log('wrote', OUT, (fs.statSync(OUT).size / 1e6).toFixed(1), 'MB');
})().catch((e) => { console.error(e); process.exit(1); });
