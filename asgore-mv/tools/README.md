# tools/ · 原工程脚本（23 个）

这些是原工程 `asgore-mv` 实际用过的分析、打包、检查、导出脚本，`PROMPT.md` 里提到的工具都在这里。拷过来时做了两件事：

1. **路径改成本仓库的布局**：音乐 `asset/music/`、精灵表 `asset/sprites/`（含 `ut/ her/ tiles/ drawn/` 子目录）、音效包 `asset/sfx/`、录像 `asset/record/`。原工程里这些文件在仓库根目录或 `asset/` 下面。
2. **`pw.cjs` 不再去找兄弟仓库的 Playwright**：找不到时报错并提示安装命令。

其余代码原样保留。它们是参考实现，也定义了接口契约：大部分 `.cjs` 工具会打开 `index.html?render=1…`，并假定页面暴露 `MV.ready`、`MV.exportFrame(t)`、`MV.checkHits(t0, t1)`、`MV.T`、`MV.TL`、`MV.MUSIC`、`TL.sfx`（见 PROMPT 第二部分 2.2–2.7）。页面不存在时，这些工具跑不起来。可以直接用，也可以照着重写，但**必须先读懂再用**，不要盲跑。

## 运行环境

- 在项目根目录运行，也就是 `index.html`、`src/`、`asset/`、`tools/` 所在的那一层，例如 `python tools/analyze_music.py`、`node tools/frames.cjs work/f 12.5 --gpu`。
- Python 3.10+：`pip install numpy scipy librosa pillow`
- Node 18+：`npm i playwright`，然后 `npx playwright install chromium`
- ffmpeg 要在 PATH 上；用 N 卡 GPU 编码时还需要 `h264_nvenc`
- `work/`（中间产物）和 `dist/`（输出）由脚本自己创建，不要提交
- **视频不在 git 仓库里**：读 `asset/record/*.mp4` 的脚本（见下表 🎥）需要先把录像放回原位，见 PROMPT 第 0 节

## 生成链（生成文件永远不手改）

- `analyze_music.py` → `src/analysis.js`（`MV_ANALYSIS.m1 / m2`，两首）
- `import_assets.py` → `src/assets.js`；`import_story.py` → `src/assets_story.js`（Asriel 表上的五幅故事画）
- `make_font.py` → `src/glyphs.js`
- `make_corridor.py`（🎥 读录像）→ `src/corridor.js`（结界房间的光波）
- `slice_sheet.py` → `work/index/`、`work/parts/`（切精灵表）；`fit_puppet.py`（🎥）→ 部件偏移，写进 `src/boss.js`

## 本项目要注意的

- `import_assets.py` 的 UI 部分（按钮、心、HP、字体、菜单音效）原本从 `../bad-time-mv/src/assets.js` 读（第一个参数 `BT`）。**本仓库没有这个文件**：要么先在 bad-time-mv 里跑出它的 `src/assets.js` 再把路径传进来，要么改成直接读 `asset/ui-kit-c2-sans-fight/`。
- `make_font.py` 用 `C:/Windows/Fonts/simsun.ttc`。
- `frames.cjs` / `sheet.cjs` / `check.cjs` 的时间参数可以写 `b<bar>`（music2 网格）或 `c<bar>`（music1 网格）。
- 原工程用 `serve.py` 做无缓存预览（`python tools/serve.py 4176`）。

## 脚本一览

| 脚本 | 作用（取自脚本自己的说明） |
| --- | --- |
| `analyze_music.py` | Analyse asset/music/music1.mp3 (Bergentrückung) and asset/music/music2.mp3 (ASGORE) and write src/analysis.js for the MV engine (window.MV_ANALYSIS = {m1: {...}, m2: {...}}, so the player works from file://). |
| `artsheet.cjs` | Review sheet of the performance sprites (src/art.js: MV.ART.list), each at 2x with its name, plus the sheet's eye-flash frames (eye0..16) for picking. Usage: node tools/artsheet.cjs [out.png]   (default work/art_sheet.png) |
| `check.cjs` | Validate the battle choreography: no bullet touches the soul unless meant. Usage: node tools/check.cjs [t0 / b<bar>] [t1 / b<bar>] |
| `eval.cjs` | Evaluate a JS expression in the loaded player (render mode) and print the result. Usage: node tools/eval.cjs "MV.TL.enemy.at(MV.T.at(1))" |
| `explore_gaps.py` | Find the near-silent gaps / big re-entries of a track and print the strong onsets around them in beat units of a reference grid (meter-change hunting). |
| `explore_music.py` | First-pass exploration of a track: tempo grid (brute force), tempo stability, per-bar energy / bands / chroma / novelty, per-16th drum patterns, repeats. Prints a table used to write the section map in tools/analyze_music.py (not needed at runtime). |
| `explore_notes.py` | Per-bar note dump on a fixed grid: bass per beat, top voice per 8th (harmonic part, CQT), drum hits per 16th (attack-aligned flux). |
| `explore_phase.py` | Phase / downbeat probe on a fixed BPM: 16th phase from attack-aligned (non-centred) flux and from backtracked onsets; downbeat from harmonic change (chroma novelty per beat position) and band patterns averaged over bar ranges. |
| `explore_tempo.py` | Precise tempo / phase probe: scores candidate BPMs on the onset envelope and fits a line through backtracked onsets snapped to the grid (drift check). |
| `fit_puppet.py` | Fit the battle-Asgore part offsets against a frame of the reference recording: draws the composite (parts at PARTS offsets, sprite px) in colour over the frame (scaled to sprite px) -> work/fit.png. Offsets found here go to src/boss.js. |
| `frames.cjs` | Render selected frames to PNG for review. Usage: node tools/frames.cjs <outDir> <t1> <t2> ... [--w=960 --h=540] [--gpu] times: seconds, or b<bar> (music2 grid, e.g. b24.5) / c<bar> (music1 grid) |
| `import_assets.py` 🎥 | Pack every sprite / font / sound the MV uses into src/assets.js (data URIs), so the player works from file:// with no loader. |
| `import_story.py` | Pack the game's own sepia story panels into src/assets_story.js (data URIs merged into MV_ASSETS, so the player still works from file://). Kept apart from src/assets.js so that file need not be regenerated. |
| `make_corridor.py` 🎥 | Bake the barrier room's light from the recording into src/corridor.js. |
| `make_font.py` | Bake the dialogue font into src/glyphs.js as bit rows: 8x16 ASCII, 16x16 CJK. |
| `plot_music.py` | Draw CQT piano-roll images on the beat grid so the arrangement can be read by eye: one overview of the whole track plus one image per N bars. |
| `pw.cjs` | Resolve Playwright (a local or global install; otherwise stop with an install hint), the file:// page URL with query, and the Chromium flags for SwiftShader / the real GPU. |
| `render.cjs` | Offline export: renders every frame in (headless) Chromium, mixes the sound effects over asset/music/music1.mp3 (T.m1, act two) and asset/music/music2.mp3 (T.m2, act four), and encodes an MP4 — or just writes a frame sequence. Ported from ../mtt-mv/tools/rende |
| `serve.py` | Serve the player for the live preview without browser caching (every reload gets the current sources): .venv/Scripts/python tools/serve.py [port] |
| `sheet.cjs` | Contact sheet: render the given times (seconds, b<bar> on music2's grid, c<bar> on music1's) small, tiled with their labels, into one PNG. Usage: node tools/sheet.cjs <out.png> <t>... [--cols=4] [--w=480] [--gpu] |
| `sheet.py` | Contact sheet: tile the PNG frames of a folder into one picture (python tools/sheet.py <dir> <out.png> [cols] [scale]). |
| `slice_sheet.py` | Cut the spriters-resource sheets in asset/ into frames. |
| `sprites.cjs` | Dump named sprites into one review grid (any MV.img name, sheet key, frame 'Obj/Anim/i', or 'art:<name>' from src/art.js), each scaled with its name and size under it. Usage: node tools/sprites.cjs <out.png> <name>... [--sc=2] |
