# UT-fight-prompt · 六部 UNDERTALE 像素 MV 复刻包

仓库：<https://github.com/guiguisocute/UT-fight-prompt>

这里是给其他 agent 从零复刻六部已完成 MV 的“开工包”。每个子目录是一个独立项目，包含三样东西：

- `PROMPT.md`：资源获取、框架要求、工作方式、超详细分镜
- `asset/`：原始素材
- `tools/`：原工程的分析、打包、检查、导出脚本，路径已改成本仓库布局

**不含**原工程的源代码（`index.html`、`src/`）、生成文件（analysis.js / assets.js / glyphs.js）和成片，要复刻的正是这些。

| 目录 | 片名 | 音乐 | 速度 / 网格 | 片长 | 难点 |
| --- | --- | --- | --- | --- | --- |
| [bad-time-mv](bad-time-mv/PROMPT.md) | BAD TIME（Sans · 屠杀线） | MEGALOVANIA | 120 BPM，原点 0.04 s，78 小节 | 160 s | 框架的起点；HUD 字母按 riff 发射、VHS 倒带、第一人称体素、可选 TikTok 竖屏版 |
| [mtt-mv](mtt-mv/PROMPT.md) | DEATH BY GLAMOUR（镁塔顿 EX · 完美线） | Death by Glamour | 148 BPM，原点 0.006 s，83 小节 | 178.6 s | 电视台图层与收视率、五家音游致敬（osu! / CHUNITHM / Beat Saber / Muse Dash / 太鼓）、终章“先定路线再放子弹”、可选全片竖屏版 |
| [asgore-mv](asgore-mv/PROMPT.md) | ASGORE 音乐剧（中立线国王战） | Bergentrückung + ASGORE | 113.01 / 114.85 BPM，两首拼接 | 约 250 s | 多平面 HD-2D 相机、六魂六种 2D 机制、体素窗口（FEZ、第一人称格挡）、打击的语法 |
| [mtt-neo-mv](mtt-neo-mv/PROMPT.md) | POWER OF NEO（不止一回合 · 空战） | Power of NEO 未完成加长版 | 145 BPM，原点 0.029 s，98 小节（硬切） | 约 207 s | WebGL 2 光线步进科技海、体素人偶与变形、空战镜头规矩、座舱 HUD |
| [Undyne-mv](Undyne-mv/PROMPT.md) | 不灭的安黛因（Battle Against a True Hero） | BTERTD + BaaTH + BTERTD | 150 BPM，原点 0.006 s，有 FL 工程当乐谱 | 约 320 s | HD-2D 冷开场、黑白正比立绘、风对心的真实位移、Windows 桌面 meta、3D 海战 |
| [mft-mv](mft-mv/PROMPT.md) | 蜘蛛之舞 · PARLOR PANIC!（Muffet × 皇家守卫） | 卓别林唱片 + Spider Dance | 115 BPM，原点 0.0845 s，第 48 小节前插 4.4 s 静默 | 约 206 s | 1930 年代默片冷开场、茶杯头式喜剧、多角色 rig、3D 蛛网潜行、弹幕评论区 |

## 怎么用

1. 一个 agent 只做**一个**项目。只拉那一个目录（以 Undyne-mv 为例）：
   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/guiguisocute/UT-fight-prompt.git
   cd UT-fight-prompt
   git sparse-checkout set Undyne-mv
   ```
   然后把 `Undyne-mv/` 下的 `asset/`、`tools/`、`PROMPT.md` 复制到新的工作仓库根目录，让 agent 先完整读 `PROMPT.md`。也可以直接把 `https://github.com/guiguisocute/UT-fight-prompt/tree/main/<目录>` 发给 agent，PROMPT 第零部分写了它该怎么取文件。
2. `PROMPT.md` 结构统一：第零部分资源从哪里拿 → 第一部分项目说明与素材 → 第二部分通用框架要求（六份相同）→ 第三部分工作方式 → 第四部分超详细分镜稿 + 迭代顺序。
3. **核心要求：逐步推进，切勿一次成片。** 每个 PROMPT 都写了阶段 0–5、自检清单和禁止事项：
   - 先读录像，再搭框架，用节拍器样片验证音乐网格，再把素材入库；
   - 之后每次只做 2–8 小节，出静帧、带声小样，跑碰撞检查；
   - **给用户确认后**再做下一段。
4. 建议的复刻顺序就是原作的制作顺序：bad-time → mtt → asgore → mtt-neo → Undyne → mft。框架从 bad-time 起步，后面每一部都在它上面加东西。

## 目录布局（每个项目相同）

| 路径 | 内容 |
| --- | --- |
| `asset/music/` | 音轨；`MV.MUSIC` 的 `src` 写成 `asset/music/…` |
| `asset/sprites/` | spriters-resource 精灵表，以及从游戏解出或从录像抽出的单帧 |
| `asset/sfx/` | UNDERTALE 原作音效全集（274 个，六个项目同一份） |
| `asset/ui-kit-c2-sans-fight/` | 原作战斗 UI（心、按钮、HP/KR、攻击靶、斩击、字体、菜单音效），从 bad-time-mv 的 `assets.js` 解包，带锚点 `meta.json` |
| `asset/record/` | 原作战斗录像，UI 位置、台词、弹幕形态的唯一权威参考（**视频不在 git 里**，见下） |
| `asset/ref/` | 风格与技术参考（截图、论文、着色器；参考视频不在 git 里） |
| `asset/notes/` | 原工程的设计文档、剧本旧稿、录像转写。**旧稿与 PROMPT 冲突时以 PROMPT 为准** |
| `tools/` | 原工程脚本 + `tools/README.md`（每个脚本的作用、生成链、依赖、哪些依赖原作者的机器或别的仓库） |

## 说明

- **git 仓库里没有 `.mp4` 视频**，原因是体积太大。唯一的例外是 mft 的音轨 `mft-mv/asset/music/spider dance.mp4`，它其实是音频。缺的视频有：
  - 各项目的原作录像（`asset/record/`）
  - Undyne 和 mft 的参考视频（`asset/ref/`，以及 `mft-mv/asset/royal-guards/`）

  每个 PROMPT 的第零部分列出了本项目缺哪些、多大、来源链接在哪，以及没有视频时怎么办。录像需要向维护者索取。
- 仓库约 250 MB。asgore 的 621 MB 无损录像从没拷进来，本地只有 100 MB 版，同样不入库。
- mft-mv 的剧本文档在原仓库的提交 `58e703e` 里被清空，`asset/notes/` 里是从前一个提交 `7c3260a` 找回来的。它的脚本注释也在同一次提交里被删了：只删了注释的 14 个脚本用的是 `7c3260a` 的带注释版本，详见 `mft-mv/tools/README.md`。
- 角色、素材与原曲版权归 Toby Fox / UNDERTALE 所有（mft 另含卓别林唱片与茶杯头参考素材）。这些都是非商业同人项目，公开传播前请注意相关权利。
