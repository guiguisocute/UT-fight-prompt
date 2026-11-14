# tools/ · 原工程脚本（21 个）

这些是原工程 `mtt-neo-mv` 实际用过的分析、打包、检查、导出脚本，`PROMPT.md` 里提到的工具都在这里。拷过来时做了两件事：

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

- `analyze_music.py` → `src/analysis.js`
- `slice_neo.py` → `work/parts/neo/`（切 NEO 精灵表）；`extract_ow.py`（🎥）→ `asset/sprites/drawn/`（已提供，不必重跑）
- `import_assets.py` → `src/assets.js`
- `make_font.py` → `src/glyphs.js`（新增中文后必须重跑）

## 本项目要注意的

- `import_assets.py` 原本从两个兄弟仓库读现成的切片：`../asgore-mv/src/assets.js`（UI、字体、伤害数字、音效）和 `../mtt-mv/src/assets.js`（方块形态、EX 的炸弹、十字爆炸、迷你镁塔顿、闪电、星星、●REC、EX 表情）。**本仓库两份都没有**：UI 换成 `asset/ui-kit-c2-sans-fight/`，方块形态和 EX 部件用 `asset/sprites/` 里的 `Mettaton.png`、`Mettaton EX.png` 自己切（照 `slice_neo.py` 的写法）。
- 镜头检查三件套：`cutaudit.cjs`（每个剪辑点前后的视线落点、轴线、屏幕方向、转角 + 前后帧）、`cutsheet.py`（排成对照表）、`camcheck.cjs`（镜头内的速度、转向跳变）。PROMPT 4.0 的镜头规矩就靠它们验收。
- `turntable.cjs` 用来检查 3D 体素人偶，从几个方向拍他。
- `make_font.py` 用 `C:/Windows/Fonts/simsun.ttc`，另外烘焙粗黑体（`MV_HEAVY_GLYPHS`，EVA 警报用）。

## 脚本一览

| 脚本 | 作用（取自脚本自己的说明） |
| --- | --- |
| `analyze_music.py` | Analyse asset/music/power_of_neo_unfinished_wip.mp3 (Toby Fox's unfinished extended "Power of NEO" mockup) and write src/analysis.js for the MV engine. |
| `camcheck.cjs` | Camera smoothness check for the 3D shots: node tools/camcheck.cjs <bar0> <bar1> Samples the camera (no impacts) at 240 Hz and reports the top speed, and where its speed or its look direction jumps (a cut shows as a jump - expected only where a shot begins). |
| `check.cjs` | Validate the choreography: node tools/check.cjs [t0] [t1] [--bars] * no attack ever touches the soul, except the scripted hits (events marked hurts) (blue passes only a still soul, orange only a moving one) * grazes: closest approaches of a beam's edge under 2 |
| `cutaudit.cjs` | Cut audit for the 3D shots (the grammar of the edit, measured): node tools/cutaudit.cjs <out> <bar0> <bar1> [--gpu] For every cut between the bars it renders the last frame of the shot before and the first of the shot after (out/cut_NN_a.png, _b.png) and write |
| `cutsheet.py` | Lay out tools/cutaudit.cjs's frames: one row per cut, the shot before / the shot after, with the soul (yellow) and him (pink) marked where they are in each picture, and the numbers. |
| `eval.cjs` | Evaluate a JS expression in the loaded player (render mode) and print the result. Usage: node tools/eval.cjs "MV.TL.enemy.at(MV.T.at(1))" |
| `explore_music.py` | First-pass exploration of power_of_neo_unfinished_wip.mp3: tempo grid, downbeat, per-bar energy / bands / chroma / drum patterns, novelty curve and bar self-similarity. Prints the table used to write the section map in tools/analyze_music.py (not needed at run |
| `explore_notes.py` | Second pass on the 145 BPM grid: per-section average drum profile per 16th (downbeat check), key estimate per section, the onsets of the intro / break / drop with their grid slots, and a per-bar note dump (bass per beat, lead per 8th). Used to write the sectio |
| `explore_spectro.py` | Third pass: tuning, the real bass note (range down to A0), and bar-gridded spectrogram / CQT images (work/spec_XX.png) to read the arrangement by eye. |
| `explore_tempo.py` | Exploration: is the tempo constant? Sliding-window tempo + global fit. |
| `extract_ow.py` 🎥 | Lift the overworld sprites of the prologue out of the reference recording (asset/record.mp4, 1440x900: the 640x480 game is drawn at 1.875x from x = 120; the game itself draws the 320x240 room at 2x, so one sprite pixel is 3.75 video px). Each sprite pixel is s |
| `frames.cjs` | Render selected frames to images for review. Usage: node tools/frames.cjs <outDir> <t1> <t2> ... [--w=960 --h=540] [--bars] [--gpu] (times as bar numbers, fractional bars allowed: 7.5625 = bar 7, 16th 9; --gpu renders on the graphics card) |
| `import_assets.py` 🎥 | Pack every sprite / font / sound the MV uses into src/assets.js (data URIs), so the player works from file:// with no loader. |
| `make_font.py` | Bake the dialogue font into src/glyphs.js as bit rows: 8x16 ASCII, 16x16 CJK. |
| `plot_music.py` | Piano-roll (CQT of the harmonic part) per 8 bars on the 145 BPM grid, to read melodies and bass lines by eye: work/roll_XX.png. Each column is one 16th (4 px), each row one semitone (5 px), C4..C7 on top, C1..C4 below; bar lines green, beats dark green, note n |
| `pw.cjs` | Resolve Playwright (a local or global install; otherwise stop with an install hint), the file:// page URL with query, and the Chromium flags for SwiftShader / the real GPU. |
| `render.cjs` | Offline export: renders every frame in (headless) Chromium, mixes the sound effects over the music (power_of_neo_unfinished_wip.mp3, which starts after the silent prologue, at T.pre), and encodes an MP4 - or just writes a frame sequence. Ported from ../mtt-mv/ |
| `serve.cjs` | Dependency-free local preview: node tools/serve.cjs [port] [directory] (or the PORT environment variable) |
| `sheet.py` | Contact sheet: tile the PNG frames of a folder into one picture (python tools/sheet.py <dir> <out.png> [cols] [scale]). |
| `slice_neo.py` | Cut the Mettaton NEO sprite sheet (asset/...Mettaton NEO.png) into parts. |
| `turntable.cjs` | Turntable of his 3D rig in one form, from several sides (checking the voxel model against the concept sheets in work/concept/). Usage: node tools/turntable.cjs <outDir> [--jet=1] [--bar=12.5] [--dist=420] [--gpu] |
