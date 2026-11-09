"""生成减伤时间线的自包含 HTML 可视化。"""

from __future__ import annotations

import html
import json
from collections import defaultdict

from wcl_analyzer.format import format_duration, format_fight_time
from wcl_analyzer.models import (
    BossAbilityCd,
    TimelineAnalysis,
    TimelineEvent,
    difficulty_label,
    fight_display_name,
    fight_kind_label,
)
from wcl_analyzer.spell_meta import icon_url
from wcl_analyzer.timeline import boss_pull_payload_items, health_series_payload

_CATEGORY_COLORS = {
    "个减": "#2563eb",
    "团减": "#7c3aed",
    "治疗药水": "#059669",
    "爆发药水": "#d97706",
    "治疗饰品": "#db2777",
    "打断": "#0ea5e9",
    "首领技能": "#dc2626",
    "阶段": "#64748b",
}

# 与游戏内职业颜色一致（亮色背景下牧师略加深，避免看不清）
_CLASS_COLORS = {
    "DeathKnight": "#C41E3A",
    "DemonHunter": "#A330C9",
    "Druid": "#FF7C0A",
    "Evoker": "#33937F",
    "Hunter": "#AAD372",
    "Mage": "#3FC7EB",
    "Monk": "#00C78C",
    "Paladin": "#F48CBA",
    "Priest": "#8B8B8B",
    "Rogue": "#C9C24B",
    "Shaman": "#0070DD",
    "Warlock": "#8788EE",
    "Warrior": "#C69B6D",
}

_CLASS_ICON_SLUGS = {
    "DeathKnight": "class_deathknight",
    "DemonHunter": "class_demonhunter",
    "Druid": "class_druid",
    "Evoker": "class_evoker",
    "Hunter": "class_hunter",
    "Mage": "class_mage",
    "Monk": "class_monk",
    "Paladin": "class_paladin",
    "Priest": "class_priest",
    "Rogue": "class_rogue",
    "Shaman": "class_shaman",
    "Warlock": "class_warlock",
    "Warrior": "class_warrior",
}


def render_timeline_html(
    analysis: TimelineAnalysis,
    *,
    home_href: str | None = None,
) -> str:
    """把 TimelineAnalysis 渲染成单文件 HTML（内联 CSS/JS；图标走 Wowhead CDN）。"""
    fight = analysis.fight
    duration_ms = max(fight.duration_ms, 1.0)
    payload = _payload(analysis, duration_ms)
    display = fight_display_name(fight)
    title = html.escape(
        f"{difficulty_label(fight.difficulty, fight.keystone_level)} {display} 减伤时间线"
    )
    headline = html.escape(_headline(analysis))
    data_json = json.dumps(payload, ensure_ascii=False)
    # </script> 出现在 JSON 字符串里时会提前结束脚本；转义防注入
    data_json = data_json.replace("<", "\\u003c").replace(">", "\\u003e")
    home_link = ""
    if home_href:
        home_link = (
            f'<a class="home-link" href="{html.escape(home_href, quote=True)}">'
            "换一场</a>"
        )
    return (
        _HTML_TEMPLATE.replace("__TITLE__", title)
        .replace("__HEADLINE__", headline)
        .replace("__HOME_LINK__", home_link)
        .replace("__DURATION__", html.escape(format_duration(fight.duration_ms)))
        .replace("__FIGHT_ID__", str(fight.id))
        .replace("__FIGHT_KIND__", html.escape(fight_kind_label(fight)))
        .replace("__DATA_JSON__", data_json)
        .replace("__CSS__", _CSS)
        .replace("__JS__", _JS)
    )


def write_timeline_html(analysis: TimelineAnalysis, path: str) -> str:
    content = render_timeline_html(analysis)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def _headline(analysis: TimelineAnalysis) -> str:
    fight = analysis.fight
    result = "击杀" if fight.kill else "灭团"
    if not fight.kill and fight.boss_percentage is not None:
        result = f"灭团 {fight.boss_percentage:.1f}%"
    return (
        f"{difficulty_label(fight.difficulty, fight.keystone_level)}  "
        f"{fight_display_name(fight)}  {result}  {format_duration(fight.duration_ms)}"
    )


def _payload(analysis: TimelineAnalysis, duration_ms: float) -> dict:
    events = [_event_dict(event) for event in analysis.events]
    defense_offsets = [
        event.offset_ms for event in analysis.events if event.kind == "defense"
    ]
    players = _player_lanes(analysis.events)
    boss_pulls = boss_pull_payload_items(analysis.fight, analysis.events)
    health_windows = [
        (float(pull["startOffsetMs"]), float(pull["endOffsetMs"]))
        for pull in boss_pulls
        if pull.get("startOffsetMs") is not None and pull.get("endOffsetMs") is not None
    ]
    return {
        "durationMs": duration_ms,
        "defenseOffsets": defense_offsets,
        "players": players,
        "events": events,
        "bossCds": [_boss_cd_dict(item) for item in analysis.boss_cds],
        "bossPulls": boss_pulls,
        "healthSeries": health_series_payload(
            analysis.health_series,
            windows=health_windows or None,
        ),
        "colors": _CATEGORY_COLORS,
    }


def _event_dict(event: TimelineEvent) -> dict:
    category = event.category
    if event.kind == "boss":
        category = "首领技能"
    elif event.kind == "phase":
        category = "阶段"
    duration_ms = max(0.0, float(event.duration_ms or 0.0))
    return {
        "offsetMs": event.offset_ms,
        "time": format_fight_time(event.offset_ms),
        "kind": event.kind,
        "ability": event.ability,
        "abilityEn": event.ability_en or "",
        "abilityId": event.ability_id,
        "category": category or "—",
        "actor": event.actor or "",
        "spec": event.spec or "",
        "actorClass": event.actor_class or "",
        "classColor": _CLASS_COLORS.get(event.actor_class or "", ""),
        "classIconUrl": class_icon_url(event.actor_class) or "",
        "target": event.target or "",
        "durationMs": duration_ms,
        "duration": format_duration(duration_ms) if duration_ms > 0 else "",
        "description": event.description or "",
        "castLabel": event.cast_label or "",
        "durationLabel": event.duration_label or "",
        "color": _CATEGORY_COLORS.get(category or "", "#64748b"),
        "iconUrl": icon_url(event.icon) or "",
    }


def _boss_cd_dict(item: BossAbilityCd) -> dict:
    return {
        "ability": item.ability,
        "abilityEn": item.ability_en or "",
        "abilityId": item.ability_id,
        "castCount": item.cast_count,
        "iconUrl": icon_url(item.icon) or "",
        "intervals": [format_duration(value) for value in item.intervals_ms],
        "median": format_duration(item.median_interval_ms)
        if item.median_interval_ms is not None
        else "—",
        "min": format_duration(item.min_interval_ms)
        if item.min_interval_ms is not None
        else "—",
        "max": format_duration(item.max_interval_ms)
        if item.max_interval_ms is not None
        else "—",
        "times": [format_fight_time(value) for value in item.timestamps_ms],
    }


def _player_lanes(events: tuple[TimelineEvent, ...] | list[TimelineEvent]) -> list[dict]:
    buckets: dict[str, list[TimelineEvent]] = defaultdict(list)
    specs: dict[str, str] = {}
    classes: dict[str, str] = {}
    for event in events:
        if event.kind != "defense" or not event.actor:
            continue
        buckets[event.actor].append(event)
        if event.spec and event.actor not in specs:
            specs[event.actor] = event.spec
        if event.actor_class and event.actor not in classes:
            classes[event.actor] = event.actor_class

    lanes: list[dict] = []
    for name in sorted(buckets, key=lambda item: (-len(buckets[item]), item)):
        actor_class = classes.get(name, "")
        lanes.append(
            {
                "name": name,
                "spec": specs.get(name, ""),
                "actorClass": actor_class,
                "classColor": _CLASS_COLORS.get(actor_class, ""),
                "classIconUrl": class_icon_url(actor_class) or "",
                "count": len(buckets[name]),
            }
        )
    return lanes


def class_icon_url(actor_class: str | None) -> str | None:
    if not actor_class:
        return None
    slug = _CLASS_ICON_SLUGS.get(actor_class)
    if not slug:
        return None
    return f"https://wow.zamimg.com/images/wow/icons/medium/{slug}.jpg"


_CSS = """
:root {
  --bg: #f8fafc;
  --panel: #ffffff;
  --ink: #0f172a;
  --muted: #64748b;
  --line: #e2e8f0;
  --lane: #f1f5f9;
  --label-w: 132px;
  --boss-h: 40px;
  --row-h: 28px;
  --stack-step: 15px;
  --icon-s: 18px;
  --pad: 12px;
  /* WowAnalyzer-like second grid (light theme equivalents of rgba white ticks) */
  --sec-w: 60px;
  --duration-s: 60;
  --grid-1s: rgba(15, 23, 42, 0.10);
  --grid-major: rgba(15, 23, 42, 0.28);
  --axis-bg: #f8fafc;
  --track-w: calc(var(--duration-s) * var(--sec-w));
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: var(--bg);
  color: var(--ink);
  font: 13px/1.35 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
body {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
header {
  padding: 10px var(--pad) 4px;
  max-width: 100%;
  flex-shrink: 0;
}
.header-top {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.home-link {
  color: #1d4ed8;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
}
.home-link:hover { text-decoration: underline; }
h1 {
  margin: 0 0 2px;
  font-size: 16px;
  font-weight: 600;
}
h2 {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
}
.meta, .hint {
  color: var(--muted);
  font-size: 12px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  align-items: center;
  padding: 4px var(--pad) 6px;
  flex-shrink: 0;
}
.toolbar-options {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  margin-left: auto;
}
.toolbar label.opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  user-select: none;
}
.toolbar label.opt input {
  margin: 0;
}
.boss-pull-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  align-items: center;
  padding: 0 var(--pad) 6px;
  flex-shrink: 0;
}
.boss-pull-bar .hint {
  margin-right: 4px;
}
#boss-pull-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  align-items: stretch;
}
.boss-pull-btn {
  appearance: none;
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  font: inherit;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 5px;
  cursor: pointer;
  text-align: left;
  line-height: 1.2;
}
.boss-pull-btn:hover {
  border-color: #94a3b8;
}
.boss-pull-btn.active {
  background: #0f172a;
  border-color: #0f172a;
  color: #f8fafc;
}
.boss-pull-btn .pull-name {
  font-weight: 600;
}
.boss-pull-btn .pull-time {
  font-size: 11px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.boss-pull-btn.active .pull-time {
  color: rgba(248, 250, 252, 0.78);
}
.boss-ability-bar {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px 8px;
  align-items: flex-start;
  padding: 0 var(--pad) 6px;
  flex-shrink: 0;
  max-height: 64px;
  overflow: auto;
}
.boss-ability-bar .hint {
  margin-right: 2px;
  flex-shrink: 0;
  padding-top: 4px;
}
.boss-ability-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
  align-items: center;
}
.boss-ability-btn {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--muted);
  font: inherit;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 5px;
  cursor: pointer;
  user-select: none;
}
.boss-ability-btn:hover {
  border-color: #94a3b8;
  color: var(--ink);
}
.boss-ability-btn.active {
  background: #0f172a;
  border-color: #0f172a;
  color: #f8fafc;
}
.boss-ability-btn .ability-icon {
  width: 16px;
  height: 16px;
  border-radius: 2px;
  border: 1px solid var(--line);
  flex-shrink: 0;
}
.boss-ability-btn.active .ability-icon {
  border-color: rgba(248, 250, 252, 0.35);
}
.boss-ability-btn .ability-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4em;
  padding: 0 5px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  line-height: 1.4;
}
.boss-ability-btn.active .ability-count {
  background: rgba(245, 158, 11, 0.95);
  color: #0f172a;
  font-weight: 700;
}
.board-wrap {
  overflow: auto;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  background: var(--panel);
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
}
.board-wrap::-webkit-scrollbar {
  height: 12px;
}
.board-wrap::-webkit-scrollbar-thumb {
  border-radius: 10px;
  background-color: #94a3b8;
}
.board {
  position: relative;
  /* 严格贴合可见窗口：label + sec-w * duration，避免 max-content 被溢出刻度撑出空白尾 */
  width: calc(var(--label-w) + var(--track-w));
  max-width: calc(var(--label-w) + var(--track-w));
  /* 不能用 overflow:hidden，否则会打断左侧姓名列的 position:sticky */
  overflow: visible;
}
.axis-row {
  display: grid;
  grid-template-columns: var(--label-w) var(--track-w);
  position: sticky;
  top: 0;
  z-index: 6;
  background: var(--axis-bg);
  border-bottom: 1px solid var(--grid-major);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}
.axis-corner {
  position: sticky;
  left: 0;
  z-index: 7;
  background: var(--axis-bg);
  border-right: 1px solid var(--line);
}
.axis {
  position: relative;
  height: 30px;
  width: var(--track-w);
  overflow: hidden;
  cursor: col-resize;
  touch-action: none;
  user-select: none;
}
.tick {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  border-left: 1px solid var(--grid-major);
  color: rgba(71, 85, 105, 0.9);
  font-size: 12px;
  line-height: 1;
  pointer-events: none;
}
.tick span {
  position: absolute;
  left: 0;
  top: 8px;
  transform: translateX(-50%);
  white-space: nowrap;
  padding: 0 2px;
}
.tick.origin {
  border-left-color: transparent;
}
.tick.origin span {
  transform: translateX(0);
  padding-left: 2px;
}
.lane-row {
  display: grid;
  grid-template-columns: var(--label-w) var(--track-w);
  min-height: var(--row-h);
  border-bottom: 1px solid var(--line);
}
.lane-row.boss {
  min-height: var(--boss-h);
  background: #fff7ed;
}
.lane-label {
  position: sticky;
  left: 0;
  z-index: 4;
  background: var(--panel);
  border-right: 1px solid var(--line);
  padding: 2px 6px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  box-shadow: 4px 0 8px -6px rgba(15, 23, 42, 0.35);
}
.lane-row.alt .lane-label {
  background: #f8fafc;
}
.lane-row.boss .lane-label { background: #fff7ed; }
.lane-label .class-icon {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  flex-shrink: 0;
  image-rendering: auto;
}
.lane-label .name {
  font-weight: 700;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.lane-label .name.class-tinted {
  text-shadow: 0 0 1px rgba(15, 23, 42, 0.25);
}
.track {
  position: relative;
  min-height: inherit;
  width: var(--track-w);
  /* 每秒一条竖线：CSS 渐变，避免为长战斗创建上千 DOM 节点 */
  background-color: transparent;
  background-image:
    repeating-linear-gradient(
      to right,
      transparent 0,
      transparent calc(var(--sec-w) - 1px),
      var(--grid-1s) calc(var(--sec-w) - 1px),
      var(--grid-1s) var(--sec-w)
    );
}
.lane-row.alt .track {
  background-color: rgba(241, 245, 249, 0.55);
}
.lane-row.boss .track {
  background-color: rgba(255, 247, 237, 0.35);
  background-image:
    repeating-linear-gradient(
      to right,
      transparent 0,
      transparent calc(var(--sec-w) - 1px),
      rgba(194, 65, 12, 0.12) calc(var(--sec-w) - 1px),
      rgba(194, 65, 12, 0.12) var(--sec-w)
    );
}
.marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  cursor: default;
  z-index: 1;
}
.marker.defense {
  height: 18px;
  min-width: 18px;
  padding: 0 6px;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  line-height: 18px;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08);
}
.marker.defense.has-icon {
  width: var(--icon-s);
  height: var(--icon-s);
  min-width: var(--icon-s);
  padding: 0;
  max-width: none;
  border: 0;
  border-radius: 2px;
  background: transparent;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.14);
  overflow: hidden;
}
.marker.defense.has-icon img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}
/* WowAnalyzer 玩家技能：弱化金米色持续条；重叠时在泳道内向上堆叠 */
.player-cast {
  position: absolute;
  height: var(--icon-s);
  min-width: var(--icon-s);
  z-index: 1;
  pointer-events: none;
}
.player-cast.instant {
  transform: translate(-50%, -50%);
}
.player-cast .effect-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 7px;
  width: 100%;
  border-radius: 4px;
  /* 弱化：低饱和米色 + 低透明度，不压过图标 */
  background: rgba(214, 184, 120, 0.38);
  box-shadow: inset 0 0 0 1px rgba(180, 140, 70, 0.22);
  z-index: 0;
  pointer-events: none;
}
.player-cast .effect-backdrop {
  position: absolute;
  left: 0;
  top: -2px;
  bottom: -2px;
  width: 100%;
  border-radius: 3px;
  background: rgba(148, 163, 184, 0.14);
  z-index: 0;
  pointer-events: none;
}
.player-cast .marker.defense {
  position: absolute;
  left: 0;
  top: 0;
  transform: none;
  pointer-events: auto;
  z-index: 2;
}
.player-cast.instant .marker.defense {
  left: 50%;
  transform: translateX(-50%);
}
.lane-row.player-stacked {
  /* 由 JS 按堆叠层数设置 --stack-n；步长更紧凑 */
  min-height: calc(22px + var(--stack-n, 1) * var(--stack-step));
}
.lane-row.player-stacked .lane-label {
  align-items: flex-start;
  padding-top: 4px;
}
/* WowAnalyzer EnemyCasts：图标在施法起点，.channel 条向右铺开 cast/channel 时长 */
.boss-cast {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  height: var(--icon-s);
  min-width: var(--icon-s);
  z-index: 1;
  pointer-events: none;
}
.boss-cast.instant {
  transform: translate(-50%, -50%);
}
.boss-cast .cast-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 8px;
  width: 100%;
  border-radius: 3px;
  /* 浅色主题版 WA channel：红系底 + 斜纹 */
  background-color: #fecaca;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='10' viewBox='0 0 10 10' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23dc2626' fill-opacity='0.45' fill-rule='evenodd'%3E%3Cpath d='M0 10L10 0H5L0 5M10 10V5L5 10'/%3E%3C/g%3E%3C/svg%3E");
  box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.25);
  z-index: 0;
  pointer-events: none;
}
.boss-cast .marker.boss {
  position: absolute;
  left: 0;
  top: 0;
  transform: none;
  pointer-events: auto;
  z-index: 1;
}
.boss-cast.instant .marker.boss {
  left: 50%;
  transform: translateX(-50%);
}
.marker.boss {
  width: 11px;
  height: 11px;
  margin-top: 5.5px;
  background: var(--c, #dc2626);
  transform: rotate(45deg);
  border-radius: 1px;
}
.marker.boss.has-icon {
  width: var(--icon-s);
  height: var(--icon-s);
  margin-top: 0;
  transform: none;
  border-radius: 2px;
  border: 0;
  background: transparent;
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.12);
}
.boss-cast.instant .marker.boss:not(.has-icon) {
  transform: translateX(-50%) rotate(45deg);
}
.marker.boss.has-icon img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}
.marker.phase-flag {
  top: 0;
  bottom: 0;
  width: 0;
  height: auto;
  transform: translateX(-50%);
  border-left: 2px dashed var(--c, #64748b);
  background: transparent;
}
.phase-tag {
  position: absolute;
  top: 4px;
  left: 4px;
  transform: none;
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
  background: rgba(248, 250, 252, 0.9);
  padding: 1px 4px;
  border-radius: 3px;
}
.vguide {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  border-left: 1px dashed rgba(100, 116, 139, 0.45);
  pointer-events: none;
  z-index: 0;
}
.ability-guides {
  position: absolute;
  top: 0;
  bottom: 0;
  left: var(--label-w);
  width: var(--track-w);
  pointer-events: none;
  z-index: 2;
}
.ability-guide-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  border-left: 1px dashed rgba(245, 158, 11, 0.55);
  box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.1);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}
.ability-guide-line.current {
  border-left: 2px solid #f59e0b;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.55);
  z-index: 3;
  animation: guide-pulse 0.7s ease;
}
@keyframes guide-pulse {
  0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.0); }
  40% { box-shadow: 0 0 18px 4px rgba(245, 158, 11, 0.65); }
  100% { box-shadow: 0 0 12px rgba(245, 158, 11, 0.55); }
}
@media (prefers-reduced-motion: reduce) {
  .ability-guide-line.current { animation: none; }
  .board-wrap { scroll-behavior: auto; }
}
#tooltip {
  position: fixed;
  z-index: 20;
  display: none;
  max-width: 300px;
  padding: 8px 10px;
  background: #0f172a;
  color: #f8fafc;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  pointer-events: none;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.25);
}
#tooltip .t-time { color: #94a3b8; margin-bottom: 2px; }
#tooltip .t-en { color: #94a3b8; font-size: 11px; margin-top: 2px; }
#tooltip .t-meta { color: #cbd5e1; margin-top: 4px; }
#tooltip .t-caster { color: #cbd5e1; margin-top: 6px; }
#tooltip .t-target { color: #cbd5e1; margin-top: 4px; }
#tooltip .t-duration { color: #cbd5e1; margin-top: 4px; }
#tooltip .t-desc {
  color: #e2e8f0;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(148, 163, 184, 0.25);
  white-space: pre-wrap;
  line-height: 1.45;
  max-width: 320px;
}
#tooltip strong { font-weight: 600; }
#tooltip .t-icon {
  float: left;
  width: 28px;
  height: 28px;
  margin: 0 8px 4px 0;
  border-radius: 3px;
  border: 1px solid rgba(148, 163, 184, 0.45);
}
#tooltip.boss-tip {
  text-align: center;
  min-width: 120px;
}
#tooltip.boss-tip .t-icon {
  float: none;
  display: block;
  width: 36px;
  height: 36px;
  margin: 0 auto 8px;
}
#tooltip.boss-tip .t-name {
  display: block;
  font-weight: 600;
  font-size: 13px;
}
#tooltip.boss-tip .t-desc {
  text-align: left;
}
.empty {
  padding: 24px var(--pad);
  color: var(--muted);
}
.cd-section {
  padding: 8px var(--pad) 12px;
  flex-shrink: 0;
  max-height: 26vh;
  overflow: auto;
  border-top: 1px solid var(--line);
  background: var(--bg);
}
.cd-note {
  color: var(--muted);
  font-size: 12px;
  margin: 0 0 10px;
}
.cd-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--panel);
  font-size: 13px;
}
.cd-table th, .cd-table td {
  border: 1px solid var(--line);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}
.cd-table th {
  background: #f1f5f9;
  font-weight: 600;
  white-space: nowrap;
}
.cd-table td.num { text-align: right; white-space: nowrap; }
.cd-ability {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.cd-ability img {
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: 1px solid var(--line);
}
.cd-empty { color: var(--muted); }
.hp-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
  padding: 0 var(--pad) 8px;
  flex-shrink: 0;
  max-height: 88px;
  overflow: auto;
}
.hp-panel[hidden] { display: none !important; }
.hp-panel .hp-time {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  min-width: 3.6em;
}
.hp-panel .hp-hint {
  color: var(--muted);
  font-size: 11px;
  margin-right: 2px;
}
.hp-panel .hp-empty {
  color: var(--muted);
  font-size: 12px;
}
.hp-bars {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
  flex: 1 1 auto;
  min-width: 0;
}
.hp-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 140px;
  max-width: 220px;
}
.hp-item .hp-name {
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 72px;
  color: var(--ink);
}
.hp-item.boss .hp-name { color: #b45309; }
.hp-item.add .hp-name { color: #64748b; }
.hp-bar {
  position: relative;
  flex: 1 1 auto;
  min-width: 56px;
  height: 12px;
  border-radius: 3px;
  background: #e2e8f0;
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.08);
}
.hp-bar > span {
  display: block;
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #dc2626, #f59e0b 55%, #22c55e);
  border-radius: 3px;
}
.hp-item.dead .hp-bar > span { background: #94a3b8; }
.hp-pct {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  min-width: 3.2em;
  text-align: right;
}
.scrub-handle {
  position: absolute;
  top: 2px;
  bottom: 2px;
  width: 14px;
  margin-left: -7px;
  background: #2563eb;
  border-radius: 3px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.28);
  z-index: 8;
  cursor: col-resize;
  touch-action: none;
  pointer-events: auto;
}
.scrub-handle::after {
  content: "";
  position: absolute;
  inset: -6px -10px;
}
.playhead-layer {
  position: absolute;
  top: 0;
  bottom: 0;
  left: var(--label-w);
  width: var(--track-w);
  pointer-events: none;
  z-index: 8;
}
.playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  border-left: 2px solid #2563eb;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.15);
  transform: translateX(-1px);
  pointer-events: none;
}
.playhead .playhead-hit {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -10px;
  width: 20px;
  cursor: col-resize;
  touch-action: none;
  pointer-events: auto;
}
"""


_JS = r"""
(function () {
  const data = window.TIMELINE_DATA;
  const board = document.getElementById("board");
  const axis = document.getElementById("axis");
  const tooltip = document.getElementById("tooltip");
  const cdBody = document.getElementById("cd-body");
  const cdTitle = document.getElementById("cd-title");
  const pullWrap = document.getElementById("boss-pull-wrap");
  const pullButtons = document.getElementById("boss-pull-buttons");
  const abilityWrap = document.getElementById("boss-ability-wrap");
  const abilityButtons = document.getElementById("boss-ability-buttons");
  const boardWrap = board.parentElement;
  const hpPanel = document.getElementById("hp-panel");
  const hpTime = document.getElementById("hp-time");
  const hpBars = document.getElementById("hp-bars");

  const fullDuration = Math.max(data.durationMs, 1);
  const bossPulls = data.bossPulls || [];
  const healthSeries = data.healthSeries || [];
  let activePullId = "all";
  let selectedAbilityId = null;
  let abilityNavIndex = -1;
  let focusedCastMs = null;
  let showInterrupts = false;
  let viewStart = 0;
  let viewDuration = fullDuration;
  let visibleEvents = data.events.slice();
  let playerLaneIndex = 0;
  let scrubMs = 0;
  let scrubbing = false;
  let scrubPointerId = null;
  let playheadEl = null;
  let scrubHandleEl = null;
  let scrubListenersBound = false;
  // 必须在首次 setupHpPanel() 之前初始化，否则 let TDZ 会让整段脚本中断
  let shownHealthSeries = [];

  const interruptToggle = document.getElementById("opt-interrupts");
  if (interruptToggle) {
    interruptToggle.checked = false;
    interruptToggle.addEventListener("change", function () {
      showInterrupts = !!interruptToggle.checked;
      applyWindow();
      setupAbilityButtons();
      paint();
      paintCds(summarizeBossCds(visibleEvents));
    });
  }

  if (!data.events.length) {
    board.innerHTML = '<div class="empty">无匹配事件。</div>';
    setupHpPanel();
    paintCds([]);
    updateHpPanel();
    return;
  }

  setupPullButtons();
  applyWindow();
  scrubMs = viewStart;
  setupHpPanel();
  setupAbilityButtons();
  paint();
  paintCds(summarizeBossCds(visibleEvents));
  updateHpPanel();

  function setupPullButtons() {
    if (bossPulls.length < 2) {
      pullWrap.hidden = true;
      activePullId = "all";
      return;
    }
    // 默认选中第一个首领战，不再提供「整场」选项
    activePullId = String(bossPulls[0].id);
    pullWrap.hidden = false;
    pullButtons.innerHTML = "";
    bossPulls.forEach(function (pull) {
      addPullButton(pull);
    });
  }

  function addPullButton(pull) {
    const id = String(pull.id);
    const label = pull.label || pull.name || ("首领 " + id);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "boss-pull-btn" + (id === activePullId ? " active" : "");
    btn.dataset.pullId = id;
    const nameEl = document.createElement("span");
    nameEl.className = "pull-name";
    nameEl.textContent = label;
    const timeEl = document.createElement("span");
    timeEl.className = "pull-time";
    const startMs = pull.startOffsetMs || 0;
    const endMs = pull.endOffsetMs != null ? pull.endOffsetMs : startMs;
    timeEl.textContent = fmtAxis(startMs) + "–" + fmtAxis(endMs)
      + " · " + fmtDuration(Math.max(0, endMs - startMs));
    btn.appendChild(nameEl);
    btn.appendChild(timeEl);
    btn.addEventListener("click", function () {
      if (activePullId === id) return;
      activePullId = id;
      selectedAbilityId = null;
      pullButtons.querySelectorAll(".boss-pull-btn").forEach(function (el) {
        el.classList.toggle("active", el.dataset.pullId === activePullId);
      });
      applyWindow();
      scrubMs = viewStart;
      setupHpPanel();
      setupAbilityButtons();
      paint();
      paintCds(summarizeBossCds(visibleEvents));
      updateHpPanel();
    });
    pullButtons.appendChild(btn);
  }

  function abilityKey(ev) {
    if (ev.abilityId != null && ev.abilityId !== "") {
      return "id:" + String(ev.abilityId);
    }
    return "name:" + String(ev.ability || "");
  }

  function setupAbilityButtons() {
    const abilities = [];
    const byKey = {};
    visibleEvents.forEach(function (ev) {
      if (ev.kind !== "boss") return;
      const key = abilityKey(ev);
      if (!byKey[key]) {
        byKey[key] = {
          key: key,
          ability: ev.ability || "（未知）",
          abilityEn: ev.abilityEn || "",
          iconUrl: ev.iconUrl || "",
          times: {},
        };
        abilities.push(byKey[key]);
      }
      byKey[key].times[ev.offsetMs] = true;
      if (!byKey[key].iconUrl && ev.iconUrl) {
        byKey[key].iconUrl = ev.iconUrl;
      }
    });
    abilities.forEach(function (item) {
      item.count = Object.keys(item.times).length;
    });
    abilities.sort(function (a, b) {
      return a.ability.localeCompare(b.ability, "zh");
    });
    if (!abilities.length) {
      abilityWrap.hidden = true;
      abilityButtons.innerHTML = "";
      selectedAbilityId = null;
      abilityNavIndex = -1;
      focusedCastMs = null;
      return;
    }
    abilityWrap.hidden = false;
    abilityButtons.innerHTML = "";
    abilities.forEach(function (item) {
      addAbilityButton(item.key, item.ability, item.iconUrl, item.count);
    });
    refreshAbilityCountLabels();
  }

  function addAbilityButton(key, label, iconUrl, count) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "boss-ability-btn" + (key === selectedAbilityId ? " active" : "");
    btn.dataset.abilityId = key;
    btn.dataset.castCount = String(count || 0);
    if (iconUrl) {
      const img = document.createElement("img");
      img.className = "ability-icon";
      img.src = iconUrl;
      img.alt = "";
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      img.onerror = function () { img.remove(); };
      btn.appendChild(img);
    }
    const text = document.createElement("span");
    text.className = "ability-name";
    text.textContent = label;
    btn.appendChild(text);
    const countEl = document.createElement("span");
    countEl.className = "ability-count";
    countEl.dataset.role = "count";
    countEl.textContent = String(count || 0);
    btn.appendChild(countEl);
    btn.title = label + " · 共施放 " + (count || 0) + " 次";
    btn.addEventListener("click", function () {
      navigateAbilityCast(key);
    });
    abilityButtons.appendChild(btn);
  }

  function refreshAbilityCountLabels() {
    abilityButtons.querySelectorAll(".boss-ability-btn").forEach(function (el) {
      const countEl = el.querySelector('[data-role="count"]');
      if (!countEl) return;
      const total = parseInt(el.dataset.castCount || "0", 10) || 0;
      const key = el.dataset.abilityId;
      if (key && key === selectedAbilityId && abilityNavIndex >= 0 && total > 0) {
        countEl.textContent = (abilityNavIndex + 1) + "/" + total;
        el.title = (el.querySelector(".ability-name") || {}).textContent +
          " · 第 " + (abilityNavIndex + 1) + " / " + total + " 次";
      } else {
        countEl.textContent = String(total);
        el.title = (el.querySelector(".ability-name") || {}).textContent +
          " · 共施放 " + total + " 次";
      }
    });
  }

  function abilityCastTimes(key) {
    const times = [];
    const seen = {};
    visibleEvents.forEach(function (ev) {
      if (ev.kind !== "boss") return;
      if (abilityKey(ev) !== key) return;
      const t = ev.offsetMs;
      if (seen[t]) return;
      seen[t] = true;
      times.push(t);
    });
    times.sort(function (a, b) { return a - b; });
    return times;
  }

  function labelWidthPx() {
    const raw = getComputedStyle(board).getPropertyValue("--label-w");
    const n = parseFloat(raw);
    return Number.isFinite(n) ? n : 132;
  }

  function secWidthPx() {
    const raw = getComputedStyle(board).getPropertyValue("--sec-w");
    const n = parseFloat(raw);
    return Number.isFinite(n) && n > 0 ? n : 60;
  }

  function currentViewTimeMs() {
    // 粘性姓名列右侧、轨道可见区中心对应的战斗时间
    const trackVisible = Math.max(boardWrap.clientWidth - labelWidthPx(), 1);
    const x = boardWrap.scrollLeft + trackVisible / 2;
    return viewStart + (x / secWidthPx()) * 1000;
  }

  function nearestCastIndex(times, timeMs) {
    let best = 0;
    let bestDist = Infinity;
    times.forEach(function (t, index) {
      const dist = Math.abs(t - timeMs);
      if (dist < bestDist) {
        bestDist = dist;
        best = index;
      }
    });
    return best;
  }

  function scrollToCast(offsetMs) {
    if (!boardWrap) return;
    const trackVisible = Math.max(boardWrap.clientWidth - labelWidthPx(), 1);
    const x = ((offsetMs - viewStart) / 1000) * secWidthPx();
    const target = Math.max(0, x - trackVisible / 2);
    const reduceMotion = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    boardWrap.scrollTo({
      left: target,
      behavior: reduceMotion ? "auto" : "smooth",
    });
  }

  function navigateAbilityCast(key) {
    const times = abilityCastTimes(key);
    if (!times.length) return;

    if (selectedAbilityId !== key) {
      selectedAbilityId = key;
      abilityNavIndex = nearestCastIndex(times, currentViewTimeMs());
    } else {
      abilityNavIndex = (abilityNavIndex + 1) % times.length;
    }
    focusedCastMs = times[abilityNavIndex];

    abilityButtons.querySelectorAll(".boss-ability-btn").forEach(function (el) {
      el.classList.toggle("active", el.dataset.abilityId === selectedAbilityId);
    });
    refreshAbilityCountLabels();
    applyAbilityHighlight();
    scrollToCast(focusedCastMs);
  }

  function clearAbilityGuides() {
    board.querySelectorAll(".ability-guides").forEach(function (n) { n.remove(); });
  }

  function applyAbilityHighlight() {
    clearAbilityGuides();
    if (!selectedAbilityId) {
      focusedCastMs = null;
      abilityNavIndex = -1;
      refreshAbilityCountLabels();
      return;
    }
    const layer = document.createElement("div");
    layer.className = "ability-guides";
    const times = abilityCastTimes(selectedAbilityId);
    times.forEach(function (t) {
      const line = document.createElement("div");
      line.className = "ability-guide-line" +
        (focusedCastMs != null && Math.abs(t - focusedCastMs) < 0.5 ? " current" : "");
      line.style.left = xPct(t) + "%";
      layer.appendChild(line);
    });
    board.appendChild(layer);
  }

  function applyWindow() {
    if (activePullId === "all") {
      viewStart = 0;
      viewDuration = fullDuration;
      visibleEvents = data.events.slice();
    } else {
      const pull = bossPulls.find(function (item) {
        return String(item.id) === String(activePullId);
      });
      viewStart = pull ? pull.startOffsetMs : 0;
      const viewEnd = pull ? pull.endOffsetMs : fullDuration;
      viewDuration = Math.max(viewEnd - viewStart, 1);
      // 施法条按区间相交保留（起点在窗外但条伸进窗内也要显示并裁剪）
      visibleEvents = data.events.filter(function (ev) {
        const end = ev.offsetMs + (ev.durationMs || 0);
        return end >= viewStart && ev.offsetMs <= viewEnd;
      });
    }
    if (!showInterrupts) {
      visibleEvents = visibleEvents.filter(function (ev) {
        return !(ev.kind === "defense" && ev.category === "打断");
      });
    }
    if (cdTitle) {
      if (activePullId === "all") {
        cdTitle.textContent = "首领技能间隔（本场实测）";
      } else {
        const pull = bossPulls.find(function (item) {
          return String(item.id) === String(activePullId);
        });
        const name = pull ? (pull.label || pull.name) : "所选首领";
        cdTitle.textContent = "首领技能间隔（" + name + "）";
      }
    }
    // 保持 playhead 落在当前窗口内
    scrubMs = clampScrub(scrubMs);
  }

  // 对齐 WowAnalyzer：默认约 60px/秒；长窗口略缩小以控制横向长度。
  // skipInterval = ceil(40 / secWidth)，近距时每秒标尺，拉远时每 N 秒标一次。
  function pickSecondWidth(ms) {
    const seconds = Math.max(ms, 1) / 1000;
    if (seconds <= 180) return 60;
    if (seconds <= 480) return 40;
    if (seconds <= 1200) return 24;
    return 16;
  }

  function pickSkipInterval(secWidth) {
    return Math.max(1, Math.ceil(40 / secWidth));
  }

  function fmtAxis(ms) {
    const total = Math.max(0, Math.round(ms / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return m + ":" + String(s).padStart(2, "0");
  }

  function fmtFightTime(ms) {
    const total = Math.max(0, Math.round(ms));
    const m = Math.floor(total / 60000);
    const rem = total % 60000;
    const s = Math.floor(rem / 1000);
    const frac = rem % 1000;
    return m + ":" + String(s).padStart(2, "0") + "." + String(frac).padStart(3, "0");
  }

  function fmtDuration(ms) {
    const total = Math.max(0, Math.round(ms / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    if (m <= 0) return s + "s";
    return m + ":" + String(s).padStart(2, "0");
  }

  function xPct(offsetMs) {
    return ((offsetMs - viewStart) / viewDuration) * 100;
  }

  function clearLanes() {
    board.querySelectorAll(".lane-row").forEach(function (n) { n.remove(); });
    clearAbilityGuides();
    axis.innerHTML = "";
  }

  function paint() {
    clearLanes();
    playerLaneIndex = 0;
    // 用精确秒数设定轨道宽，避免 ceil/额外 padding 在窗口末尾留下可滚动空白
    const totalSeconds = Math.max(viewDuration, 1) / 1000;
    const secWidth = pickSecondWidth(viewDuration);
    const skipInterval = pickSkipInterval(secWidth);
    board.style.setProperty("--sec-w", secWidth + "px");
    board.style.setProperty("--duration-s", String(totalSeconds));
    board.style.setProperty("--track-w", "calc(var(--duration-s) * var(--sec-w))");

    // 标尺标签：按秒对齐；每隔 skipInterval 尝试放刻度，但若像素间距不足则跳过，
    // 避免绝对时间如 18:54 / 18:55 在 secWidth≈60 时重叠（origin 左对齐 + 下一刻度居中）。
    const lastLabeled = Math.floor(totalSeconds / skipInterval) * skipInterval;
    let lastLabelRight = -1e9;
    function estimateLabelWidth(text) {
      // 12px 等宽近似；"18:54" ≈ 36–42px
      return Math.max(34, String(text).length * 7.2);
    }
    function placeAxisTick(sec, isOrigin) {
      const x = sec * secWidth;
      const text = fmtAxis(viewStart + sec * 1000);
      const w = estimateLabelWidth(text);
      // origin 左对齐：占 [x, x+w]；其余居中：占 [x-w/2, x+w/2]
      const left = isOrigin ? x : x - w / 2;
      const right = isOrigin ? x + w : x + w / 2;
      if (left < lastLabelRight + 6) return false;
      const t = document.createElement("div");
      t.className = "tick" + (isOrigin ? " origin" : "");
      t.style.left = x + "px";
      const label = document.createElement("span");
      label.textContent = text;
      t.appendChild(label);
      axis.appendChild(t);
      lastLabelRight = right;
      return true;
    }
    for (let sec = 0; sec <= lastLabeled + 1e-9; sec += skipInterval) {
      placeAxisTick(sec, sec === 0);
    }
    // 窗口终点若未落在标签上，且与上一标签有足够间距，补结束刻度
    if (totalSeconds - lastLabeled > 0.05) {
      placeAxisTick(totalSeconds, false);
    }

    const bossRow = makeRow({ name: "首领 / 小怪", isBoss: true });
    const tracks = [bossRow.querySelector(".track")];

    if (!data.players.length) {
      tracks.push(makeRow({ name: "（无玩家事件）" }).querySelector(".track"));
    } else {
      data.players.forEach(function (player) {
        tracks.push(makeRow(player).querySelector(".track"));
      });
    }

    const phaseEvents = visibleEvents.filter(function (ev) { return ev.kind === "phase"; });
    phaseEvents.forEach(function (ev) {
      addPhase(tracks[0], ev);
      for (let i = 1; i < tracks.length; i++) {
        addGuide(tracks[i], ev.offsetMs);
      }
    });

    visibleEvents.forEach(function (ev) {
      if (ev.kind === "boss") {
        addBoss(tracks[0], ev);
      }
    });

    data.players.forEach(function (player, index) {
      const track = tracks[index + 1];
      if (!track) return;
      const row = track.parentElement;
      const playerEvents = visibleEvents.filter(function (ev) {
        return ev.kind === "defense" && ev.actor === player.name;
      });
      const stackLevels = assignStackLevels(playerEvents);
      let maxStack = 0;
      stackLevels.forEach(function (level) {
        if (level > maxStack) maxStack = level;
      });
      if (row && maxStack > 0) {
        row.classList.add("player-stacked");
        row.style.setProperty("--stack-n", String(maxStack + 1));
      }
      playerEvents.forEach(function (ev, evIndex) {
        addDefense(track, ev, stackLevels[evIndex] || 0, maxStack);
      });
    });

    applyAbilityHighlight();
    ensureScrubber();
    updatePlayhead();
  }

  function clampScrub(ms) {
    const viewEnd = viewStart + viewDuration;
    if (!Number.isFinite(ms)) return viewStart;
    return Math.max(viewStart, Math.min(viewEnd, ms));
  }

  function seriesOverlapsView(series) {
    const samples = series.samples || [];
    if (!samples.length) return false;
    const viewEnd = viewStart + viewDuration;
    return samples[0].offsetMs <= viewEnd + 1 &&
      samples[samples.length - 1].offsetMs >= viewStart - 1;
  }

  function pickHealthSeriesForView() {
    // 只展示当前时间窗内有采样的单位，否则拖动时血条会一直停在 100%/0%
    const active = healthSeries.filter(seriesOverlapsView);
    active.sort(function (a, b) {
      const bossDiff = (b.isBoss ? 1 : 0) - (a.isBoss ? 1 : 0);
      if (bossDiff) return bossDiff;
      return (b.samples || []).length - (a.samples || []).length;
    });
    return active.slice(0, 8);
  }

  function setupHpPanel() {
    if (!hpPanel || !hpBars) return;
    hpPanel.hidden = false;
    hpBars.innerHTML = "";
    shownHealthSeries = pickHealthSeriesForView();
    if (!healthSeries.length) {
      const empty = document.createElement("span");
      empty.className = "hp-empty";
      empty.textContent = "本场暂无血量采样（需重新生成时间线以拉取资源字段）";
      hpBars.appendChild(empty);
      return;
    }
    if (!shownHealthSeries.length) {
      const empty = document.createElement("span");
      empty.className = "hp-empty";
      empty.textContent = "当前时间窗内没有敌方血量采样";
      hpBars.appendChild(empty);
      return;
    }
    shownHealthSeries.forEach(function (series, index) {
      const item = document.createElement("div");
      item.className = "hp-item " + (series.isBoss ? "boss" : "add");
      item.dataset.seriesIndex = String(index);
      const name = document.createElement("span");
      name.className = "hp-name";
      name.textContent = series.name || ("#" + series.id);
      name.title = series.name || "";
      const bar = document.createElement("div");
      bar.className = "hp-bar";
      const fill = document.createElement("span");
      bar.appendChild(fill);
      const pct = document.createElement("span");
      pct.className = "hp-pct";
      pct.textContent = "—";
      item.appendChild(name);
      item.appendChild(bar);
      item.appendChild(pct);
      hpBars.appendChild(item);
    });
  }

  function sampleAt(series, timeMs) {
    const samples = series.samples || [];
    if (!samples.length) return null;
    let lo = 0;
    let hi = samples.length - 1;
    // 尚未开打：显示满血；已结束：定格末点
    if (timeMs < samples[0].offsetMs) return samples[0];
    if (timeMs >= samples[hi].offsetMs) return samples[hi];
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (samples[mid].offsetMs <= timeMs) lo = mid;
      else hi = mid - 1;
    }
    const left = samples[lo];
    const right = samples[lo + 1];
    if (!right || right.offsetMs === left.offsetMs) return left;
    const t = (timeMs - left.offsetMs) / (right.offsetMs - left.offsetMs);
    const pct = left.pct + (right.pct - left.pct) * t;
    let current = null;
    let maxHp = left.max != null ? left.max : right.max;
    if (left.current != null && right.current != null) {
      current = left.current + (right.current - left.current) * t;
    } else if (left.current != null) {
      current = left.current;
    }
    return { offsetMs: timeMs, pct: pct, current: current, max: maxHp };
  }

  function updateHpPanel() {
    if (!hpPanel || hpPanel.hidden || !hpBars) return;
    if (hpTime) hpTime.textContent = fmtAxis(scrubMs);
    if (!shownHealthSeries.length) return;
    hpBars.querySelectorAll(".hp-item").forEach(function (el) {
      const index = parseInt(el.dataset.seriesIndex || "-1", 10);
      const series = shownHealthSeries[index];
      const fill = el.querySelector(".hp-bar > span");
      const pctEl = el.querySelector(".hp-pct");
      if (!series || !fill || !pctEl) return;
      const sample = sampleAt(series, scrubMs);
      if (!sample) {
        fill.style.width = "0%";
        pctEl.textContent = "—";
        el.classList.add("dead");
        return;
      }
      const pct = Math.max(0, Math.min(100, Number(sample.pct) || 0));
      fill.style.width = pct.toFixed(1) + "%";
      pctEl.textContent = pct.toFixed(1) + "%";
      el.classList.toggle("dead", pct <= 0.05);
      let title = (series.name || "") + " · " + pct.toFixed(1) + "%";
      if (sample.current != null && sample.max != null) {
        title += " (" + Math.round(sample.current).toLocaleString() +
          " / " + Math.round(sample.max).toLocaleString() + ")";
      }
      el.title = title;
    });
  }

  function pointerToScrub(clientX) {
    const rect = axis.getBoundingClientRect();
    if (!rect.width) return scrubMs;
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const ratio = x / rect.width;
    return clampScrub(viewStart + ratio * viewDuration);
  }

  function applyScrubFromClientX(clientX) {
    scrubMs = pointerToScrub(clientX);
    updatePlayhead();
    updateHpPanel();
  }

  function onScrubPointerDown(e) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    scrubbing = true;
    scrubPointerId = e.pointerId;
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch (err) { /* ignore */ }
    applyScrubFromClientX(e.clientX);
    e.preventDefault();
    e.stopPropagation();
  }

  function onScrubPointerMove(e) {
    if (!scrubbing) return;
    if (scrubPointerId != null && e.pointerId !== scrubPointerId) return;
    applyScrubFromClientX(e.clientX);
    e.preventDefault();
  }

  function onScrubPointerUp(e) {
    if (scrubPointerId != null && e.pointerId !== scrubPointerId) return;
    scrubbing = false;
    scrubPointerId = null;
  }

  function bindScrubTarget(el) {
    if (!el || el.dataset.scrubBound === "1") return;
    el.dataset.scrubBound = "1";
    el.addEventListener("pointerdown", onScrubPointerDown);
    el.addEventListener("pointermove", onScrubPointerMove);
    el.addEventListener("pointerup", onScrubPointerUp);
    el.addEventListener("pointercancel", onScrubPointerUp);
  }

  function ensureScrubber() {
    board.querySelectorAll(".playhead-layer").forEach(function (n) {
      n.remove();
    });
    axis.querySelectorAll(".scrub-handle").forEach(function (n) {
      n.remove();
    });

    // 标尺上的可拖手柄（在 sticky 时间轴上层，不会被盖住）
    scrubHandleEl = document.createElement("div");
    scrubHandleEl.className = "scrub-handle";
    scrubHandleEl.title = "拖动查看该时刻血量";
    axis.appendChild(scrubHandleEl);
    bindScrubTarget(scrubHandleEl);
    bindScrubTarget(axis);

    // 贯穿泳道的蓝色指示线 + 宽命中条
    const layer = document.createElement("div");
    layer.className = "playhead-layer";
    playheadEl = document.createElement("div");
    playheadEl.className = "playhead";
    const hit = document.createElement("div");
    hit.className = "playhead-hit";
    hit.title = "拖动时间线";
    playheadEl.appendChild(hit);
    layer.appendChild(playheadEl);
    board.appendChild(layer);
    bindScrubTarget(hit);

    if (!scrubListenersBound) {
      // 捕获阶段兜底：拖出元素外仍能移动（未 setPointerCapture 时）
      window.addEventListener("pointermove", onScrubPointerMove, true);
      window.addEventListener("pointerup", onScrubPointerUp, true);
      window.addEventListener("pointercancel", onScrubPointerUp, true);
      scrubListenersBound = true;
    }
  }

  function updatePlayhead() {
    const pct = Math.max(0, Math.min(100, xPct(scrubMs)));
    const hidden =
      scrubMs < viewStart - 1 || scrubMs > viewStart + viewDuration + 1;
    if (playheadEl) {
      playheadEl.style.left = pct + "%";
      playheadEl.style.display = hidden ? "none" : "block";
    }
    if (scrubHandleEl) {
      scrubHandleEl.style.left = pct + "%";
      scrubHandleEl.style.display = hidden ? "none" : "block";
    }
  }

  function assignStackLevels(events) {
    // 贪心：按开始时间把重叠持续条放到更高层（对齐 WA 堆叠）
    const ordered = events.map(function (ev, index) {
      return {
        index: index,
        start: ev.offsetMs,
        end: ev.offsetMs + Math.max(0, ev.durationMs || 0),
      };
    }).sort(function (a, b) {
      if (a.start !== b.start) return a.start - b.start;
      return (b.end - b.start) - (a.end - a.start);
    });
    const levelEnds = [];
    const levels = new Array(events.length).fill(0);
    ordered.forEach(function (item) {
      // 瞬发（无持续）不占堆叠层
      if (item.end <= item.start + 1) {
        levels[item.index] = 0;
        return;
      }
      let level = 0;
      for (; level < levelEnds.length; level++) {
        if (levelEnds[level] <= item.start + 1) break;
      }
      if (level === levelEnds.length) levelEnds.push(item.end);
      else levelEnds[level] = item.end;
      levels[item.index] = level;
    });
    return levels;
  }

  function makeRow(player) {
    const isBoss = !!(player && player.isBoss);
    const name = (player && player.name) || "";
    const row = document.createElement("div");
    let cls = "lane-row";
    if (isBoss) {
      cls += " boss";
    } else {
      if (playerLaneIndex % 2 === 1) cls += " alt";
      playerLaneIndex += 1;
    }
    row.className = cls;
    const label = document.createElement("div");
    label.className = "lane-label";
    if (player && player.classIconUrl) {
      const icon = document.createElement("img");
      icon.className = "class-icon";
      icon.src = player.classIconUrl;
      icon.alt = player.actorClass || "";
      icon.title = player.spec || player.actorClass || "";
      icon.referrerPolicy = "no-referrer";
      icon.addEventListener("error", function () {
        icon.remove();
      });
      label.appendChild(icon);
    }
    const nameEl = document.createElement("div");
    nameEl.className = "name";
    nameEl.textContent = name;
    if (player && player.classColor) {
      nameEl.classList.add("class-tinted");
      nameEl.style.color = player.classColor;
    }
    if (player && player.spec) {
      nameEl.title = player.spec;
    }
    label.appendChild(nameEl);
    const track = document.createElement("div");
    track.className = "track";
    row.appendChild(label);
    row.appendChild(track);
    board.appendChild(row);
    return row;
  }

  function addGuide(track, offsetMs) {
    const g = document.createElement("div");
    g.className = "vguide";
    g.style.left = xPct(offsetMs) + "%";
    track.appendChild(g);
  }

  function addDefense(track, ev, stackLevel, maxStack) {
    stackLevel = stackLevel || 0;
    maxStack = maxStack || 0;
    const dur = Math.max(0, ev.durationMs || 0);
    const rawStart = ev.offsetMs;
    const rawEnd = rawStart + dur;
    const viewEnd = viewStart + viewDuration;
    const clipStart = Math.max(rawStart, viewStart);
    const clipEnd = Math.min(rawEnd, viewEnd);
    const hasBar = dur > 0 && clipEnd > clipStart + 1;

    const wrap = document.createElement("div");
    wrap.className = "player-cast" + (hasBar ? " has-duration" : " instant");
    wrap.dataset.stack = String(stackLevel);
    wrap.style.left = xPct(hasBar ? clipStart : rawStart) + "%";
    if (hasBar) {
      wrap.style.width = ((clipEnd - clipStart) / viewDuration) * 100 + "%";
    }
    // 堆叠：底层居中，更高层向上抬；重叠层加淡灰底衬
    if (maxStack > 0) {
      const step = 15;
      const laneH = 22 + (maxStack + 1) * step;
      const bottom = 4 + stackLevel * step;
      wrap.style.top = "auto";
      wrap.style.bottom = bottom + "px";
      wrap.style.transform = "none";
      if (stackLevel > 0 && hasBar) {
        const backdrop = document.createElement("div");
        backdrop.className = "effect-backdrop";
        wrap.appendChild(backdrop);
      }
      if (track.parentElement) {
        track.parentElement.style.minHeight = laneH + "px";
      }
    } else {
      wrap.style.top = "50%";
      wrap.style.transform = hasBar ? "translateY(-50%)" : "translate(-50%, -50%)";
    }

    if (hasBar) {
      const bar = document.createElement("div");
      bar.className = "effect-bar";
      wrap.appendChild(bar);
    }

    const el = document.createElement("div");
    el.className = "marker defense" + (ev.iconUrl ? " has-icon" : "");
    el.style.setProperty("--c", ev.color);
    if (!ev.iconUrl) {
      el.style.background = ev.color;
      el.textContent = shortName(ev.ability);
    } else {
      const img = document.createElement("img");
      img.src = ev.iconUrl;
      img.alt = ev.ability || "";
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      img.decoding = "async";
      img.onerror = function () {
        el.classList.remove("has-icon");
        el.style.background = ev.color;
        el.textContent = shortName(ev.ability);
        img.remove();
      };
      el.appendChild(img);
    }
    bindTip(el, ev);
    wrap.appendChild(el);
    track.appendChild(wrap);
  }

  function addBoss(track, ev) {
    const dur = Math.max(0, ev.durationMs || 0);
    const rawStart = ev.offsetMs;
    const rawEnd = rawStart + dur;
    const viewEnd = viewStart + viewDuration;
    const clipStart = Math.max(rawStart, viewStart);
    const clipEnd = Math.min(rawEnd, viewEnd);
    const hasBar = dur > 0 && clipEnd > clipStart + 1;

    const wrap = document.createElement("div");
    wrap.className = "boss-cast" + (hasBar ? " has-duration" : " instant");
    wrap.dataset.abilityKey = abilityKey(ev);
    wrap.dataset.abilityId = ev.abilityId != null ? String(ev.abilityId) : "";
    wrap.dataset.ability = ev.ability || "";
    wrap.style.left = xPct(hasBar ? clipStart : rawStart) + "%";
    if (hasBar) {
      wrap.style.width = ((clipEnd - clipStart) / viewDuration) * 100 + "%";
      const bar = document.createElement("div");
      bar.className = "cast-bar";
      wrap.appendChild(bar);
    }

    const el = document.createElement("div");
    el.className = "marker boss" + (ev.iconUrl ? " has-icon" : "");
    el.style.setProperty("--c", ev.color);
    if (ev.iconUrl) {
      const img = document.createElement("img");
      img.src = ev.iconUrl;
      img.alt = ev.ability || "";
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      img.decoding = "async";
      img.onerror = function () {
        el.classList.remove("has-icon");
        img.remove();
      };
      el.appendChild(img);
    }
    bindTip(el, ev);
    wrap.appendChild(el);
    track.appendChild(wrap);
  }

  function addPhase(track, ev) {
    const el = document.createElement("div");
    el.className = "marker phase-flag";
    el.style.left = xPct(ev.offsetMs) + "%";
    el.style.setProperty("--c", ev.color);
    const tag = document.createElement("span");
    tag.className = "phase-tag";
    tag.textContent = ev.ability;
    el.appendChild(tag);
    bindTip(el, ev);
    track.appendChild(el);
  }

  function shortName(name) {
    if (!name) return "";
    return name.length > 8 ? name.slice(0, 7) + "…" : name;
  }

  function bindTip(el, ev) {
    el.addEventListener("mouseenter", function (e) {
      tooltip.style.display = "block";
      tooltip.classList.add("boss-tip");
      tooltip.innerHTML = tipHtml(ev);
      moveTip(e);
    });
    el.addEventListener("mousemove", moveTip);
    el.addEventListener("mouseleave", function () {
      tooltip.style.display = "none";
      tooltip.classList.remove("boss-tip");
    });
  }

  function tipHtml(ev) {
    // 首领 / 玩家统一：居中图标+技能名；施法者；不展示英文名 / 类别 / 战斗时刻 / Wowhead 施法时间
    let html = "";
    if (ev.iconUrl) {
      html += '<img class="t-icon" src="' + escAttr(ev.iconUrl) + '" alt="">';
    }
    html += '<span class="t-name">' + esc(ev.ability || "（未知）") + "</span>";
    if (ev.actor) {
      html += '<div class="t-caster">施法者: ' + esc(ev.actor) + "</div>";
    }
    if (ev.durationMs && ev.durationMs > 0) {
      html += '<div class="t-duration">持续: ' +
        esc(ev.duration || fmtDuration(ev.durationMs)) + "</div>";
    }
    if (ev.target) {
      html += '<div class="t-target">目标: ' + esc(ev.target) + "</div>";
    }
    const desc = cleanTipDescription(ev);
    if (desc) {
      html += '<div class="t-desc">' + esc(desc) + "</div>";
    }
    return html;
  }

  function cleanTipDescription(ev) {
    let text = String(ev.description || "").replace(/\r/g, "").trim();
    if (!text) return "";
    const dropExact = {};
    [
      ev.ability,
      ev.abilityEn,
      ev.category,
      ev.castLabel,
      ev.durationLabel,
      "首领技能",
      "阶段",
      "瞬发",
      "Instant",
    ].forEach(function (item) {
      const key = String(item || "").trim();
      if (key) dropExact[key] = true;
    });
    const lines = text.split("\n");
    while (lines.length) {
      let line = String(lines[0] || "").trim();
      if (!line) {
        lines.shift();
        continue;
      }
      // 剥掉行首粘连的施法时间 / 瞬发
      line = line.replace(/^(?:瞬发|Instant)\s*/i, "");
      line = line.replace(/^[\d.]+\s*秒\s*施法(?:时间)?\s*/i, "");
      line = line.replace(/^[\d.]+\s*sec(?:ond)?s?\s*cast(?:\s*time)?\s*/i, "");
      line = line.trim();
      if (!line || dropExact[line]) {
        lines.shift();
        continue;
      }
      if (/^(?:瞬发|Instant)$/i.test(line)) {
        lines.shift();
        continue;
      }
      if (/^[\d.]+\s*秒\s*施法(?:时间)?$/i.test(line)) {
        lines.shift();
        continue;
      }
      if (/^[\d.]+\s*sec(?:ond)?s?\s*cast(?:\s*time)?$/i.test(line)) {
        lines.shift();
        continue;
      }
      lines[0] = line;
      break;
    }
    return lines.join("\n").trim();
  }

  function moveTip(e) {
    const x = Math.min(e.clientX + 14, window.innerWidth - 360);
    const y = Math.min(e.clientY + 14, window.innerHeight - 220);
    tooltip.style.left = x + "px";
    tooltip.style.top = y + "px";
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escAttr(s) {
    return esc(s).replace(/'/g, "&#39;");
  }

  function median(values) {
    if (!values.length) return null;
    const ordered = values.slice().sort(function (a, b) { return a - b; });
    const mid = Math.floor(ordered.length / 2);
    if (ordered.length % 2) return ordered[mid];
    return (ordered[mid - 1] + ordered[mid]) / 2;
  }

  function summarizeBossCds(events) {
    const buckets = {};
    events.forEach(function (ev) {
      if (ev.kind !== "boss") return;
      const key = String(ev.abilityId || "") + "|" + ev.ability;
      if (!buckets[key]) buckets[key] = [];
      buckets[key].push(ev);
    });
    const rows = Object.keys(buckets).map(function (key) {
      const group = buckets[key].slice().sort(function (a, b) {
        return a.offsetMs - b.offsetMs;
      });
      const timestamps = group.map(function (ev) { return ev.offsetMs; });
      const intervals = [];
      for (let i = 1; i < timestamps.length; i++) {
        intervals.push(timestamps[i] - timestamps[i - 1]);
      }
      const med = median(intervals);
      return {
        ability: group[0].ability,
        abilityEn: group[0].abilityEn || "",
        abilityId: group[0].abilityId,
        castCount: timestamps.length,
        iconUrl: (group.find(function (ev) { return ev.iconUrl; }) || {}).iconUrl || "",
        intervals: intervals.map(fmtDuration),
        median: med == null ? "—" : fmtDuration(med),
        min: intervals.length ? fmtDuration(Math.min.apply(null, intervals)) : "—",
        max: intervals.length ? fmtDuration(Math.max.apply(null, intervals)) : "—",
        times: timestamps.map(fmtFightTime),
      };
    });
    rows.sort(function (a, b) {
      if (b.castCount !== a.castCount) return b.castCount - a.castCount;
      return a.ability.localeCompare(b.ability, "zh");
    });
    return rows;
  }

  function paintCds(rows) {
    if (!rows.length) {
      cdBody.innerHTML = '<p class="cd-empty">本段没有可汇总的首领技能施法。</p>';
      return;
    }
    let html = '<table class="cd-table"><thead><tr>' +
      "<th>技能</th><th>次数</th><th>时间点</th><th>间隔</th><th>推算 CD</th><th>最短</th><th>最长</th>" +
      "</tr></thead><tbody>";
    rows.forEach(function (row) {
      const icon = row.iconUrl
        ? '<img src="' + escAttr(row.iconUrl) + '" alt="">'
        : "";
      html += "<tr>" +
        '<td><span class="cd-ability">' + icon + "<span>" + esc(row.ability) + "</span></span></td>" +
        '<td class="num">' + esc(String(row.castCount)) + "</td>" +
        "<td>" + esc((row.times || []).join(" · ") || "—") + "</td>" +
        "<td>" + esc((row.intervals || []).join(" / ") || "—") + "</td>" +
        '<td class="num">' + esc(row.median) + "</td>" +
        '<td class="num">' + esc(row.min) + "</td>" +
        '<td class="num">' + esc(row.max) + "</td>" +
        "</tr>";
    });
    html += "</tbody></table>";
    cdBody.innerHTML = html;
  }
})();
"""


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<header>
  <div class="header-top">
    <h1>__HEADLINE__</h1>
    __HOME_LINK__
  </div>
  <div class="meta">fight id __FIGHT_ID__ · __FIGHT_KIND__ · 时长 __DURATION__ · 减伤 / 药水 / 饰品泳道时间线（对照首领技能）</div>
</header>
<div class="toolbar">
  <span class="hint">时间轴含首领与小怪技能；在顶部时间标尺或蓝色滑块上拖动可查看对应时刻血量。左侧玩家名横向滚动时固定。</span>
  <div class="toolbar-options">
    <label class="opt">
      <input type="checkbox" id="opt-interrupts">
      显示打断
    </label>
  </div>
</div>
<div class="hp-panel" id="hp-panel" hidden>
  <span class="hp-hint">血量</span>
  <span class="hp-time" id="hp-time">0:00</span>
  <div class="hp-bars" id="hp-bars"></div>
</div>
<div class="boss-pull-bar" id="boss-pull-wrap" hidden>
  <span class="hint">首领战：</span>
  <div id="boss-pull-buttons"></div>
</div>
<div class="boss-ability-bar" id="boss-ability-wrap" hidden>
  <span class="hint">技能定位（旁注总次数；点击后显示第几次 / 再点下一次）：</span>
  <div id="boss-ability-buttons" class="boss-ability-buttons"></div>
</div>
<div class="board-wrap">
  <div class="board" id="board">
    <div class="axis-row">
      <div class="axis-corner" aria-hidden="true"></div>
      <div class="axis" id="axis"></div>
    </div>
  </div>
</div>
<section class="cd-section">
  <h2 id="cd-title">首领技能间隔（本场实测）</h2>
  <p class="cd-note">推算 CD 取相邻施法间隔的中位数；受阶段 / 能量 / 机制影响，未必等于技能真实冷却。大秘多首领可上方切换单个首领时间窗。点击技能按钮：跳到离当前视野最近的一次施放（平滑滚动）；再点同一按钮跳到下一次，到末次后回到第一次。</p>
  <div id="cd-body"></div>
</section>
<div id="tooltip" role="tooltip"></div>
<script>
window.TIMELINE_DATA = __DATA_JSON__;
</script>
<script>__JS__</script>
</body>
</html>
"""
