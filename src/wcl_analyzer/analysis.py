from __future__ import annotations

from collections import OrderedDict
from typing import Any

from wcl_analyzer.models import (
    BossSummary,
    DeathEvent,
    Fight,
    FightAnalysis,
    PlayerRow,
    Report,
    is_player,
    spec_label,
)


def summarize_bosses(report: Report) -> tuple[BossSummary, ...]:
    groups: OrderedDict[tuple[int, int | None, str], list[Fight]] = OrderedDict()
    for fight in report.boss_fights:
        key = (fight.encounter_id, fight.difficulty, fight.name)
        groups.setdefault(key, []).append(fight)

    summaries: list[BossSummary] = []
    for (encounter_id, difficulty, name), fights in groups.items():
        kills = [fight for fight in fights if fight.kill]
        keystone = next((fight.keystone_level for fight in fights if fight.keystone_level), None)
        fastest = min((fight.duration_ms for fight in kills), default=None)
        summaries.append(
            BossSummary(
                name=name,
                encounter_id=encounter_id,
                difficulty=difficulty,
                keystone_level=keystone,
                attempts=len(fights),
                kills=len(kills),
                fastest_kill_ms=fastest,
                best_wipe=_best_wipe(fights),
                fights=tuple(fights),
            )
        )
    return tuple(summaries)


def analyze_fight(fight: Fight, tables: dict[str, Any]) -> FightAnalysis:
    duration_ms = fight.duration_ms or _table_time(tables.get("damageDone"))
    return FightAnalysis(
        fight=fight,
        damage=_player_rows(tables.get("damageDone"), duration_ms),
        healing=_player_rows(tables.get("healing"), duration_ms, include_overheal=True),
        damage_taken=_player_rows(tables.get("damageTaken"), duration_ms),
        deaths=_deaths(tables.get("deaths"), fight),
    )


def select_fight(report: Report, fight_token: str | None) -> Fight:
    """选择要分析的战斗。

    - 未指定：取最后一次**首领击杀**（含钥石大秘整场）；无击杀则取最后一场首领。
    - ``last``：最后一场已结束的首领/钥石战斗（含灭团）。
    - 数字 id：精确匹配该 fight；**显式指定时不再要求是首领**
      （大秘整场、地下城 boss、甚至小怪 pull 均可），仅拒绝仍在上传的战斗。
      链接 / ``--fight`` / ``--pull`` 给出的编号绝不会被悄悄替换成其它击杀。
    """
    bosses = report.boss_fights
    if fight_token is None:
        if not bosses:
            raise ValueError("这份报告里没有已结束的首领战斗。")
        kills = [fight for fight in bosses if fight.kill]
        return kills[-1] if kills else bosses[-1]
    if fight_token == "last":
        if not bosses:
            raise ValueError("这份报告里没有已结束的首领战斗。")
        return bosses[-1]
    if not fight_token.isdigit():
        raise ValueError(
            f"无法识别的战斗编号：{fight_token}。"
            "一场 pull = 一个 fight id，可用 --list-pulls 查看。"
        )
    fight_id = int(fight_token)
    for fight in report.fights:
        if fight.id == fight_id:
            if fight.in_progress:
                raise ValueError(f"战斗 {fight_id} 仍在上传，还不能分析。")
            return fight
    raise ValueError(
        f"报告里没有编号为 {fight_id} 的战斗。"
        "一场 pull = 一个 fight id，可用 `wcl report 报告 --list-pulls` 或 "
        "`wcl timeline 报告 --list-pulls` 查看列表。"
    )


def resolve_fight_token(
    *,
    fight: str | None = None,
    pull: str | None = None,
    ref_fight: str | None = None,
) -> str | None:
    """合并 --fight / --pull / URL 中的 fight。

    优先级：``--fight`` / ``--pull``（须一致）> 链接里的 ``#fight=`` / ``?fight=``。
    都未给出时返回 ``None``（由 ``select_fight`` 取最后一次击杀）。
    """
    if fight and pull and fight != pull:
        raise ValueError(f"--fight ({fight}) 与 --pull ({pull}) 不能指向不同编号。")
    cli_token = fight or pull
    if cli_token:
        return cli_token
    return ref_fight


def _best_wipe(fights: list[Fight]) -> Fight | None:
    wipes = [fight for fight in fights if not fight.kill]
    if not wipes:
        return None
    return max(wipes, key=_wipe_progress)


def _wipe_progress(fight: Fight) -> tuple[int, float]:
    if fight.fight_percentage is not None:
        return (1, fight.fight_percentage)
    if fight.boss_percentage is not None:
        return (0, 100.0 - fight.boss_percentage)
    return (-1, 0.0)


def _player_rows(
    table: Any,
    duration_ms: float,
    include_overheal: bool = False,
) -> tuple[PlayerRow, ...]:
    rows: list[PlayerRow] = []
    seconds = duration_ms / 1000.0 if duration_ms else 0.0
    for entry in _entries(table):
        if not is_player(entry):
            continue
        total = int(entry.get("total") or 0)
        active_ms = float(entry.get("activeTime") or 0)
        active = total / (active_ms / 1000.0) if active_ms else None
        overheal = None
        if include_overheal:
            overheal = _overheal_percent(total, int(entry.get("overheal") or 0))
        rows.append(
            PlayerRow(
                name=entry.get("name") or "未知",
                spec=spec_label(entry.get("icon"), entry.get("type")),
                total=total,
                per_second=total / seconds if seconds else 0.0,
                active_per_second=active,
                overheal_percent=overheal,
                top_ability=_top_ability(entry),
            )
        )
    rows.sort(key=lambda row: row.total, reverse=True)
    return tuple(rows)


def _deaths(table: Any, fight: Fight) -> tuple[DeathEvent, ...]:
    events: list[DeathEvent] = []
    for entry in _entries(table):
        if not is_player(entry):
            continue
        moment = entry.get("deathTime", entry.get("timestamp"))
        offset = float(moment) - fight.start_time if moment is not None else 0.0
        ability = entry.get("ability") or {}
        events.append(
            DeathEvent(
                name=entry.get("name") or "未知",
                spec=spec_label(entry.get("icon"), entry.get("type")),
                offset_ms=max(0.0, offset),
                ability=ability.get("name") if isinstance(ability, dict) else None,
            )
        )
    events.sort(key=lambda event: event.offset_ms)
    return tuple(events)


def _entries(table: Any) -> list[dict]:
    if not isinstance(table, dict):
        return []
    if isinstance(table.get("entries"), list):
        return table["entries"]
    data = table.get("data")
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return data["entries"]
    return []


def _table_time(table: Any) -> float:
    if not isinstance(table, dict):
        return 0.0
    if table.get("totalTime"):
        return float(table["totalTime"])
    data = table.get("data")
    if isinstance(data, dict) and data.get("totalTime"):
        return float(data["totalTime"])
    return 0.0


def _top_ability(entry: dict) -> str | None:
    abilities = entry.get("abilities") or []
    ranked = sorted(
        (item for item in abilities if isinstance(item, dict)),
        key=lambda item: int(item.get("total") or 0),
        reverse=True,
    )
    if not ranked:
        return None
    return ranked[0].get("name")


def _overheal_percent(total: int, overheal: int) -> float | None:
    raw = total + overheal
    if raw <= 0:
        return None
    return overheal / raw * 100.0
