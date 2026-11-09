"""首领技能与防御技能时间线分析。"""

from __future__ import annotations

from typing import Any

from wcl_analyzer.defenses import (
    DefenseCategory,
    build_ability_id_filter,
    category_label,
    is_ignored_boss_ability,
    lookup_defense,
    parse_category,
)
from wcl_analyzer.models import (
    ActorInfo,
    DungeonPull,
    Fight,
    HealthSample,
    HealthSeries,
    TimelineAnalysis,
    TimelineEvent,
    short_encounter_name,
    spec_label,
)
from wcl_analyzer.spell_meta import summarize_boss_cds

# 敌方血量采样：同一单位 hitPoints 未变时的最小记录间隔；每单位上限
_HEALTH_MIN_GAP_MS = 400.0
_HEALTH_MAX_SAMPLES = 240
# 写入 HTML 时再抽稀，避免 TIMELINE_DATA 过大拖垮页面
_HEALTH_PAYLOAD_MAX_SAMPLES = 120
_HEALTH_PAYLOAD_MAX_SERIES = 40
# 每个首领时间窗至少保留若干条重叠序列，避免后期 boss 被前 40 条挤掉
_HEALTH_PAYLOAD_PER_WINDOW = 6


def analyze_timeline(
    fight: Fight,
    *,
    actors: tuple[ActorInfo, ...] | list[ActorInfo],
    abilities: dict[int, str],
    defense_events: list[dict[str, Any]],
    boss_events: list[dict[str, Any]],
    health_events: list[dict[str, Any]] | None = None,
    player: str | None = None,
    category: str | DefenseCategory | None = None,
) -> TimelineAnalysis:
    actors_by_id = {actor.id: actor for actor in actors}
    category_filter = _resolve_category(category)
    player_filter = player.casefold() if player else None

    events: list[TimelineEvent] = []
    events.extend(_phase_events(fight))
    events.extend(
        _boss_cast_events(fight, boss_events, actors_by_id, abilities)
    )
    events.extend(
        _defense_cast_events(
            fight,
            defense_events,
            actors_by_id,
            abilities,
            player_filter=player_filter,
            category_filter=category_filter,
        )
    )
    events.sort(key=lambda item: (item.offset_ms, _kind_order(item.kind), item.ability))
    event_tuple = tuple(events)
    health_series = build_health_series(
        fight,
        health_events or [],
        actors_by_id,
    )
    return TimelineAnalysis(
        fight=fight,
        events=event_tuple,
        boss_cds=summarize_boss_cds(event_tuple),
        health_series=health_series,
    )


def fetch_timeline_inputs(client: Any, code: str, fight: Fight) -> dict[str, Any]:
    """通过客户端拉取时间线所需的 master data 与事件。"""
    master = client.get_master_data(code)
    defense_filter = build_ability_id_filter()
    defense_events = client.get_events(
        code,
        fight,
        data_type="Casts",
        filter_expression=defense_filter,
    )
    # 部分药水 / 光环可能只有 applybuff，补抓同 ID 的 Buffs 并去重
    buff_events = client.get_events(
        code,
        fight,
        data_type="Buffs",
        filter_expression=defense_filter,
    )
    defense_events = _merge_unique_events(
        defense_events,
        [event for event in buff_events if event.get("type") == "applybuff"],
    )
    boss_events = client.get_events(
        code,
        fight,
        data_type="Casts",
        hostility_type="Enemies",
    )
    # 友方 DamageDone + includeResources：目标（首领/小怪）带 hitPoints/maxHitPoints
    # 注意：WCL 默认不返回资源字段，不设 includeResources 时血量序列会为空
    health_events = client.get_events(
        code,
        fight,
        data_type="DamageDone",
        hostility_type="Friendlies",
        include_resources=True,
    )
    return {
        "actors": master["actors"],
        "abilities": master["abilities"],
        "ability_icons": master.get("ability_icons") or {},
        "defense_events": defense_events,
        "boss_events": boss_events,
        "health_events": health_events,
    }


def _dungeon_boss_name_keys(fight: Fight) -> set[str]:
    """大秘 dungeonPull 首领名（含中英短名），用于把未标 Boss 子类的首领算进 is_boss。"""
    keys: set[str] = set()
    for pull in fight.dungeon_pulls:
        if not pull.is_boss or not pull.name:
            continue
        keys.add(pull.name.casefold())
        keys.add(short_encounter_name(pull.name).casefold())
    return keys


def build_health_series(
    fight: Fight,
    raw_events: list[dict[str, Any]],
    actors_by_id: dict[int, ActorInfo],
) -> tuple[HealthSeries, ...]:
    """从伤害事件采样敌方（首领 + 小怪）血量百分比时间序列。"""
    buckets: dict[tuple[int, int], list[HealthSample]] = {}
    meta: dict[tuple[int, int], tuple[str, bool]] = {}
    dungeon_boss_keys = _dungeon_boss_name_keys(fight)

    for raw in raw_events:
        parsed = _parse_health_point(raw, fight, actors_by_id)
        if parsed is None:
            continue
        key, name, is_boss, sample = parsed
        if not is_boss and dungeon_boss_keys:
            name_key = name.casefold()
            short_key = short_encounter_name(name).casefold()
            if name_key in dungeon_boss_keys or short_key in dungeon_boss_keys:
                is_boss = True
        meta[key] = (name, is_boss)
        series = buckets.setdefault(key, [])
        if series:
            prev = series[-1]
            same_hp = (
                prev.current is not None
                and sample.current is not None
                and abs(prev.current - sample.current) < 0.5
                and abs(prev.pct - sample.pct) < 0.05
            )
            if same_hp and sample.offset_ms - prev.offset_ms < _HEALTH_MIN_GAP_MS:
                continue
            if same_hp and abs(sample.pct - prev.pct) < 0.05:
                # 血量未变：仅刷新末点时间，避免冗余点
                series[-1] = HealthSample(
                    offset_ms=sample.offset_ms,
                    pct=prev.pct,
                    current=prev.current,
                    max_hp=prev.max_hp,
                )
                continue
        series.append(sample)
        if len(series) > _HEALTH_MAX_SAMPLES:
            # 均匀抽稀到上限一半，再继续追加
            buckets[key] = _downsample_samples(series, _HEALTH_MAX_SAMPLES // 2)

    items: list[HealthSeries] = []
    for key, samples in buckets.items():
        if not samples:
            continue
        actor_id, instance = key
        name, is_boss = meta[key]
        localized = short_encounter_name(name)
        display = localized if instance <= 1 else f"{localized} #{instance}"
        items.append(
            HealthSeries(
                id=actor_id,
                name=display,
                is_boss=is_boss,
                instance=instance,
                samples=tuple(samples),
            )
        )

    items.sort(
        key=lambda item: (
            0 if item.is_boss else 1,
            -len(item.samples),
            item.name.casefold(),
            item.instance,
            item.id,
        )
    )
    return tuple(items)


def _series_time_span(item: HealthSeries) -> tuple[float, float] | None:
    if not item.samples:
        return None
    return item.samples[0].offset_ms, item.samples[-1].offset_ms


def _series_overlaps_window(
    item: HealthSeries, start_ms: float, end_ms: float
) -> bool:
    span = _series_time_span(item)
    if span is None:
        return False
    return span[0] <= end_ms + 1.0 and span[1] >= start_ms - 1.0


def _select_health_series_for_payload(
    series: tuple[HealthSeries, ...] | list[HealthSeries],
    windows: list[tuple[float, float]] | tuple[tuple[float, float], ...] | None,
    *,
    max_series: int = _HEALTH_PAYLOAD_MAX_SERIES,
    per_window: int = _HEALTH_PAYLOAD_PER_WINDOW,
) -> list[HealthSeries]:
    """优先保留首领，并为每个时间窗保留重叠序列，再按采样数填满限额。

    大秘多首领场次里，早期小怪采样点极多，若直接截前 N 条，后期首领窗会整段落空，
    页面就会显示「当前时间窗内没有敌方血量采样」。
    """
    items = [item for item in series if item.samples]
    if not items:
        return []

    selected: list[HealthSeries] = []
    selected_keys: set[tuple[int, int]] = set()

    def _key(item: HealthSeries) -> tuple[int, int]:
        return item.id, item.instance

    def _add(item: HealthSeries) -> None:
        key = _key(item)
        if key in selected_keys or len(selected) >= max_series:
            return
        selected_keys.add(key)
        selected.append(item)

    for item in items:
        if item.is_boss:
            _add(item)

    for start_ms, end_ms in windows or ():
        overlapping = [
            item for item in items if _series_overlaps_window(item, start_ms, end_ms)
        ]
        overlapping.sort(
            key=lambda item: (
                0 if item.is_boss else 1,
                -len(item.samples),
                item.name.casefold(),
                item.instance,
                item.id,
            )
        )
        for item in overlapping[:per_window]:
            _add(item)

    for item in items:
        if len(selected) >= max_series:
            break
        _add(item)

    return selected


def health_series_payload(
    series: tuple[HealthSeries, ...] | list[HealthSeries],
    windows: list[tuple[float, float]] | tuple[tuple[float, float], ...] | None = None,
) -> list[dict[str, Any]]:
    """HTML / JSON 用的血量序列（限制条数与采样点，保证拖动时页面可响应）。

    windows: 可选的战斗相对时间窗（通常是首领 pull）。传入后会保证每个窗都有覆盖。
    """
    trimmed = _select_health_series_for_payload(series, windows)
    payload: list[dict[str, Any]] = []
    for item in trimmed:
        samples = list(item.samples)
        if len(samples) > _HEALTH_PAYLOAD_MAX_SAMPLES:
            samples = _downsample_samples(samples, _HEALTH_PAYLOAD_MAX_SAMPLES)
        payload.append(
            {
                "id": item.id,
                "name": item.name,
                "isBoss": item.is_boss,
                "instance": item.instance,
                "samples": [
                    {
                        "offsetMs": sample.offset_ms,
                        "pct": round(sample.pct, 2),
                        "current": sample.current,
                        "max": sample.max_hp,
                    }
                    for sample in samples
                ],
            }
        )
    return payload


def boss_dungeon_pulls(fight: Fight) -> tuple[DungeonPull, ...]:
    """本场内的首领 dungeonPull（跳过小怪 pull）。"""
    return tuple(pull for pull in fight.dungeon_pulls if pull.is_boss)


def infer_boss_pulls_from_events(
    fight: Fight,
    events: tuple[TimelineEvent, ...] | list[TimelineEvent],
) -> tuple[DungeonPull, ...]:
    """当 API 没有 dungeonPulls 时，按首领施法者聚类推断时间窗（至少 2 个首领才有意义）。

    小怪技能也会画在首领轴上，但推断 pull 时忽略（category=小怪），避免把增援拆成假首领段。
    """
    by_actor: dict[str, list[float]] = {}
    for event in events:
        if event.kind != "boss" or not event.actor:
            continue
        if event.category == "小怪":
            continue
        by_actor.setdefault(event.actor, []).append(event.offset_ms)
    if len(by_actor) < 2:
        return ()

    ordered = sorted(by_actor.items(), key=lambda item: min(item[1]))
    segments: list[DungeonPull] = []
    for index, (name, offsets) in enumerate(ordered):
        first = min(offsets)
        last = max(offsets)
        next_start = min(ordered[index + 1][1]) if index + 1 < len(ordered) else None
        start_offset = max(0.0, first - 2_000.0)
        if next_start is not None:
            end_offset = min(last + 5_000.0, max(last, (last + next_start) / 2.0))
        else:
            end_offset = min(fight.duration_ms, last + 5_000.0)
        if end_offset <= start_offset:
            end_offset = min(fight.duration_ms, start_offset + 1_000.0)
        segments.append(
            DungeonPull(
                id=-(index + 1),
                name=name,
                encounter_id=0,
                start_time=fight.start_time + start_offset,
                end_time=fight.start_time + end_offset,
                kill=None,
            )
        )
    return tuple(segments)


def resolve_boss_pulls(
    fight: Fight,
    events: tuple[TimelineEvent, ...] | list[TimelineEvent] | None = None,
) -> tuple[DungeonPull, ...]:
    """优先 dungeonPulls；否则用首领施法聚类回退。少于 2 段则返回空（页面隐藏控件）。"""
    pulls = boss_dungeon_pulls(fight)
    if len(pulls) >= 2:
        return pulls
    if events is None:
        return ()
    inferred = infer_boss_pulls_from_events(fight, events)
    return inferred if len(inferred) >= 2 else ()


def pull_offsets(fight: Fight, pull: DungeonPull) -> tuple[float, float]:
    """把 pull 的报告相对时间转成战斗相对 offset（毫秒）。"""
    start = max(0.0, pull.start_time - fight.start_time)
    end = max(start, pull.end_time - fight.start_time)
    end = min(end, fight.duration_ms) if fight.duration_ms else end
    return start, end


def filter_events_by_window(
    events: tuple[TimelineEvent, ...] | list[TimelineEvent],
    start_offset_ms: float,
    end_offset_ms: float,
) -> tuple[TimelineEvent, ...]:
    """保留与 [start, end] 有重叠的事件（含端点；带 duration 的施法条按区间相交）。"""
    kept: list[TimelineEvent] = []
    for event in events:
        event_start = event.offset_ms
        event_end = event.offset_ms + max(0.0, event.duration_ms)
        if event_end < start_offset_ms or event_start > end_offset_ms:
            continue
        kept.append(event)
    return tuple(kept)


def boss_pull_payload_items(
    fight: Fight,
    events: tuple[TimelineEvent, ...] | list[TimelineEvent] | None = None,
) -> list[dict[str, float | int | str | bool | None]]:
    """HTML / JSON 用的首领段列表（战斗相对时间）。"""
    items: list[dict[str, float | int | str | bool | None]] = []
    for pull in resolve_boss_pulls(fight, events):
        start, end = pull_offsets(fight, pull)
        items.append(
            {
                "id": pull.id,
                "name": pull.name,
                "label": short_encounter_name(pull.name),
                "encounterId": pull.encounter_id,
                "startOffsetMs": start,
                "endOffsetMs": end,
                "kill": pull.kill,
            }
        )
    return items


def _resolve_category(category: str | DefenseCategory | None) -> DefenseCategory | None:
    if category is None:
        return None
    if isinstance(category, DefenseCategory):
        return category
    return parse_category(category)


def _phase_events(fight: Fight) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for phase in fight.phase_transitions:
        offset = max(0.0, phase.start_time - fight.start_time)
        events.append(
            TimelineEvent(
                offset_ms=offset,
                kind="phase",
                ability=f"阶段 {phase.id}",
                ability_id=None,
                category=None,
                actor=None,
                spec=None,
            )
        )
    return events


# begincast 与完成 cast 的最大配对窗口（毫秒）；超时视为打断 / 未完成
_BOSS_CAST_MATCH_WINDOW_MS = 60_000.0
# 同名相关施法（不同 spell id，如利斧投掷 cast + channel）去重窗口
_BOSS_SAME_NAME_DEDUPE_MS = 250.0


def _boss_cast_events(
    fight: Fight,
    raw_events: list[dict[str, Any]],
    actors_by_id: dict[int, ActorInfo],
    abilities: dict[int, str],
) -> list[TimelineEvent]:
    candidates: list[tuple[dict[str, Any], ActorInfo | None, int | None, str]] = []
    for raw in raw_events:
        # WowAnalyzer EnemyCasts：保留 begincast + cast，再配对成一条带时长的施法
        if raw.get("type") not in {None, "cast", "begincast"}:
            continue
        spell_id = _ability_id(raw)
        ability_name = _ability_name(raw, abilities)
        if is_ignored_boss_ability(spell_id, ability_name):
            continue
        source = _resolve_actor(raw.get("sourceID"), actors_by_id, prefer_owner=False)
        if source is not None and (source.is_player or source.is_pet):
            continue
        candidates.append((raw, source, spell_id, ability_name))

    # 多首领 / 小怪增援：敌方非玩家施法一律上「首领」轴（含 Boss 与 add）
    # 仍忽略近战平 A；玩家与宠物已在上面剔除
    selected = [
        item
        for item in candidates
        if _is_enemy_cast_source(item[1])
    ]
    if not selected:
        selected = candidates
    merged = _merge_boss_begincast_casts(fight, selected, actors_by_id)
    return _dedupe_boss_cast_events(merged)


def _merge_boss_begincast_casts(
    fight: Fight,
    selected: list[tuple[dict[str, Any], ActorInfo | None, int | None, str]],
    actors_by_id: dict[int, ActorInfo],
) -> list[TimelineEvent]:
    """把同一 source+ability 的 begincast→cast 合并为一条带 duration 的事件。"""
    ordered = sorted(
        selected,
        key=lambda item: (
            _offset_ms(item[0], fight),
            0 if (item[0].get("type") or "cast") == "begincast" else 1,
            item[2] or 0,
        ),
    )
    # 待配对的 begincast：key = (sourceID, abilityGameID)
    pending: dict[
        tuple[int | None, int | None],
        list[tuple[dict[str, Any], ActorInfo | None, int | None, str, float]],
    ] = {}
    events: list[TimelineEvent] = []

    for raw, source, spell_id, ability_name in ordered:
        event_type = raw.get("type") or "cast"
        source_id = _source_id(raw)
        key = (source_id, spell_id)
        offset = _offset_ms(raw, fight)
        actor_name = _source_name(source, raw)

        if event_type == "begincast":
            pending.setdefault(key, []).append(
                (raw, source, spell_id, ability_name, offset)
            )
            continue

        # cast：优先匹配尚未超时的 begincast
        queue = pending.get(key) or []
        matched_begin: tuple[dict[str, Any], ActorInfo | None, int | None, str, float] | None = None
        while queue:
            candidate = queue[0]
            begin_offset = candidate[4]
            if offset - begin_offset > _BOSS_CAST_MATCH_WINDOW_MS:
                # 超时未完成 → 作为打断 / 仅开始的施法留下
                stale = queue.pop(0)
                events.append(
                    _make_boss_event(
                        raw=stale[0],
                        spell_id=stale[2],
                        ability_name=stale[3],
                        actors_by_id=actors_by_id,
                        offset_ms=stale[4],
                        duration_ms=0.0,
                        target_raw=stale[0],
                        actor_name=_source_name(stale[1], stale[0]),
                        category=_boss_event_category(stale[1], fight),
                    )
                )
                continue
            if offset + 1.0 < begin_offset:
                break
            matched_begin = queue.pop(0)
            break

        if matched_begin is not None:
            begin_raw, begin_source, begin_spell_id, begin_name, begin_offset = matched_begin
            events.append(
                _make_boss_event(
                    raw=begin_raw,
                    spell_id=begin_spell_id,
                    ability_name=begin_name,
                    actors_by_id=actors_by_id,
                    offset_ms=begin_offset,
                    duration_ms=max(0.0, offset - begin_offset),
                    target_raw=raw,
                    actor_name=_source_name(begin_source, begin_raw),
                    category=_boss_event_category(begin_source, fight),
                )
            )
            continue

        events.append(
            _make_boss_event(
                raw=raw,
                spell_id=spell_id,
                ability_name=ability_name,
                actors_by_id=actors_by_id,
                offset_ms=offset,
                duration_ms=_raw_duration_ms(raw),
                target_raw=raw,
                actor_name=actor_name,
                category=_boss_event_category(source, fight),
            )
        )

    # 战斗结束仍未配对的 begincast（打断 / 日志截断）
    for queue in pending.values():
        for begin_raw, begin_source, begin_spell_id, begin_name, begin_offset in queue:
            events.append(
                _make_boss_event(
                    raw=begin_raw,
                    spell_id=begin_spell_id,
                    ability_name=begin_name,
                    actors_by_id=actors_by_id,
                    offset_ms=begin_offset,
                    duration_ms=0.0,
                    target_raw=begin_raw,
                    actor_name=_source_name(begin_source, begin_raw),
                    category=_boss_event_category(begin_source, fight),
                )
            )
    return events


def _make_boss_event(
    *,
    raw: dict[str, Any],
    spell_id: int | None,
    ability_name: str,
    actors_by_id: dict[int, ActorInfo],
    offset_ms: float,
    duration_ms: float,
    target_raw: dict[str, Any],
    actor_name: str | None,
    category: str | None = None,
) -> TimelineEvent:
    target_name = _resolve_target_name(
        target_raw,
        actors_by_id,
        source_id=raw.get("sourceID"),
        source_name=actor_name,
    )
    return TimelineEvent(
        offset_ms=offset_ms,
        kind="boss",
        ability=ability_name,
        ability_id=spell_id,
        category=category,
        actor=actor_name,
        spec=None,
        target=target_name,
        duration_ms=max(0.0, duration_ms),
    )


def _dedupe_boss_cast_events(events: list[TimelineEvent]) -> list[TimelineEvent]:
    """多目标重复行、以及同名相关 spell（begincast 技能 + 同时刻触发 cast）去重。"""
    ordered = sorted(
        events,
        key=lambda item: (
            item.offset_ms,
            -(item.duration_ms or 0.0),
            item.ability_id or 0,
            item.ability,
        ),
    )
    kept: list[TimelineEvent] = []
    seen_id_bucket: set[tuple[str | None, int | None, int]] = set()
    for event in ordered:
        actor = event.actor
        spell_id = event.ability_id
        bucket = (actor, spell_id, int(event.offset_ms) // 100)
        if bucket in seen_id_bucket:
            continue
        # 同施法者同名：起点落在已保留条目的施法条内，或 250ms 内 → 保留更长 duration
        name_key = (actor or "").casefold(), event.ability.casefold()
        duplicate = False
        for index, prior in enumerate(kept):
            prior_key = (prior.actor or "").casefold(), prior.ability.casefold()
            if prior_key != name_key:
                continue
            prior_end = prior.offset_ms + max(0.0, prior.duration_ms)
            near_start = abs(event.offset_ms - prior.offset_ms) <= _BOSS_SAME_NAME_DEDUPE_MS
            inside_bar = prior.offset_ms <= event.offset_ms <= prior_end + 1.0
            if not (near_start or inside_bar):
                continue
            if event.duration_ms > prior.duration_ms:
                kept[index] = event
                seen_id_bucket.add(bucket)
            duplicate = True
            break
        if duplicate:
            continue
        seen_id_bucket.add(bucket)
        kept.append(event)
    kept.sort(key=lambda item: (item.offset_ms, item.ability_id or 0, item.ability))
    return kept


def _source_id(raw: dict[str, Any]) -> int | None:
    if raw.get("sourceID") is None:
        return None
    try:
        return int(raw["sourceID"])
    except (TypeError, ValueError):
        return None


def _raw_duration_ms(raw: dict[str, Any]) -> float:
    for key in ("duration", "castDuration"):
        value = raw.get(key)
        if value is not None:
            try:
                return max(0.0, float(value))
            except (TypeError, ValueError):
                continue
    return 0.0


def _is_enemy_cast_source(source: ActorInfo | None) -> bool:
    """首领、小怪、未识别敌方 NPC 均可；排除玩家与宠物。"""
    if source is None:
        # hostility=Enemies 拉来的事件里，未知 source 仍视为敌方
        return True
    if source.is_player or source.is_pet:
        return False
    if source.is_boss_npc or source.is_npc:
        return True
    # 部分日志把小怪标成其它 type，名字匹配不到 Boss 也照样收
    return source.type not in {"Player", "Pet", "Unknown"}


def _is_primary_boss_source(source: ActorInfo | None, fight: Fight) -> bool:
    """真正首领（用于多首领 pull 推断）；增援小怪不算。"""
    if source is None:
        return False
    if source.is_boss_npc:
        return True
    return bool(fight.name) and source.name == fight.name


def _boss_event_category(source: ActorInfo | None, fight: Fight) -> str | None:
    if _is_primary_boss_source(source, fight):
        return None
    return "小怪"


def _source_name(source: ActorInfo | None, raw: dict[str, Any]) -> str | None:
    if source is not None:
        return source.name
    nested = raw.get("source")
    if isinstance(nested, dict):
        return nested.get("name")
    return None


def _defense_cast_events(
    fight: Fight,
    raw_events: list[dict[str, Any]],
    actors_by_id: dict[int, ActorInfo],
    abilities: dict[int, str],
    *,
    player_filter: str | None,
    category_filter: DefenseCategory | None,
) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for raw in raw_events:
        event_type = raw.get("type")
        if event_type not in {None, "cast", "applybuff"}:
            continue
        spell_id = _ability_id(raw)
        ability_name = _ability_name(raw, abilities)
        defense = lookup_defense(spell_id, ability_name)
        if defense is None:
            continue
        if category_filter is not None and defense.category != category_filter:
            continue
        actor = _resolve_actor(raw.get("sourceID"), actors_by_id, prefer_owner=True)
        if actor is None:
            source = raw.get("source")
            name = source.get("name") if isinstance(source, dict) else None
            spec = None
            actor_class = None
        else:
            if not actor.is_player and not actor.is_pet:
                continue
            name = actor.name
            spec = _actor_spec(actor)
            actor_class = actor.player_class
        if player_filter and (name or "").casefold() != player_filter:
            continue
        source_id = raw.get("sourceID")
        target_name = _resolve_target_name(
            raw,
            actors_by_id,
            source_id=source_id,
            source_name=name,
        )
        events.append(
            TimelineEvent(
                offset_ms=_offset_ms(raw, fight),
                kind="defense",
                ability=defense.name,
                ability_id=defense.spell_id,
                category=category_label(defense.category),
                actor=name,
                spec=spec,
                actor_class=actor_class,
                target=target_name,
            )
        )
    return events


def _resolve_actor(
    source_id: Any,
    actors_by_id: dict[int, ActorInfo],
    *,
    prefer_owner: bool,
) -> ActorInfo | None:
    if source_id is None:
        return None
    actor = actors_by_id.get(int(source_id))
    if actor is None:
        return None
    if prefer_owner and actor.is_pet and actor.pet_owner is not None:
        owner = actors_by_id.get(actor.pet_owner)
        if owner is not None:
            return owner
    return actor


def _resolve_target_name(
    raw: dict[str, Any],
    actors_by_id: dict[int, ActorInfo],
    *,
    source_id: Any,
    source_name: str | None,
) -> str | None:
    """解析施法目标：有目标名则返回；对自己施放返回「自身」；无法判断则省略。"""
    nested = raw.get("target")
    nested_name = nested.get("name") if isinstance(nested, dict) else None
    target_id = raw.get("targetID")
    if target_id is None and isinstance(nested, dict):
        target_id = nested.get("id")

    if target_id is not None:
        try:
            tid = int(target_id)
        except (TypeError, ValueError):
            tid = None
        if tid is not None:
            if source_id is not None:
                try:
                    if tid == int(source_id):
                        return "自身"
                except (TypeError, ValueError):
                    pass
            target_actor = actors_by_id.get(tid)
            if target_actor is not None:
                if source_name and target_actor.name == source_name:
                    return "自身"
                return target_actor.name
            if nested_name:
                if source_name and nested_name == source_name:
                    return "自身"
                return str(nested_name)
            return None

    if nested_name:
        if source_name and nested_name == source_name:
            return "自身"
        return str(nested_name)
    return None


def _actor_spec(actor: ActorInfo) -> str:
    # masterData 常见：type=Player / subType=职业；table 风格：type=职业 / subType=专精
    if actor.sub_type and "-" in actor.sub_type:
        return spec_label(actor.sub_type, actor.player_class or actor.type)
    if actor.type in {
        "DeathKnight",
        "DemonHunter",
        "Druid",
        "Evoker",
        "Hunter",
        "Mage",
        "Monk",
        "Paladin",
        "Priest",
        "Rogue",
        "Shaman",
        "Warlock",
        "Warrior",
    } and actor.sub_type:
        icon = f"{actor.type}-{actor.sub_type.replace(' ', '')}"
        return spec_label(icon, actor.type)
    cls = actor.player_class
    if cls:
        return spec_label(None, cls)
    if actor.type == "Player":
        return "玩家"
    return spec_label(None, actor.type)


def _ability_id(raw: dict[str, Any]) -> int | None:
    for key in ("abilityGameID", "abilityId", "ability_id"):
        if raw.get(key) is not None:
            return int(raw[key])
    ability = raw.get("ability")
    if isinstance(ability, dict) and ability.get("guid") is not None:
        return int(ability["guid"])
    if isinstance(ability, dict) and ability.get("id") is not None:
        return int(ability["id"])
    return None


def _ability_name(raw: dict[str, Any], abilities: dict[int, str]) -> str:
    ability = raw.get("ability")
    if isinstance(ability, dict) and ability.get("name"):
        return str(ability["name"])
    spell_id = _ability_id(raw)
    if spell_id is not None and spell_id in abilities:
        return abilities[spell_id]
    if spell_id is not None:
        return f"#{spell_id}"
    return "未知技能"


def _offset_ms(raw: dict[str, Any], fight: Fight) -> float:
    timestamp = float(raw.get("timestamp") or fight.start_time)
    return max(0.0, timestamp - fight.start_time)


def _merge_unique_events(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """合并 Casts 与 applybuff；同一施法者同一技能在 250ms 内只保留一条（优先 Cast）。"""
    seen: set[tuple[int | None, int | None, int]] = set()
    merged: list[dict[str, Any]] = []
    for raw in (*primary, *secondary):
        timestamp = int(raw["timestamp"]) if raw.get("timestamp") is not None else 0
        key = (
            _ability_id(raw),
            int(raw["sourceID"]) if raw.get("sourceID") is not None else None,
            timestamp // 250,
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(raw)
    return merged


def _kind_order(kind: str) -> int:
    return {"phase": 0, "boss": 1, "defense": 2}.get(kind, 9)


def _parse_health_point(
    raw: dict[str, Any],
    fight: Fight,
    actors_by_id: dict[int, ActorInfo],
) -> tuple[tuple[int, int], str, bool, HealthSample] | None:
    """解析单条事件中的敌方血量；无法解析或非敌方则返回 None。"""
    hit_points, max_hit_points, actor_id, instance = _extract_health_fields(raw)
    if hit_points is None or max_hit_points is None or actor_id is None:
        return None
    if max_hit_points <= 0:
        return None

    actor = actors_by_id.get(actor_id)
    if actor is not None:
        if actor.is_player or actor.is_pet:
            return None
        if not (actor.is_npc or actor.is_boss_npc or _is_enemy_cast_source(actor)):
            return None
        name = actor.name
        is_boss = _is_primary_boss_source(actor, fight)
    else:
        # masterData 未收录时仍保留（多为敌方 NPC）
        nested = raw.get("target")
        name = nested.get("name") if isinstance(nested, dict) else None
        name = str(name) if name else f"#{actor_id}"
        is_boss = bool(fight.name) and name == fight.name

    pct = max(0.0, min(100.0, (hit_points / max_hit_points) * 100.0))
    sample = HealthSample(
        offset_ms=_offset_ms(raw, fight),
        pct=pct,
        current=float(hit_points),
        max_hp=float(max_hit_points),
    )
    return (actor_id, max(0, instance)), name, is_boss, sample


def _extract_health_fields(
    raw: dict[str, Any],
) -> tuple[float | None, float | None, int | None, int]:
    """从 damage / resources 事件提取 hitPoints、maxHitPoints 与目标 actor。"""
    hit_points = _coerce_float(raw.get("hitPoints"))
    max_hit_points = _coerce_float(raw.get("maxHitPoints"))
    actor_id = _coerce_int(raw.get("targetID"))
    instance = _coerce_int(raw.get("targetInstance")) or 0

    # 嵌套 resources（部分 API / includeResources）
    if hit_points is None or max_hit_points is None:
        for key in ("targetResources", "resources"):
            nested = raw.get(key)
            if not isinstance(nested, dict):
                continue
            if hit_points is None:
                hit_points = _coerce_float(nested.get("hitPoints"))
            if max_hit_points is None:
                max_hit_points = _coerce_float(nested.get("maxHitPoints"))

    # Resources 类事件：资源属于 source
    event_type = raw.get("type")
    if actor_id is None or (
        hit_points is None
        and event_type in {"resourcechange", "resources", "combatantinfo"}
    ):
        source_hp = _coerce_float(raw.get("hitPoints"))
        source_max = _coerce_float(raw.get("maxHitPoints"))
        source_res = raw.get("sourceResources")
        if isinstance(source_res, dict):
            if source_hp is None:
                source_hp = _coerce_float(source_res.get("hitPoints"))
            if source_max is None:
                source_max = _coerce_float(source_res.get("maxHitPoints"))
        if source_hp is not None and source_max is not None:
            hit_points = source_hp
            max_hit_points = source_max
            actor_id = _coerce_int(raw.get("sourceID"))
            instance = _coerce_int(raw.get("sourceInstance")) or 0

    return hit_points, max_hit_points, actor_id, instance


def _downsample_samples(
    samples: list[HealthSample],
    limit: int,
) -> list[HealthSample]:
    if limit <= 0 or len(samples) <= limit:
        return samples
    if limit == 1:
        return [samples[-1]]
    result: list[HealthSample] = []
    last_index = len(samples) - 1
    for index in range(limit):
        pos = round(index * last_index / (limit - 1))
        result.append(samples[pos])
    # 去重相邻同一时刻
    deduped: list[HealthSample] = []
    for sample in result:
        if deduped and abs(deduped[-1].offset_ms - sample.offset_ms) < 1e-6:
            deduped[-1] = sample
            continue
        deduped.append(sample)
    return deduped


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

