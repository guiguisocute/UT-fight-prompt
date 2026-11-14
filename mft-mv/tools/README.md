# tools/ · 原工程脚本（40 个）

这些是原工程 `mft-mv` 实际用过的分析、打包、检查、导出脚本，`PROMPT.md` 里提到的工具都在这里。拷过来时做了两件事：

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

- `make_analysis.py`（`spider dance.mp4`，网格按 MUSIC2.md 已验证的 115 BPM / 0.0845 s）→ `src/analysis.js`；`spider_grid.py` / `spider_tempo_check.py` / `spider_zoom.py` / `spider_accents.py` / `spider_music.py` 是验证网格的五种独立方法
- `chaplin_analyze.py` → 卓别林唱片的拍点；`make_rundown.py` → `asset/music/chaplin_cold.mp3`（“发条松了”的尾巴，已提供）
- `slice_sheet.py` / `cut_parts.py` / `cut_sheet.py` → 切精灵表；`rec_game.py`（🎥）→ 从录像还原游戏帧（.npy）；`fit_muffet.py` / `zfit_muffet.py` / `rigfit.py` → 拟合部件；`make_muf_rig.py` / `make_rig.py` → 动作 rig；`make_props.py` → `src/props_img.js`
- `import_assets.py` + `import_sfx.py` → `src/assets.js`；`make_font.py` → `src/glyphs.js`（另含弹幕评论区用的 6×12 / 12×12 小字）

## 本项目要注意的

- 原仓库在提交 `58e703e` 里删光了脚本注释。下面这 14 个只删了注释、代码没变，所以用的是删之前 `7c3260a` 的带注释版本：`beatcheck.cjs chaplin_analyze.py eval.cjs frames.cjs import_assets.py make_analysis.py make_muf_rig.py make_props.py muf_motion.py pw.cjs rec_game.py rigfit.py serve.cjs slice_sheet.py`。其余用最终版本（有的没有注释）。
- `import_assets.py` 的 UI 和部分音效原本从 `../Undyne-mv/src/assets.js` 读。**本仓库没有这个文件**，改成读 `asset/ui-kit-c2-sans-fight/`。`import_sfx.py` 已改成读 `asset/sfx/`。
- **`beatcheck.cjs` 是本片最重要的检查**：列出一段小节里每个冲击、音效、镜头切换和急停、杯子摆动、紫心换线落在哪个 16 分，以及那里实测有没有音。每改一次就跑一次：`node tools/beatcheck.cjs <起> <止>`。
- `compare_muffet.py` / `compare_rig.py` / `scan_eyes.py` / `record_bubbles.py` 都要读录像（🎥）。
- `cover.cjs` 用来出封面静帧：去掉框和 HUD，加多子帧运动模糊。

## 脚本一览

| 脚本 | 作用（取自脚本自己的说明） |
| --- | --- |
| `analyze_spider.py` | First-pass analysis of spider dance.mp4 (librosa): tempo, onsets, bands, sections -> analysis.json, music_grid.csv and work/spider-analysis.png (superseded by spider_grid / spider_music / make_analysis). |
| `beatcheck.cjs` | The beat check: everything in a span of bars that should land on the music - the camera's hits (impacts), the sounds, the camera's cuts and sudden stops / starts, the box's swings, the soul's hops between strings - each placed on its 16th, with how far off the |
| `calib_grid.py` | Where exactly a capture's game pixels are: sample a video frame on a grid (x0 + (gx + 0.5) s, y0 + (gy + 0.5) s) for small changes of x0, y0, s, and keep the grid on which a fitted rig (rigfit spec) agrees best with what is sampled - a capture scaled with smoo |
| `chaplin_analyze.py` | The cold open's music (Charlie Chaplin, "At the Picture", Modern Times 1936): tempo and beats, the loudness, where the music changes (sections from a self-similarity novelty curve), the accents - to cut an excerpt on its phrases and hang the gags on its hits.  |
| `compare_muffet.py` | Hold the rig against the recording: for each game frame k, the recording (work/muf/g/game.npy, the 640 x 480 game screen) beside our render of ?lab=muffet at lab t = k / 30 (tools/frames.cjs, 960 x 540, the game screen at +160, +30), and the difference (white  |
| `compare_rig.py` | Hold a rig against its recording (tools/compare_muffet.py, generalised): for each game frame k, the recording's frame (a .npy of game frames, tools/rec_game.py) beside our render of a lab at lab t = k / 30 (tools/frames.cjs, 960 x 540, the game screen at +160, |
| `contact_sheet.py` | Contact sheet of a video: one frame every N seconds, tiled with timestamps, plus times.json (used to read asset/record/record.mp4 and the reference videos). |
| `cover.cjs` | A still for the cover: one moment of the film rendered without the battle box and HUD, with motion blur from many subframes (scene time t0→t1, camera eased from cam0 to cam1 across the shutter). node tools/cover.cjs <out.png> [--w=1920 --h=1080] [--json=work/c |
| `cut_parts.py` | Cut Muffet's parts (the top of the Spriters Resource sheet: head, body, arms, legs, eyes) by XY cuts: split into bands at rows that are all sheet colour, then into cells at columns that are all sheet colour. The cell colour becomes transparent. -> work/muf/par |
| `cut_sheet.py` | Cut a Spriters Resource sheet's parts (tools/cut_parts.py, generalised): a region of the sheet is split into bands at rows with no cell colour, then into cells at columns that are all sheet colour; a cell must hold cell colour (labels are left out). The cell c |
| `eval.cjs` | Evaluate a JS expression in the loaded player (render mode) and print the result. Usage: node tools/eval.cjs "MV.TL.enemy.at(MV.T.at(1))" |
| `fit_muffet.py` 🎥 | Fit Muffet's parts (work/muf/parts, the sheet's sprites at 2x) to the recording, frame by frame. |
| `frames.cjs` | Render selected frames to images for review. Usage: node tools/frames.cjs <outDir> <t1> <t2> ... [--w=960 --h=540] [--bars] [--gpu] (times as bar numbers, fractional bars allowed: 7.5625 = bar 7, 16th 9; --gpu renders on the graphics card) |
| `import_assets.py` | Pack the pictures and sounds into src/assets.js (window.MV_ASSETS = {img, meta, sfx, size}) so the player works from file:// with no loader (the same scheme as ../Undyne-mv and ../asgore-mv). |
| `import_sfx.py` | Pack the game's own sound effects (the Undertale pack in ../mtt-mv/asset) into src/assets.js, next to what tools/import_assets.py put there: each chosen file trimmed to the part that is used, mono 44.1 kHz, mp3 - keyed by its name in the game (snd_b, mus_rimsh |
| `inspect_record.py` 🎥 | Probe asset/record/record.mp4: duration, frame times and a frame dump for reading the original fight. |
| `make_analysis.py` | spider dance.mp4 -> src/analysis.js (window.MV_ANALYSIS), the same fields as the earlier MVs' (bpm, offset, sixteenth, barLength, duration, sections, pattern, slots.*, env.*). The grid is the one verified in MUSIC2.md: 115 BPM, bar 0 at 0.0845 s, 51 bars. |
| `make_font.py` | Bake the dialogue font into src/glyphs.js as bit rows: 8x16 ASCII, 16x16 CJK, plus the small chat set at 6x12 / 12x12 (from ../mtt-neo-mv/tools/make_font.py). Re-run after adding Chinese text anywhere in src/. |
| `make_muf_rig.py` 🎥 | Muffet's rig for the film, as the game moves her: the tracked idle (work/muf/track3.json) reduced to the game's own numbers. |
| `make_props.py` | The film's small pictures (bullets, the tiny spiders, the sign, the pet), cut from the sheets by tools/cut_sheet.py, packed as data URLs under readable names -> src/props_img.js (window.MV_PROPS). |
| `make_rig.py` | A sprite rig for the film from a tracked idle (tools/rigfit.py track), reduced to the game's own numbers (tools/make_muf_rig.py, generalised: any parts, any scale, several actors on their own clocks). |
| `make_rundown.py` | The cold open's score with its ending: Chaplin's "At the Picture" as it is up to the throw, then the record running down - a gramophone whose spring has given out: speed and pitch sinking together to a stop, the sound dulling and dropping as it goes, the needl |
| `muf_motion.py` | What moves in Muffet's idle: the tracked rig (work/muf/track.json, tools/zfit_muffet.py track) per part over the frames -> a table (x, y, deg per frame) and work/muf/motion_plot.png (each part's x, y and angle against the frame number, offset from its mean). |
| `pw.cjs` | Resolve Playwright (a local or global install; otherwise stop with an install hint), the file:// page URL with query, and the Chromium flags for SwiftShader / the real GPU. |
| `rec_game.py` 🎥 | The game's own frames out of a recording. asset/record.mp4 is the 640 x 480 screen scaled 2.25x (nearest neighbour) into 1920 x 1080 at x 240: sampling each game pixel's centre gives the game's frame back. Other captures sit differently and are smoothed: --gri |
| `record_bubbles.py` 🎥 | Capture every finished speech bubble and battle text box in asset/record.mp4. |
| `render.cjs` | Offline export: renders every frame in (headless) Chromium, mixes the sound effects over MV.MUSIC (chaplin_cold.mp3, then spider dance.mp4 in two pieces around the 4.4 s gap), and encodes an MP4 - or writes a frame sequence. |
| `rigfit.py` | Fit a sprite rig to frames by rendering it and comparing (tools/zfit_muffet.py, generalised: any parts folder, any scale, frames from a .npy of game frames or from a picture's white pixels). |
| `scan_eyes.py` 🎥 | Her five eyes through the whole recording: which frame each shows (0 open .. 3 shut, 4 the round one), every game frame - to learn when and how she blinks. The face is cut out of asset/record.mp4 by ffmpeg (the head's region only), sampled at game-pixel centre |
| `serve.cjs` | Dependency-free local preview: node tools/serve.cjs [port] [directory] (or the PORT environment variable) |
| `sfx_survey.py` | A look at the game's sound effects pack before choosing from it: for each file its length, loudness, where its energy sits (attack, sustain, tail) and which way its pitch goes (spectral centroid early vs late - a slide whistle up or down, a falling bomb) - pri |
| `slice_sheet.py` | Cut a Spriters Resource sheet into its cells: every connected patch of the cell colour is one cell; the cell colour becomes transparent. Writes work/slices/<name>/NN.png, cells.json and a numbered contact sheet (work/slices/<name>_index.png) to map cells to ke |
| `spider_accents.py` | Per-section 16th-slot accent profiles + stop-time detection + click-track check file. |
| `spider_grid.py` | Tempo / phase / downbeat fit for asset/music/spider dance.mp4 (independent of analyze_spider.py). |
| `spider_music.py` | Full music analysis of asset/music/spider dance.mp4 on the verified 115 BPM grid. |
| `spider_tempo_check.py` | Independent cross-checks of the tempo of spider dance.mp4. |
| `spider_zoom.py` | Origin refinement by slot-folded envelopes + zoomed 2-bar views (harmonic CQT / percussive STFT). |
| `strip.py` | A filmstrip of rendered frames (tools/frames.cjs --bars): each frame cut to a region, labelled bar·16th (SCRIPT.md's notation), side by side; optional guide lines across all of them (world y) so a bob reads at a glance. |
| `strip3.py` | A filmstrip of ?lab=beat with all three on stage: each tile labelled with its bar and beat and who is at the bottom of their bob (measured: the crown's lowest row in the frame - Muffet's head at world x 478-488, the guards' at 222-238 and 716-732). |
| `zfit_muffet.py` | Fit Muffet's whole rig to one recording frame by rendering it and comparing (tools/fit_muffet.py fits parts one at a time; this one knows the draw order, so a part hidden behind another is not blamed for what it cannot show). |
