# c2-sans-fight 战斗 UI 素材包（解包版）

来源：<https://github.com/Jcw87/c2-sans-fight>（UNDERTALE 原作素材，按原工程 `.caproj` 的锚点拼装）。
这里是从 bad-time-mv 的 `src/assets.js`（data URI）原样解包出来的文件，五个 MV 的战斗 UI 都基于这一套。

| 路径 | 内容 |
| --- | --- |
| `img/PlayerHeart/Default/0.png`、`Split/0.png` | 红心 / 裂开的心 |
| `img/HeartShard/Default/0-3.png` | 心碎片（4 帧） |
| `img/UIFight|UIAct|UIItem|UIMercy/{Default,Highlight}/0.png` | 四个按钮（常态 / 高亮） |
| `img/HP/Default/0.png`、`img/KR/Default/0.png` | HP、KR 标签 |
| `img/Target/Default/0.png`、`TargetChoice/Default/0-1.png` | 攻击靶、靶上光标（白 / 黑两帧） |
| `img/Strike/Default/0-5.png` | 玩家斩击（6 帧） |
| `img/SpeechBubble/*` | 敌方对话气泡 |
| `img/BattleFont.png`、`DamageFont.png`、`DefaultFont.png` | 位图字体贴图（字形坐标见 `meta.json`） |
| `img/BoneV.png` | 骨头贴图（bad-time 专用） |
| `img/Sans*`、`img/GasterBlaster/*` | Sans 分件与兽颅炮（bad-time 专用） |
| `sfx/*.mp3` | MenuCursor、MenuSelect、BattleText、PlayerFight、PlayerDamaged、HeartSplit、HeartShatter、Ding、Flash、Warning、Slam、BoneStab、GasterBlaster/Blast/Blast2、SansSpeak |
| `meta.json` | 每个动画帧的原点（origin）与挂点（如 SansBody 的 Head 点、SansLegs 的 Torso 点）、字体字形表 |

拼装 Sans：Legs 的 `Torso` 点 → 放 Torso；Torso 的 `Head` 点 → 放 Head；Body（手臂动画）同理。像素按 2 倍整数缩放。
