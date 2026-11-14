# tools/ · 原工程脚本（18 个）

这些是原工程 `mtt-mv` 实际用过的分析、打包、检查、导出脚本，`PROMPT.md` 里提到的工具都在这里。拷过来时做了两件事：

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

- `analyze_music.py` → `src/analysis.js`（`asset/music/music.mp3`，Death by Glamour）
- `slice_sheet.py` → `work/`（切 Mettaton EX 与方块形态两张表）
- `import_assets.py` → `src/assets.js`
- `make_font.py` → `src/glyphs.js`（宋体）；没有宋体时用 `fill_glyphs.py` 拿 GNU Unifont 补缺字
- `recover_buttons.py`（🎥）→ `src/btnglyphs.js`（照实机录屏还原的按钮字形）

## 本项目要注意的

- `import_assets.py` 的 UI 部分（心、按钮、HP、字体、菜单音效）原本从 `../bad-time-mv/src/assets.js` 读（第一个参数 `BT`）。**本仓库没有这个文件**，改成读 `asset/ui-kit-c2-sans-fight/`，或者先在 bad-time-mv 里跑出 `src/assets.js` 再把路径传进来。
- `check.cjs` 是全片校验：碰撞、**完美线**（`MV.checkPacifist`：HP 全程 20/20，子弹只打道具和他胸口的心形核心）、第一人称段、音效名是否都存在；`--cut=tiktok` 校验竖屏版。
- `build.cjs` 是原工程发布到 Cloudflare Pages 用的：只把运行需要的文件（`index.html`、音乐、`src/`、静态配置）复制到 `dist/site`，并写 `version.json`。复刻时可以不用。
- `render.cjs` 混音时音乐从 `T.pre`（14 s）开始、压低 4 dB 给音效留余量；`--limit` 改用前视峰值限制器。

## 脚本一览

| 脚本 | 作用（取自脚本自己的说明） |
| --- | --- |
| `analyze_music.py` | Analyse asset/music/music.mp3 (Death by Glamour) and write src/analysis.js for the MV engine. |
| `build.cjs` | Deploy only the runtime, never recordings, source reference assets, or tools. |
| `check.cjs` | Validate choreography: node tools/check.cjs [t0] [t1] [--cut=tiktok] * no white attack ever touches the soul (blue: only while still, orange: only while moving) * perfect route: FIGHT is never selected, HP stays 20 / 20 * first person: no obstacle reaches the  |
| `eval.cjs` | Evaluate a JS expression in the loaded player (render mode) and print the result. Usage: node tools/eval.cjs "MV.TL.enemy.at(MV.T.at(1))" |
| `explore_music.py` | First-pass exploration of music.mp3: tempo grid, per-bar energy / bands / chroma and a bar-level novelty curve. Prints a table used to write the section map in tools/analyze_music.py (not needed at runtime). |
| `explore_notes.py` | Per-bar note / rhythm dump on the corrected grid (148 BPM, bar 0 at 0.010 s): bass pitch per beat, lead pitch per 8th (harmonic part), drum hits per 16th. Used to write the section map and choreography notes (not needed at runtime). |
| `explore_phase.py` | Downbeat / 16th-phase probe: average kick / snare / hat per 16th slot over bar ranges, for each of the 16 possible rotations of the grid. Also prints the exact onset times of the first seconds and the length of the sfx we prepend. |
| `fill_glyphs.py` | Fill glyphs missing from src/glyphs.js from GNU Unifont, leaving every existing glyph as is. |
| `frames.cjs` | Render selected frames to images for review. Usage: node tools/frames.cjs <outDir> <t1> <t2> ... [--w=960 --h=540] [--bars] (times as bar numbers) [--cut=tiktok] (the vertical cut; default size 540x960) |
| `import_assets.py` | Pack every sprite / font / sound the MV uses into src/assets.js (data URIs), so the player works from file:// with no loader. |
| `make_font.py` | Bake the dialogue font into src/glyphs.js as bit rows: 8x16 ASCII, 16x16 CJK. |
| `pw.cjs` | Resolve Playwright (a local or global install; otherwise stop with an install hint), the file:// page URL with query, and the Chromium flags for SwiftShader / the real GPU. |
| `recover_buttons.py` 🎥 | Recover the Chinese command-button glyphs (战斗 行动 物品 仁慈) of the Chinese UNDERTALE build from the gameplay recording, so the buttons match the game. |
| `render.cjs` | Offline export: renders every frame in (headless) Chromium, mixes the sound effects over asset/music/music.mp3 (which starts after the silent prologue, at T.pre), and encodes an MP4 - or just writes a frame sequence. Ported from ../bad-time-mv/tools/render.cjs |
| `serve.cjs` | Dependency-free local preview: node tools/serve.cjs [port] [directory] |
| `sheet.py` | Contact sheet: tile the PNG frames of a folder into one picture (python tools/sheet.py <dir> <out.png> [cols] [scale]). |
| `shot.cjs` | Usage: node tools/shot.cjs <url-or-file> <out.png> [width] [height] [evalJS] |
| `slice_sheet.py` | Cut the Mettaton sprite sheets (asset/...Mettaton EX.png, asset/...Mettaton.png) into frames. |
