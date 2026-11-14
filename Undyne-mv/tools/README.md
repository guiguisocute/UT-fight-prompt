# tools/ · 原工程脚本（30 个）

这些是原工程 `Undyne-mv` 实际用过的分析、打包、检查、导出脚本，`PROMPT.md` 里提到的工具都在这里。拷过来时做了两件事：

1. **路径改成本仓库的布局**：音乐 `asset/music/`、精灵表 `asset/sprites/`（含 `ut/ her/ tiles/ drawn/` 子目录）、音效包 `asset/sfx/`、录像 `asset/record/`。原工程里这些文件在仓库根目录或 `asset/` 下面。
2. **`pw.cjs` 不再去找兄弟仓库的 Playwright**：找不到时报错并提示安装命令。

其余代码原样保留。它们是参考实现，也定义了接口契约：大部分 `.cjs` 工具会打开 `index.html?render=1…`，并假定页面暴露 `MV.ready`、`MV.exportFrame(t)`、`MV.checkHits(t0, t1)`、`MV.T`、`MV.TL`、`MV.MUSIC`、`TL.sfx`（见 PROMPT 第二部分 2.2–2.7）。页面不存在时，这些工具跑不起来。可以直接用，也可以照着重写，但**必须先读懂再用**，不要盲跑。

## 运行环境

- 在项目根目录运行，也就是 `index.html`、`src/`、`asset/`、`tools/` 所在的那一层，例如 `python tools/analyze_music.py`、`node tools/frames.cjs work/f 12.5 --gpu`。
- Python 3.10+：`pip install numpy scipy librosa pillow`；另需 `pip install pyflp`（读 FL Studio 工程）
- Node 18+：`npm i playwright`，然后 `npx playwright install chromium`
- ffmpeg 要在 PATH 上；用 N 卡 GPU 编码时还需要 `h264_nvenc`
- `work/`（中间产物）和 `dist/`（输出）由脚本自己创建，不要提交
- **视频不在 git 仓库里**：读 `asset/record/*.mp4` 的脚本（见下表 🎥）需要先把录像放回原位，见 PROMPT 第 0 节

## 生成链（生成文件永远不手改）

- `flp_notes.py` → `work/flp_notes.json`；`analyze_music.py`（mp3 + `.flp`）→ `src/analysis.js`（含 `score` / `lead` / `motif` / `chords`）
- `import_assets.py` → `src/assets.js`（读 `asset/sprites/{tiles,drawn,ut,her}`、`asset/desktop/`、音效包）
- `make_font.py` → `src/glyphs.js`
- `fit_undying.py rest|track|…`（🎥）→ `work/undying_*.json` → `src/und_data.js`（不灭形态人偶）
- `lift_overworld.py`（🎥）→ `make_tiles.py` → `asset/sprites/tiles/`（已提供）

## 本项目要注意的

- `import_assets.py` 的 UI 和原作音效原本从 `../asgore-mv/src/assets.js` 读。**本仓库没有这个文件**，改成读 `asset/ui-kit-c2-sans-fight/` 和 `asset/sfx/`。
- 这几样东西只能在原作者的机器上生成，结果已经放进 `asset/`，**不必重跑**：
  - `ut_sprites.py`：从本机安装的 UNDERTALE `data.win` 读原图，结果在 `asset/sprites/ut/`
  - `win_desktop.ps1` / `win_cursors.py`：从本机 Windows 11 取图标和鼠标指针，结果在 `asset/desktop/`
  - `her_frames.py`：第四幕她的动作帧，结果在 `asset/sprites/her/`
- `explore_*.py` 是读谱、对齐用的探查脚本，结论已经写进 `asset/music/MUSIC.md`。
- `check.cjs` 量的是红心和每一把能伤它的刀之间的最近距离（`MV.RD.dangers`）。

## 脚本一览

| 脚本 | 作用（取自脚本自己的说明） |
| --- | --- |
| `analyze_music.py` | Analyse 'asset/music/Toby Fox - Battle Against A True Hero.mp3' together with the FL Studio deconstruction of it and write src/analysis.js for the MV engine. |
| `check.cjs` | The soul and what is thrown at it: node tools/check.cjs [bar0] [bar1] Samples the battle at 240 Hz (the picture's own time) and measures, for the red soul, how near each blade that can cut it comes (MV.RD.dangers: round 4's spears, the rings', the floor's, the |
| `cropsheet.py` | Contact sheet of crops: the same region cut out of many frames, tiled with labels. |
| `eval.cjs` | Evaluate a JS expression in the loaded player (render mode) and print the result. Usage: node tools/eval.cjs "MV.TL.enemy.at(MV.T.at(1))" |
| `explore_align.py` | Check that the FLP transcription lines up with the mp3, and fit the grid. |
| `explore_ed.py` | Look at "But the Earth Refused to Die" before choreographing on it: tempo, beats, onsets, the loudness and the harmony over time - printed, and drawn into work/ed_look.png. |
| `explore_ed2.py` | BTERTD, closer: when the harmony changes (fine chroma novelty), the swells in the bands, and the pulse (autocorrelation of the band energy) - for cutting on it. |
| `explore_flp.py` | Dump the FL Studio project (channels, patterns, playlist) as text. |
| `explore_notes.py` | Read work/flp_notes.json as a score. |
| `explore_record.py` 🎥 | Where does Battle Against a True Hero start in the gameplay recording, and where does the in-game loop jump back to? |
| `explore_transpose.py` | Find the sounding transposition of every FLP channel against the mp3. |
| `explore_undying.py` 🎥 | How the Undying battle sprite moves in the recording (asset/record.mp4). |
| `fit_undying.py` 🎥 | Undyne the Undying's puppet, fitted on the game's own picture and on the recording. |
| `flp_notes.py` | Flatten the FL Studio deconstruction into an absolute note list. |
| `frames.cjs` | Render selected frames to images for review. Usage: node tools/frames.cjs <outDir> <t1> <t2> ... [--w=960 --h=540] [--bars] [--gpu] (times as bar numbers, fractional bars allowed: 7.5625 = bar 7, 16th 9; --gpu renders on the graphics card) |
| `her_frames.py` | Her frames for the load scene (README 第四幕: drawn by codex, the user 2026-10-19: 动画精灵帧为了表现力可以 让codex逐帧画), snapped to true pixel art on her own sprite's grid: area-averaged down to the art size, thresholded to the original's 1-bit white, stray pixels dropped, th |
| `import_assets.py` | Pack the pictures (and later the sounds) the MV uses into src/assets.js as data URIs, so the player works from file:// with no loader (the same scheme as ../mtt-neo-mv and ../asgore-mv). |
| `lift_overworld.py` 🎥 | Lift the original overworld (the bridge at the end of asset/record.mp4) at art-pixel resolution. |
| `make_font.py` | Bake the dialogue font into src/glyphs.js as bit rows: 8x16 ASCII, 16x16 CJK (from ../mtt-neo-mv/tools/make_font.py). Re-run after adding Chinese text anywhere in src/. |
| `make_tiles.py` | The original bridge room's textures, cut from the lifted overworld (tools/lift_overworld.py). |
| `pw.cjs` | Resolve Playwright (a local or global install; otherwise stop with an install hint), the file:// page URL with query, and the Chromium flags for SwiftShader / the real GPU. |
| `render.cjs` | Offline export: renders every frame in (headless) Chromium, mixes the sound effects over the soundtrack (MV.MUSIC: each file at its start time - "But the Earth Refused to Die" after the cold open, then Battle Against a True Hero), and encodes an MP4 - or just  |
| `serve.cjs` | Dependency-free local preview: node tools/serve.cjs [port] [directory] (or the PORT environment variable) |
| `sheet.py` | Contact sheet: tile the PNG frames of a folder into one picture (python tools/sheet.py <dir> <out.png> [cols] [scale]). |
| `slice_npc.py` | Cut the overworld sprite sheets (asset/... Non-Playable Characters - *.png) into frames. |
| `slice_sheet.py` | Cut the Spriters Resource sheets in asset/ into cells (from ../mtt-neo-mv/tools/slice_neo.py). |
| `sprdump.cjs` | Dump pictures the page makes (packed sprites and the ones drawn in src/sprites.js) to PNGs for review, enlarged on a dark ground. Usage: node tools/sprdump.cjs <outDir> <key> [key ...] [--scale=8]   e.g. ow/echo kid/17 |
| `ut_sprites.py` | The original game's own sprites, read out of the installed UNDERTALE's data.win (GameMaker 1.4): each sprite by its name in the game, every frame laid out on its own canvas the size the game draws it - no sheet, no recording, no watermark. (README 第四幕: the GAM |
| `win_cursors.py` | Windows' own mouse pointers (README 场景 · 桌面: "Windows 的白色箭头") off this machine, every size the .cur / .ani holds, so a zoomed shot can draw the pointer from the frame the system itself would use at that scale (32 px at 100 %, 64 at 200 % ...). |
| `win_desktop.ps1` | Lift the desktop's pieces off this Windows 11 machine (README 场景 · 桌面; user 2026-10-19: icons are Windows' own defaults): every icon exactly as the shell draws it, at each size the desktop, the taskbar and the title bar ask for, plus the metrics the desktop re |
