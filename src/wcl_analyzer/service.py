from __future__ import annotations

from typing import Any

from wcl_analyzer.analysis import resolve_fight_token, select_fight
from wcl_analyzer.client import WclClient
from wcl_analyzer.models import TimelineAnalysis
from wcl_analyzer.refs import parse_report_ref
from wcl_analyzer.spell_meta import SpellMetaStore, enrich_timeline_metadata
from wcl_analyzer.timeline import analyze_timeline, fetch_timeline_inputs


def build_timeline_analysis(
    client: WclClient,
    report_value: str,
    *,
    fight: str | None = None,
    pull: str | None = None,
    player: str | None = None,
    category: str | None = None,
    fetch_meta: bool = True,
) -> TimelineAnalysis:
    """根据报告代码 / WCL 链接构建可视化时间线分析结果。"""
    ref = parse_report_ref(report_value)
    report = client.get_report(ref.code)
    fight_token = resolve_fight_token(fight=fight, pull=pull, ref_fight=ref.fight)
    selected = select_fight(report, fight_token)
    payload: dict[str, Any] = fetch_timeline_inputs(client, report.code, selected)
    analysis = analyze_timeline(
        selected,
        actors=payload["actors"],
        abilities=payload["abilities"],
        defense_events=payload["defense_events"],
        boss_events=payload["boss_events"],
        health_events=payload.get("health_events") or [],
        player=player,
        category=category,
    )
    with SpellMetaStore(fetch=fetch_meta) as store:
        return enrich_timeline_metadata(
            analysis,
            store,
            ability_icons=payload.get("ability_icons"),
            ability_names=payload.get("abilities"),
            fetch=fetch_meta,
        )
