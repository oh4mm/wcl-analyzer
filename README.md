# wcl-analyzer

读取 [Warcraft Logs](https://www.warcraftlogs.com/) 的公开报告，汇总首领尝试，分析单场战斗的伤害 / 治疗 / 承伤 / 死亡，并输出减伤与药水时间线。

## 准备

在 [API Clients](https://www.warcraftlogs.com/api/clients/) 创建一个应用，然后：

```bash
cd /Users/oh4mm/workspace/python/wcl-analyzer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

把 Client ID 和 Client Secret 填进 `.env`。公开日志用 client credentials 即可。私人日志需要用户授权，这个版本读不了。

## 用法

汇总整份报告里的首领：

```bash
wcl report https://www.warcraftlogs.com/reports/报告代码
wcl report 报告代码
```

**一场 pull = 一个 fight id。** 先查编号再分析：

```bash
wcl report 报告代码 --list-pulls
wcl timeline 报告代码 --list-pulls
```

分析一场战斗。链接里的 `#fight=12` / `?fight=12` 会自动用上；省略时分析最后一次首领/钥石击杀。`--fight` / `--pull` 优先于链接，且会精确选中该 id（含大秘整场）。**链接请务必加引号**：

- zsh 会把未加引号的 `?` 当成通配符（报 `no matches found`）
- 未加引号的 `&` 会把命令拆成后台任务
- 某些情况下 `#fight=…` 后面的片段也会丢

```bash
wcl fight 'https://www.warcraftlogs.com/reports/报告代码#fight=12'
wcl fight 'https://cn.warcraftlogs.com/reports/报告代码?fight=12&type=damage-done'
wcl fight 报告代码 --fight 12
wcl fight 报告代码 --pull 12
```

**网页入口（推荐）**：先打开本地入口页，粘贴 WCL 链接再分析，不用跟 shell 的 `?` / `#` 打架：

```bash
wcl serve --open
# 默认 http://127.0.0.1:8765/
```

入口页可填报告链接（含 `fight`）、可选覆盖 fight id / 只看某玩家；分析完成后进现有泳道时间线，点「换一场」回到入口。

命令行查看某一场 pull 的减伤 / 药水时间线，并对照首领技能施放。默认输出文本表；加 `--open` / `--html` 可看可视化泳道：

```bash
wcl timeline 'https://www.warcraftlogs.com/reports/报告代码#fight=12&type=damage-done'
wcl timeline 'https://cn.warcraftlogs.com/reports/报告代码?fight=12&type=damage-done' --open
wcl timeline 报告代码 --fight 12
wcl timeline 报告代码 --pull 12
wcl timeline 报告代码 --pull 12 --player 法师甲
wcl timeline 报告代码 --pull 12 --category 个减

# 可视化：默认浏览器打开（临时 HTML）
wcl timeline 报告代码 --pull 12 --open

# 可视化：写出 HTML（可再 --open）
wcl timeline 报告代码 --pull 12 --html timeline.html
wcl timeline 报告代码 --pull 12 --player 法师甲 --html out.html --open

# 导出减伤 / 药水 / 饰品 / 打断为 CSV（不含首领技能与阶段）
wcl timeline 报告代码 --pull 12 --export-csv timeline.csv
wcl timeline 报告代码 --pull 12 --player 法师甲 --category 个减 --export-csv mage.csv
```

`timeline` 会按战斗相对时间合并：

- 首领技能施放（波次标记；近战平 A 会过滤；名称尽量用中文）
- 阶段转换（若报告提供 `phaseTransitions`）
- 玩家减伤 / 药水 / 饰品：`个减`、`团减`、`治疗药水`、`爆发药水`、`治疗饰品`
- 首领技能间隔摘要：同技能相邻施法间隔、次数、推算 CD（中位数；受阶段/能量影响，未必等于真实冷却）

HTML 泳道图：横轴为战斗相对时间（mm:ss），顶栏为首领技能 / 阶段，每位有匹配事件的玩家一行（含只喝药水 / 点饰品的人）；技能尽量显示 Wowhead 图标（无类别色描边）。悬停可看时间 / 中英文技能名 / 玩家 / 类别 / 目标（`目标: xxx`，自身施放显示「自身」）。页面下方有首领技能 CD 汇总表。大秘境整场（一个 fight id 含多首领）会显示「整场 / 各首领」切换：按 WCL `dungeonPulls` 时间窗在页内筛选事件并重算横轴与 CD 表（无需重拉）；无多首领段时隐藏该控件。图标来自 WCL master data + Wowhead tooltip，CDN 为 `wow.zamimg.com`（首次解析未知技能时写本地缓存 `~/.cache/wcl-analyzer/spell_cache.json`）。离线可加 `--no-fetch-meta`（仍用已有缓存与 WCL 自带图标）。裂图时前端 `onerror` 会退回彩色文字 / 菱形标记。

技能目录见 `src/wcl_analyzer/defenses.py`（个减 / 团减 / 治疗与爆发药水 / 主动治疗饰品；不含灵界打击一类坦克吞吐自疗）。药水与饰品按战斗日志 spell ID 匹配，目录会随赛季补全，未必覆盖全部变体。宠物施放的技能会归到主人。

加上 `--json` 可以拿到结构化结果（可与 `--html` / `--open` 同时使用）。

`--export-csv FILE` 把本场减伤 / 药水 / 饰品 / 打断事件写成 UTF-8 CSV（表头：时间、偏移毫秒、类别、玩家、专精、职业、技能、技能 ID、英文名、目标）。不含首领技能和阶段标记。已有的 `--player` / `--category` 会先过滤再导出，因此可以只导出某一名玩家或某一种类别。可与 `--html` / `--open` / `--json` 同时使用；单独使用时只写文件并打印路径，不重复输出文本表。

`fight` / `pull` 编号是日志里的战斗 id，不是“第几次尝试”。`report` 的汇总表只列首领，小怪战斗会跳过。

## 限制

- 仅公开日志；私人日志不支持
- 未知首领技能首次需要联网查 Wowhead 才能拿到中文名 / 图标；之后走本地缓存
- HTML 中的图标依赖 Wowhead CDN（`wow.zamimg.com`）。仍可能缺图的情况：报告里没有该 spell 的 icon、Wowhead 无此 ID / 返回 403、本地开了 `--no-fetch-meta` 且缓存也没有、或 CDN 被网络拦截；此时保留彩色标记兜底
- 推算 CD 是本场实测间隔，不是技能面板上的真实冷却
- 未加引号的报告链接在 zsh 里常被 `?` / `&` / `#` 弄坏，看起来像「总是分析最后一次击杀」或命令直接失败——请加引号，或显式传 `--fight` / `--pull`
- 同一份报告可能同时含团本与大秘境；`--list-pulls` 会标出「大秘境 / 团本/首领」。链接里的 fight id 会精确选中该场（含钥石整场）
- HTML 的「单首领」筛选依赖报告的 `dungeonPulls`（优先）或首领施法聚类回退；小怪 pull 不进选项；单首领团本通常不显示该栏

## 测试

```bash
pytest
```
