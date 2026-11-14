# tools/ · 原工程脚本（8 个）

这些是原工程 `bad-time-mv` 实际用过的分析、打包、检查、导出脚本，`PROMPT.md` 里提到的工具都在这里。拷过来时做了两件事：

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

- `analyze_music.py` → `src/analysis.js`（`asset/music/music.mp3`）
- `import_assets.py <c2-sans-fight 路径>` → `src/assets.js`
- `make_font.py` → `src/glyphs.js`

## 本项目要注意的

- `import_assets.py` 读的是 c2-sans-fight 原工程（`.caproj` + Animations/ + Textures/ + Files/），先 `git clone --depth 1 https://github.com/Jcw87/c2-sans-fight ../c2-sans-fight`（默认路径已改成 `../c2-sans-fight`）。不想 clone 的话，`asset/ui-kit-c2-sans-fight/` 里已经是解包好的同一套图和音效，锚点在 `meta.json`。
- `make_font.py` 里写死了 Linux 的 Unifont 路径（`/usr/share/fonts/opentype/unifont/unifont.otf`）。Windows 上改成 Unifont 的实际路径，或者改用 `C:/Windows/Fonts/simsun.ttc`（另外四个项目都用它）。
- 原工程预览用的是 `python -m http.server`，没有 `serve.cjs`；直接双击 `index.html` 也能播。
- `check.cjs` 要求页面提供 `MV.checkHits` 和 `MV.checkPov`（第一人称段）。

## 脚本一览

| 脚本 | 作用（取自脚本自己的说明） |
| --- | --- |
| `analyze_music.py` | Analyse asset/music/music.mp3 and write src/analysis.js for the MV engine. |
| `check.cjs` | Validate choreography: node tools/check.cjs [t0] [t1] [--cut=tiktok] |
| `frames.cjs` | Render selected frames to images for review. Usage: node tools/frames.cjs <outDir> <t1> <t2> ... [--w=960 --h=540 --cut=tiktok] |
| `import_assets.py` | Pack sprites, fonts and sound effects from the c2-sans-fight project (https://github.com/Jcw87/c2-sans-fight) into src/assets.js as data URIs, with the hotspots / image points read from its .caproj so parts attach exactly as in the original. |
| `make_font.py` | Bake GNU Unifont glyphs (8x16 ASCII, 16x16 CJK) into src/glyphs.js as bit rows. |
| `render.cjs` | Offline export: renders every frame in (headless) Chromium, mixes the sound effects over music.mp3, and encodes an MP4 — or just writes a frame sequence. |
| `sheet.py` | Contact sheet: tile the PNG frames of a folder into one picture (python tools/sheet.py <dir> <out.png> [cols] [scale]). |
| `shot.cjs` | Usage: node tools/shot.cjs <url-or-file> <out.png> [width] [height] [evalJS] |
