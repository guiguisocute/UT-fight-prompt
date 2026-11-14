# CLAUDE.md

Undertale「不灭的安黛因」MV。剧本只看 **SCRIPT.md**；不要再写设计长文 / 巨型注释。

## 命令
- 预览：`node tools/serve.cjs` → http://localhost:4173（`?lab=<name>` 打开 src/tl_lab.js 的单段样片）
- 检查：`node tools/check.cjs [bar0] [bar1]`（默认 12–60，碰撞与密度）
- 抽帧：`node tools/frames.cjs <outDir> <t...> --gpu --w=1920 --h=1080`
- 导出：`node tools/render.cjs --t0=<s> --t1=<s> --gpu --vcodec=h264_nvenc --out=dist/x.mp4`
- 音乐分析 / 素材打包（生成文件勿手改）：tools/analyze_music.py → src/analysis.js；tools/import_assets.py → src/assets.js；tools/make_font.py → src/glyphs.js；tools/fit_undying.py → src/und_data.js（读 work/undying_*.json）

## 时间（src/util.js）
- 150 BPM，1 小节 = 1.6 s，16 分 = 0.1 s
- 冷开场 0–45.5 s（T.cold）→ "But the Earth Refused to Die" 45.5–77.7 s → BaaTH 从 T.pre = 77.7 s 起
- 小节 → 视频时间：`T.at(bar, beat, s16)` ≈ 77.706 + 1.6·bar（bar 24 ≈ 116.1 s，bar 72 ≈ 192.9 s，bar 96 曲终）
- 一切都是 t 的纯函数（src/engine.js 的 Track），任意帧可单独渲染

## src 地图
- 基础：util.js（时间/随机）、engine.js（Track）、timeline.js（TL.* 轨道）、synth.js（音效）、main.js（播放/导出接口）
- 画面：hd2d.js + waterfall.js（3D 瀑布木桥）、draw.js（屏幕层）、battle.js（战斗框/HUD/菜单）、stage2d.js / bw.js / refusal_bw.js（黑白段）、undyne.js + und_data.js（安黛因）、desktop.js（电脑桌面）、scene.js（合成）
- 战斗效果：rounds.js（原作弹幕/盾/矛）、storm.js（雨）、gale.js + windfx.js（风）、narrate.js（风雨里的旁白）、abyss.js（水面/深渊）、homage.js、load.js（读档段）
- 时间轴：tl_cold.js / tl_cold2.js（冷开场）、tl_refusal_bw.js（0–12）、tl_battle1.js（12–27）、tl_battle2.js（28–43）、tl_battle3.js（44–60）、tl_load.js（60–71）、tl_lab.js（样片）

## 硬规则（以代码为准）
- 玩家 HP 56（TL.bat，src/battle.js），12–60 一路被打到 0；12–59 玩家不攻击
- 原作 UI 本地化风格，960×540 世界坐标

## 现状 / 方向
- 保留的样板：bar 24–27 的风（tl_battle1 + windfx + storm）、bar 50 的水面交互（tl_battle3 + abyss）、bar 60–71 的读档桌面（tl_load + load + desktop）
- 其余 12–59 战斗待大范围重做，重点：心（灵魂）在狂风里硬扛、站稳的感觉
- bar 72 之后为空，完全重做：参考 ../mtt-neo-mv 的 2D→3D 切换，战舰世界式地形 + 新 HUD；装填条（参考 ../bad-time-mv 战斗条）作攻击时机，同时格挡 3D 世界来的箭头
