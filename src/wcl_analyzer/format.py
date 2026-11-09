from __future__ import annotations

import unicodedata
from datetime import datetime

from wcl_analyzer.analysis import summarize_bosses
from wcl_analyzer.models import (
    BossAbilityCd,
    BossSummary,
    Fight,
    FightAnalysis,
    PlayerRow,
    Report,
    TimelineAnalysis,
    TimelineEvent,
    difficulty_label,
    fight_display_name,
    fight_kind_label,
    localized_encounter_name,
)
def format_report(report: Report) -> str:
    lines = [
        f"{report.title}  [{report.code}]",
        _meta_line(report),
        "",
        _table(
            ["首领", "难度", "尝试", "击杀", "最快击杀", "最佳灭团进度"],
            [_boss_cells(summary) for summary in summarize_bosses(report)],
            aligns=["left", "left", "right", "right", "right", "left"],
        ),
    ]
    if not report.boss_fights:
        lines.append("这份报告里没有已结束的首领战斗。")
    return "\n".join(lines)


def format_pulls(report: Report) -> str:
    """列出可分析的首领 / 大秘境 pull（fight id）。"""
    lines = [
        f"{report.title}  [{report.code}]",
        _meta_line(report),
        "",
        "一场 pull = 一个 fight id。分析时用 --fight / --pull 或链接里的 fight=N。",
        "注意：报告 zone 可能是团本，但列表里仍会单独标出大秘境钥石场次。",
        "链接请加引号（zsh 会把未加引号的 ? 与 & 弄坏）。",
        "",
    ]
    bosses = report.boss_fights
    if not bosses:
        lines.append("这份报告里没有已结束的首领战斗。")
        return "\n".join(lines)
    rows = [_pull_cells(fight) for fight in bosses]
    lines.append(
        _table(
            ["编号", "类型", "名称", "难度", "结果", "时长"],
            rows,
            aligns=["right", "left", "left", "left", "left", "right"],
        )
    )
    return "\n".join(lines)


def format_fight(analysis: FightAnalysis) -> str:
    fight = analysis.fight
    lines = [
        _fight_headline(fight),
        f"死亡 {len(analysis.deaths)}",
    ]
    if analysis.deaths:
        for death in analysis.deaths:
            cause = f"  {death.ability}" if death.ability else ""
            lines.append(f"  {format_duration(death.offset_ms)}  {death.name}  {death.spec}{cause}")
    else:
        lines.append("  无")

    lines.extend(["", "伤害"])
    lines.append(_player_table(analysis.damage, "DPS", show_overheal=False))
    lines.extend(["", "治疗"])
    lines.append(_player_table(analysis.healing, "HPS", show_overheal=True))
    lines.extend(["", "承受伤害"])
    lines.append(_player_table(analysis.damage_taken, "DTPS", show_overheal=False))
    return "\n".join(lines)


def format_duration(milliseconds: float | None) -> str:
    if milliseconds is None:
        return "—"
    total_seconds = max(0, int(round(milliseconds / 1000.0)))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_fight_time(milliseconds: float | None) -> str:
    """战斗相对时间，精确到毫秒：m:ss.mmm"""
    if milliseconds is None:
        return "—"
    total_ms = max(0, int(milliseconds))
    minutes, rem = divmod(total_ms, 60_000)
    seconds, ms = divmod(rem, 1000)
    return f"{minutes}:{seconds:02d}.{ms:03d}"


def format_timeline(analysis: TimelineAnalysis) -> str:
    fight = analysis.fight
    lines = [
        _fight_headline(fight),
        (
            f"fight id {fight.id}  ·  {fight_kind_label(fight)}  ·  "
            "减伤 / 药水时间线（含首领技能）"
        ),
        "",
    ]
    if not analysis.events:
        lines.append("  无匹配事件。")
        return "\n".join(lines)
    rows = [_timeline_cells(event) for event in analysis.events]
    lines.append(
        _table(
            ["时间", "类型", "类别", "玩家/首领", "专精", "技能"],
            rows,
            aligns=["right", "left", "left", "left", "left", "left"],
        )
    )
    cd_block = format_boss_cds(analysis.boss_cds)
    if cd_block:
        lines.extend(["", cd_block])
    return "\n".join(lines)


def format_boss_cds(summaries: tuple[BossAbilityCd, ...] | list[BossAbilityCd]) -> str:
    if not summaries:
        return ""
    lines = [
        "首领技能间隔（本场实测，推算 CD ≠ 必然真实冷却）",
        "",
        _table(
            ["技能", "次数", "间隔", "推算 CD（中位）", "最短", "最长"],
            [_boss_cd_cells(item) for item in summaries],
            aligns=["left", "right", "left", "right", "right", "right"],
        ),
    ]
    return "\n".join(lines)


def _timeline_cells(event: TimelineEvent) -> list[str]:
    kind_label = {"boss": "首领", "defense": "减伤", "phase": "阶段"}.get(event.kind, event.kind)
    ability = event.ability
    if event.ability_en and event.ability_en != event.ability:
        ability = f"{event.ability} ({event.ability_en})"
    return [
        format_fight_time(event.offset_ms),
        kind_label,
        event.category or "—",
        event.actor or "—",
        event.spec or "—",
        ability,
    ]


def _pull_cells(fight: Fight) -> list[str]:
    if fight.kill:
        result = "击杀"
    elif fight.boss_percentage is not None:
        result = f"灭团 {fight.boss_percentage:.1f}%"
    else:
        result = "灭团"
    return [
        str(fight.id),
        fight_kind_label(fight),
        fight_display_name(fight),
        difficulty_label(fight.difficulty, fight.keystone_level),
        result,
        format_duration(fight.duration_ms),
    ]


def _boss_cd_cells(item: BossAbilityCd) -> list[str]:
    if not item.intervals_ms:
        interval_text = "—"
    else:
        interval_text = " / ".join(format_duration(value) for value in item.intervals_ms[:6])
        if len(item.intervals_ms) > 6:
            interval_text += " …"
    return [
        item.ability,
        str(item.cast_count),
        interval_text,
        format_duration(item.median_interval_ms) if item.median_interval_ms is not None else "—",
        format_duration(item.min_interval_ms) if item.min_interval_ms is not None else "—",
        format_duration(item.max_interval_ms) if item.max_interval_ms is not None else "—",
    ]



def format_amount(value: float) -> str:
    sign = "-" if value < 0 else ""
    number = abs(value)
    if number >= 100_000_000:
        return f"{sign}{number / 100_000_000:.2f}亿"
    if number >= 10_000:
        return f"{sign}{number / 10_000:.1f}万"
    return f"{sign}{number:.0f}"


def format_rate(value: float) -> str:
    return f"{format_amount(value)}/秒"


def _meta_line(report: Report) -> str:
    parts = []
    if report.zone_name:
        parts.append(report.zone_name)
    if report.owner:
        parts.append(f"上传者 {report.owner}")
    if report.start_time:
        start = datetime.fromtimestamp(report.start_time / 1000.0)
        end = datetime.fromtimestamp(report.end_time / 1000.0)
        parts.append(f"{start:%Y-%m-%d %H:%M} – {end:%H:%M}")
    return "  ".join(parts)


def _boss_cells(summary: BossSummary) -> list[str]:
    return [
        localized_encounter_name(summary.name),
        difficulty_label(summary.difficulty, summary.keystone_level),
        str(summary.attempts),
        str(summary.kills),
        format_duration(summary.fastest_kill_ms),
        _wipe_text(summary.best_wipe),
    ]


def _wipe_text(fight: Fight | None) -> str:
    if fight is None:
        return "—"
    pieces = []
    if fight.fight_percentage is not None:
        pieces.append(f"完成度 {fight.fight_percentage:.1f}%")
    if fight.boss_percentage is not None:
        pieces.append(f"剩余血量 {fight.boss_percentage:.1f}%")
    return " / ".join(pieces) if pieces else "灭团"


def _fight_headline(fight: Fight) -> str:
    result = "击杀" if fight.kill else "灭团"
    if not fight.kill and fight.boss_percentage is not None:
        result = f"灭团 {fight.boss_percentage:.1f}%"
    bits = [
        difficulty_label(fight.difficulty, fight.keystone_level),
        fight_display_name(fight),
        result,
        format_duration(fight.duration_ms),
    ]
    if fight.size:
        bits.append(f"{fight.size}人")
    if fight.average_item_level:
        bits.append(f"装等 {fight.average_item_level:.1f}")
    if fight.last_phase:
        bits.append(f"阶段 {fight.last_phase}")
    return "  ".join(bits)


def _player_table(rows: tuple[PlayerRow, ...], rate_name: str, show_overheal: bool) -> str:
    if not rows:
        return "  无玩家数据"
    headers = ["#", "玩家", "专精", "总量", rate_name, "主要技能"]
    aligns = ["right", "left", "left", "right", "right", "left"]
    cells = []
    for index, row in enumerate(rows, start=1):
        record = [
            str(index),
            row.name,
            row.spec,
            format_amount(row.total),
            format_rate(row.per_second),
            row.top_ability or "—",
        ]
        if show_overheal:
            record.insert(5, f"{row.overheal_percent:.0f}%" if row.overheal_percent is not None else "—")
        cells.append(record)
    if show_overheal:
        headers.insert(5, "过量")
        aligns.insert(5, "right")
    return _table(headers, cells, aligns)


def _table(headers: list[str], rows: list[list[str]], aligns: list[str]) -> str:
    if not rows:
        return "  无"
    widths = [_width(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], _width(cell))
    rendered = [_render_row(headers, widths, aligns)]
    rendered.extend(_render_row(row, widths, aligns) for row in rows)
    return "\n".join(rendered)


def _render_row(cells: list[str], widths: list[int], aligns: list[str]) -> str:
    padded = []
    for cell, width, align in zip(cells, widths, aligns):
        gap = max(0, width - _width(cell))
        padded.append((" " * gap + cell) if align == "right" else (cell + " " * gap))
    return "  ".join(padded)


def _width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width
