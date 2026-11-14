// Offline export: renders every frame in (headless) Chromium, mixes the sound effects over the
// soundtrack (MV.MUSIC: each file at its start time - "But the Earth Refused to Die" after the cold
// open, then Battle Against a True Hero), and encodes an MP4 - or just writes a frame sequence.
// From ../mtt-neo-mv/tools/render.cjs.
//
//   node tools/render.cjs [options]
//
// Options (all optional):
//   --cut=tiktok                     the vertical version (1080x1920): the whole film reframed to 9:16,
//                                    same soundtrack
//   --fps=60 --w=1920 --h=1080       output format
//   --t0=0 --t1=178.6                time range in seconds (default: the whole video)
//   --limit                          look-ahead peak limiter on the mix instead of scaling the whole
//                                    mix down when the sound effects push it over (default: off)
//   --workers=2                      parallel browser instances
//   --gpu                            render WebGL on the real GPU (default: SwiftShader, CPU)
//   --channel=chrome                 use an installed Chrome/Edge instead of Playwright's Chromium
//   --headful                        show the browser windows (some GPU drivers need this)
//   --vcodec=libx264                 e.g. h264_nvenc | hevc_nvenc | h264_amf | h264_qsv | libx264
//   --vopts="-preset p5 -cq 19"      extra encoder options (default depends on --vcodec)
//   --frames=dist/frames             write JPEG frames + dist/mix.wav instead of encoding
//   --audio-only                     mix the soundtrack and exit (no video)
//   --out=dist/mv_1080p60.mp4
// Environment: FFMPEG=/path/to/ffmpeg (default: ffmpeg on PATH)
const { chromium, pageUrl, argsFor } = require('./pw.cjs');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const opt = Object.fromEntries(process.argv.slice(2).map((a) => { const [k, ...v] = a.replace(/^--/, '').split('='); return [k, v.length ? v.join('=') : true]; }));
const FFMPEG = process.env.FFMPEG || 'ffmpeg';
const CUT = opt.cut && opt.cut !== true ? opt.cut : '';
const VERTICAL = CUT === 'tiktok';
const FPS = +(opt.fps || 60), W = +(opt.w || (VERTICAL ? 1080 : 1920)), H = +(opt.h || (VERTICAL ? 1920 : 1080)), WORKERS = +(opt.workers || 2);
const OUT = path.resolve(ROOT, opt.out || (CUT ? `dist/mv_${CUT}_${W}x${H}_${FPS}.mp4` : `dist/mv_${H}p${FPS}.mp4`));
const LIMIT = opt.limit !== undefined && opt.limit !== '0';
const TMP = path.join(ROOT, 'dist', '.tmp');
const VCODEC = opt.vcodec || 'libx264';
const VOPTS = (opt.vopts || (VCODEC === 'libx264' ? '-preset medium -crf 20 -tune animation' : VCODEC.includes('nvenc') ? '-preset p5 -rc vbr -cq 19 -b:v 0' : '-b:v 40M')).split(/\s+/).filter(Boolean);
const AR = 48000;
const MUSIC_GAIN = 10 ** (-1.5 / 20); // the music sits just under full scale: the beds no longer bury it
const CEILING = 10 ** (-1 / 20);    // -1 dBFS encoder true-peak margin
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
// (--lab=<name>: a lab reel instead of the film, src/tl_lab.js)
const QUERY = `?render=1&w=${W}&h=${H}` + (CUT ? `&cut=${CUT}` : '') + (opt.lab && opt.lab !== true ? `&lab=${opt.lab}` : '');

async function openPage() {
  const browser = await chromium.launch({ args: ARGS, headless: !opt.headful, channel: opt.channel || undefined });
  const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto(pageUrl(QUERY));
  await page.waitForFunction(() => window.MV && window.MV.ready, null, { timeout: 120000 });
  return { browser, page };
}

// ---------------------------------------------------------------- audio: music + sound effects
function decode(file) {
  const raw = execFileSync(FFMPEG, ['-v', 'error', '-i', file, '-af', 'aresample=resampler=soxr', '-f', 'f32le', '-ac', '2', '-ar', String(AR), '-'], { maxBuffer: 1 << 30 });
  return new Float32Array(raw.buffer, raw.byteOffset, raw.length / 4);
}
// Look-ahead peak limiter on interleaved stereo: the gain reaches its target 5 ms before
// each peak (trailing min + box average) and recovers over ~80 ms, so only the few
// overshooting transients are turned down instead of the whole mix.
function limit(x, ceiling) {
  const N = x.length / 2, Wn = Math.round(AR * 0.005), rel = Math.exp(-1 / (AR * 0.08));
  const need = new Float32Array(N);
  for (let i = 0; i < N; i++) { const p = Math.max(Math.abs(x[2 * i]), Math.abs(x[2 * i + 1])); need[i] = p > ceiling ? ceiling / p : 1; }
  const g1 = new Float32Array(N), dq = new Int32Array(N);
  let h = 0, tl = 0;
  for (let i = 0; i < N; i++) { // min over need[i - Wn + 1 .. i]
    while (tl > h && need[dq[tl - 1]] >= need[i]) tl--;
    dq[tl++] = i;
    if (dq[h] <= i - Wn) h++;
    g1[i] = need[dq[h]];
  }
  let sum = 0, g = 1, reduced = 0;
  for (let i = 0; i < Wn && i < N; i++) sum += g1[i];
  for (let i = 0; i < N; i++) { // mean over g1[i .. i + Wn - 1], then a smooth release
    const g2 = sum / Wn;
    sum += (i + Wn < N ? g1[i + Wn] : 1) - g1[i];
    g = Math.min(g2, 1 - (1 - g) * rel);
    if (g < 0.999) reduced++;
    x[2 * i] *= g; x[2 * i + 1] *= g;
  }
  return reduced / AR;
}
// RBJ biquad on one channel: 'lp' | 'hp' | 'peak' (gain dB)
function biquad(type, fc, q = 0.707, db = 0) {
  const w = (2 * Math.PI * fc) / AR, cw = Math.cos(w), al = Math.sin(w) / (2 * q), A = 10 ** (db / 40);
  let b0, b1, b2, a0, a1, a2;
  if (type === 'lp') { b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = b0; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; }
  else if (type === 'hp') { b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = b0; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; }
  else { b0 = 1 + al * A; b1 = -2 * cw; b2 = 1 - al * A; a0 = 1 + al / A; a1 = -2 * cw; a2 = 1 - al / A; }
  b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  return (x) => { const y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; };
}
// the music changed in place (interleaved stereo), README 第四幕:
//   speaker - the computer's own speakers: mono, nothing under ~350 Hz or over ~5 kHz, a honk round 2 kHz,
//             a few early reflections off the desk and the wall; crossfaded with the full sound
//   duck    - pressed down by db, with an attack and a release
function musicFx(x, fx) {
  const N = x.length / 2, i0 = Math.max(0, Math.round((fx.t0 - 0.2) * AR)), i1 = Math.min(N, Math.round((fx.t1 + (fx.out || fx.rel || 0) + 0.05) * AR));
  if (fx.kind === 'speaker') {
    const chain = [biquad('hp', 330, 0.6), biquad('hp', 330, 0.6), biquad('lp', 5200, 0.6), biquad('peak', 2100, 0.9, 4.5), biquad('lp', 7000, 0.5)];
    const echoes = [[0.011, 0.22], [0.017, 0.16], [0.023, 0.11], [0.034, 0.07]].map(([d, g]) => [Math.round(d * AR), g]);
    const wet = new Float32Array(i1 - i0);
    for (let i = i0; i < i1; i++) { let v = (x[2 * i] + x[2 * i + 1]) * 0.5; for (const f of chain) v = f(v); wet[i - i0] = v; }
    for (let i = i0; i < i1; i++) {
      const t = i / AR, w = t < fx.t0 ? 0 : t < fx.t0 + (fx.in || 0.01) ? (t - fx.t0) / (fx.in || 0.01) : t < fx.t1 ? 1 : Math.max(0, 1 - (t - fx.t1) / (fx.out || 0.01));
      if (w <= 0) continue;
      let v = wet[i - i0];
      for (const [d, g] of echoes) if (i - d >= i0) v += wet[i - d - i0] * g;
      v *= 1.35;
      x[2 * i] = x[2 * i] * (1 - w) + v * w; x[2 * i + 1] = x[2 * i + 1] * (1 - w) + v * w;
    }
  } else if (fx.kind === 'duck') {
    const g = 10 ** ((fx.db || -18) / 20), atk = fx.atk || 0.05, rel = fx.rel || 0.12;
    for (let i = i0; i < i1; i++) {
      const t = i / AR, k = t < fx.t0 ? 0 : t < fx.t0 + atk ? (t - fx.t0) / atk : t < fx.t1 ? 1 : Math.max(0, 1 - (t - fx.t1) / rel);
      const m = 1 + (g - 1) * k;
      x[2 * i] *= m; x[2 * i + 1] *= m;
    }
  }
}
//   under   - under water (the whole mix, effects too): two low-passes at ~500 Hz, crossfaded in / out
function under(x, fx) {
  const N = x.length / 2, i0 = Math.max(0, Math.round((fx.t0 - 0.1) * AR)), i1 = Math.min(N, Math.round((fx.t1 + fx.out + 0.05) * AR));
  const F = [0, 1].map(() => [biquad('lp', fx.fc || 520, 0.7), biquad('lp', fx.fc || 520, 0.7)]);
  for (let i = i0; i < i1; i++) {
    const t = i / AR, w = t < fx.t0 ? 0 : t < fx.t0 + fx.in ? (t - fx.t0) / fx.in : t < fx.t1 ? 1 : Math.max(0, 1 - (t - fx.t1) / fx.out);
    for (let c = 0; c < 2; c++) { let v = x[2 * i + c]; for (const f of F[c]) v = f(v); x[2 * i + c] = x[2 * i + c] * (1 - w) + v * 1.3 * w; }
  }
}
// o: {music: [{src, t0}], dur: video length (s), limit, fadeIn (s), musicFx: TL.musicFx}
function mixAudio(sfx, wavPath, o) {
  const gain = 0.55;
  // (the weather beds: they were as loud as the music; now they sit under it and under the blades)
  const AMBIENT = { Rain: 0.42, WindFall: 0.5, Wind: 0.65, Crumble: 0.7 };
  const src = fs.readFileSync(path.join(ROOT, 'src/assets.js'), 'utf8');
  const assets = JSON.parse(src.slice(src.indexOf('{'), src.lastIndexOf('}') + 1));
  const bank = {};
  for (const name of new Set(sfx.map((e) => e.name))) {
    const url = assets.sfx[name];
    if (!url) continue;
    const f = path.join(TMP, name + '.snd');
    fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64'));
    bank[name] = decode(f);
  }
  // procedural sounds (src/synth.js), mono -> stereo
  const SYN = require(path.join(ROOT, 'src/synth.js'));
  for (const name of new Set(sfx.map((e) => e.name))) {
    if (bank[name] || !SYN.has(name)) continue;
    const m = SYN.make(name, AR), st = new Float32Array(m.length * 2);
    for (let i = 0; i < m.length; i++) st[2 * i] = st[2 * i + 1] = m[i];
    bank[name] = st;
  }
  // each piece of the soundtrack at its start; silence pads the rest (the cold open, the epilogue)
  const tracks = o.music.map((m) => ({ pcm: decode(path.join(ROOT, m.src)), m0: Math.round(m.t0 * AR) * 2 }));
  const mix = new Float32Array(Math.max(...tracks.map((k) => k.m0 + k.pcm.length), Math.ceil(o.dur * AR) * 2));
  for (const k of tracks) for (let i = 0; i < k.pcm.length; i++) mix[k.m0 + i] += k.pcm[i] * MUSIC_GAIN;
  // (here the mix is the music alone: what the timeline does to it - TL.musicFx - goes in now, before the
  // sound effects, which play in the room as they are)
  for (const fx of o.musicFx || []) musicFx(mix, fx);
  // (e.rate: the sound played slower / faster - resampled, its pitch with it)
  const resampled = {};
  const at = (name, r) => {
    const k = name + '@' + r;
    if (resampled[k]) return resampled[k];
    const s = bank[name], n = Math.floor(s.length / 2 / r) - 1, o = new Float32Array(Math.max(0, n) * 2);
    for (let i = 0; i < n; i++) { const p = i * r, j = Math.floor(p), f = p - j; o[2 * i] = s[2 * j] * (1 - f) + s[2 * j + 2] * f; o[2 * i + 1] = s[2 * j + 1] * (1 - f) + s[2 * j + 3] * f; }
    return (resampled[k] = o);
  };
  for (const e of sfx) {
    if (!bank[e.name]) { console.warn('missing sound', e.name); continue; }
    const s = e.rate ? at(e.name, e.rate) : bank[e.name];
    const i0 = Math.round(e.t * AR) * 2;
    const g = e.vol * gain * (AMBIENT[e.name] ?? 1);
    // (e.end / e.fade: cut off by a silence - H.sfxCut - a cosine fade from end, nothing after it)
    const n = e.end !== undefined ? Math.min(s.length, Math.max(0, Math.round((e.end + (e.fade || 0) - e.t) * AR)) * 2) : s.length;
    const c0 = e.end !== undefined ? Math.round((e.end - e.t) * AR) * 2 : n, cn = Math.max(2, Math.round((e.fade || 0) * AR) * 2);
    for (let i = 0; i < n && i0 + i < mix.length; i++) {
      if (i0 + i < 0) continue;
      const k = i < c0 ? 1 : 0.5 + 0.5 * Math.cos(Math.PI * Math.min(1, (i - c0) / cn));
      mix[i0 + i] += s[i] * g * k;
    }
  }
  for (const fx of o.musicFx || []) if (fx.kind === 'under') under(mix, fx);
  // a range that starts mid-sound: 12 ms fade-in so the first sample does not click
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
  // scale down only if the sum clips; no tanh limiter (that rounds off transients)
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

// ---------------------------------------------------------------- video
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
    const url = await page.evaluate((t) => window.MV.exportFrame(t, 'image/jpeg', 0.95), f / FPS);
    const buf = Buffer.from(url.slice(url.indexOf(',') + 1), 'base64');
    if (ff) { if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r)); }
    else fs.writeFileSync(path.join(opt.frames, String(f).padStart(5, '0') + '.jpg'), buf);
    if ((f - f0) % 120 === 0) {
      const done = f - f0 + 1, rate = done / ((Date.now() - t0) / 1000);
      console.log(`[w${id}] ${done}/${f1 - f0} frames  ${rate.toFixed(1)} fps  eta ${((f1 - f) / rate / 60).toFixed(1)} min`);
    }
  }
  if (ff) { ff.stdin.end(); await new Promise((r) => ff.on('close', r)); }
  await browser.close();
  return seg;
}

(async () => {
  const { browser, page } = await openPage();
  const info = await page.evaluate(() => ({ music: window.MV.MUSIC, end: window.MV.T.end, cut: window.MV.T.cut, sfx: window.MV.TL.sfx, musicFx: window.MV.TL.musicFx || [] }));
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
  mixAudio(info.sfx, wav, { music: info.music, dur: Math.max(info.end, t1), limit: LIMIT, fadeIn: t0, musicFx: info.musicFx });
  if (opt['audio-only']) return;
  console.log(`rendering ${F1 - F0} frames (${t0}s-${t1}s) at ${W}x${H}@${FPS}, ${WORKERS} workers, ${opt.gpu ? 'GPU' : 'SwiftShader'}${CUT ? ', cut=' + CUT : ''}`);
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
})();
