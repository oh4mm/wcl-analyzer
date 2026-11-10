from wcl_analyzer.analysis import resolve_fight_token
from wcl_analyzer.client import _fight_from_api
from wcl_analyzer.defenses import DefenseCategory, lookup_defense, parse_category
from wcl_analyzer.format import format_fight_time, format_pulls, format_timeline
from wcl_analyzer.html_timeline import render_timeline_html
from wcl_analyzer.models import (
    ActorInfo,
    DungeonPull,
    Fight,
    PhaseTransition,
    Report,
    TimelineEvent,
)
from wcl_analyzer.spell_meta import SpellMetaStore, enrich_timeline_metadata
from wcl_analyzer.timeline import (
    analyze_timeline,
    boss_dungeon_pulls,
    build_health_series,
    fetch_timeline_inputs,
    filter_events_by_window,
    health_series_payload,
    infer_boss_pulls_from_events,
    pull_offsets,
    resolve_boss_pulls,
)


def _fight(**overrides) -> Fight:
    data = dict(
        id=12,
        name="虫巢女王",
        encounter_id=2902,
        difficulty=5,
        kill=True,
        start_time=100_000,
        end_time=280_000,
        fight_percentage=None,
        boss_percentage=0,
        size=20,
        average_item_level=640,
        last_phase=2,
        in_progress=False,
        keystone_level=None,
        phase_transitions=(
            PhaseTransition(id=1, start_time=100_000),
            PhaseTransition(id=2, start_time=190_000),
        ),
    )
    data.update(overrides)
    return Fight(**data)


def _actors() -> tuple[ActorInfo, ...]:
    return (
        ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        # masterData 风格
        ActorInfo(id=10, name="法师甲", type="Player", sub_type="Mage"),
        # table / 旧风格：type=职业，subType=专精
        ActorInfo(id=11, name="战士乙", type="Warrior", sub_type="Protection"),
        ActorInfo(id=12, name="牧师丙", type="Player", sub_type="Priest"),
        ActorInfo(id=50, name="小恶魔", type="Pet", sub_type="Pet", pet_owner=10),
    )


def test_lookup_defense_by_id_and_name() -> None:
    ice = lookup_defense(45438)
    assert ice is not None
    assert ice.category == DefenseCategory.PERSONAL
    assert ice.name == "寒冰屏障"

    amz = lookup_defense(name="Anti-Magic Zone")
    assert amz is not None
    assert amz.category == DefenseCategory.RAID
    assert parse_category("团减") == DefenseCategory.RAID
    assert parse_category("治疗饰品") == DefenseCategory.HEAL_TRINKET
    silk = lookup_defense(1232721)
    assert silk is not None
    assert silk.category == DefenseCategory.HEAL_TRINKET
    assert silk.name == "卢米萨尔的活体丝绸"
    # 修正后的 TWW 药水 ID
    assert lookup_defense(431914) is not None
    assert lookup_defense(431914).category == DefenseCategory.COMBAT_POTION
    assert lookup_defense(431925).name == "前线药水"
    assert lookup_defense(431419).category == DefenseCategory.HEAL_POTION
    assert lookup_defense(431418).category == DefenseCategory.HEAL_POTION
    # Midnight 消耗品 / 治疗饰品（WCL Casts spell ID）
    assert lookup_defense(1295247).category == DefenseCategory.HEAL_POTION
    assert lookup_defense(1236994).category == DefenseCategory.COMBAT_POTION
    assert lookup_defense(1295132).category == DefenseCategory.COMBAT_POTION
    assert lookup_defense(1236616).category == DefenseCategory.COMBAT_POTION
    assert lookup_defense(1291894).category == DefenseCategory.HEAL_TRINKET
    assert lookup_defense(1219198).category == DefenseCategory.HEAL_TRINKET
    assert lookup_defense(name="Order Up!").category == DefenseCategory.HEAL_TRINKET
    assert lookup_defense(1295247).name == "浓缩银月城生命药水"
    assert lookup_defense(198103).name == "土元素"
    assert lookup_defense(31884).name == "复仇之怒"
    assert lookup_defense(386208).name == "防御姿态"
    assert lookup_defense(1766).category == DefenseCategory.INTERRUPT
    assert lookup_defense(2139).name == "法术反制"
    assert parse_category("打断") == DefenseCategory.INTERRUPT
    # 坦克吞吐 / 自疗不应再出现在个减目录
    assert lookup_defense(49998) is None
    assert lookup_defense(name="Death Strike") is None
    assert lookup_defense(22842) is None
    assert lookup_defense(name="Frenzied Regeneration") is None


def test_boss_lane_ignores_environment_amz_aura() -> None:
    """玩家反魔法领域的 Environment 光环生效不应出现在首领轴。"""
    fight = _fight()
    abilities = {
        451112: "刺骨尖啸",
        51052: "Anti-Magic Zone",
        145629: "Anti-Magic Zone",
    }
    analysis = analyze_timeline(
        fight,
        actors=_actors()
        + (
            ActorInfo(id=20, name="神奇的阿诺", type="Player", sub_type="DeathKnight"),
        ),
        abilities=abilities,
        defense_events=[
            {
                "timestamp": 130_000,
                "type": "cast",
                "sourceID": 20,
                "abilityGameID": 51052,
            },
        ],
        boss_events=[
            {
                "timestamp": 130_000,
                "type": "cast",
                "sourceID": 1,
                "abilityGameID": 451112,
            },
            # WCL 把 AMZ 光环记成 Environment(sourceID=-1) 对玩家的 cast
            {
                "timestamp": 130_009,
                "type": "cast",
                "sourceID": -1,
                "targetID": 20,
                "abilityGameID": 145629,
            },
        ],
    )
    boss = [event for event in analysis.events if event.kind == "boss"]
    defense = [event for event in analysis.events if event.kind == "defense"]
    assert [event.ability_id for event in boss] == [451112]
    assert not any(event.ability_id == 145629 for event in boss)
    assert any(event.ability_id == 51052 and event.actor == "神奇的阿诺" for event in defense)


def test_analyze_timeline_sorts_filters_and_categorizes() -> None:
    fight = _fight()
    abilities = {
        451112: "刺骨尖啸",
        45438: "Ice Block",
        97462: "Rallying Cry",
        431416: "Algari Healing Potion",
        431932: "Tempered Potion",
        1232721: "Loom'ithar's Living Silk",
        1: "Melee",
    }
    boss_events = [
        {
            "timestamp": 130_000,
            "type": "cast",
            "sourceID": 1,
            "targetID": 11,
            "abilityGameID": 451112,
        },
        {"timestamp": 131_000, "type": "cast", "sourceID": 1, "abilityGameID": 1},
        {"timestamp": 200_500, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
    ]
    defense_events = [
        {
            "timestamp": 129_800,
            "type": "cast",
            "sourceID": 10,
            "targetID": 10,
            "abilityGameID": 45438,
        },
        {
            "timestamp": 130_200,
            "type": "cast",
            "sourceID": 11,
            "targetID": 11,
            "abilityGameID": 97462,
        },
        {
            "timestamp": 150_000,
            "type": "cast",
            "sourceID": 12,
            "targetID": 12,
            "abilityGameID": 431416,
        },
        {
            "timestamp": 151_000,
            "type": "applybuff",
            "sourceID": 10,
            "targetID": 10,
            "abilityGameID": 431932,
        },
        {
            "timestamp": 152_000,
            "type": "cast",
            "sourceID": 12,
            "targetID": 11,
            "abilityGameID": 1232721,
        },
        {
            "timestamp": 160_000,
            "type": "cast",
            "sourceID": 50,
            "abilityGameID": 45438,
        },
    ]

    all_players = analyze_timeline(
        fight,
        actors=_actors(),
        abilities=abilities,
        defense_events=defense_events,
        boss_events=boss_events,
    )
    kinds = [event.kind for event in all_players.events]
    assert kinds[0] == "phase"
    assert any(event.kind == "boss" and event.ability == "刺骨尖啸" for event in all_players.events)
    assert not any(event.ability == "Melee" or event.ability_id == 1 for event in all_players.events)

    defenses = [event for event in all_players.events if event.kind == "defense"]
    assert [event.category for event in defenses] == [
        "个减",
        "团减",
        "治疗药水",
        "爆发药水",
        "治疗饰品",
        "个减",
    ]
    # 宠物施法归到主人；masterData 通常只有职业没有专精
    assert defenses[-1].actor == "法师甲"
    assert defenses[0].spec == "法师"
    assert defenses[1].spec == "防护战士"
    assert defenses[0].target == "自身"
    assert defenses[4].target == "战士乙"
    boss_hit = next(
        event for event in all_players.events if event.kind == "boss" and event.offset_ms == 30_000
    )
    assert boss_hit.target == "战士乙"

    filtered = analyze_timeline(
        fight,
        actors=_actors(),
        abilities=abilities,
        defense_events=defense_events,
        boss_events=boss_events,
        player="战士乙",
        category="团减",
    )
    defense_only = [event for event in filtered.events if event.kind == "defense"]
    assert len(defense_only) == 1
    assert defense_only[0].actor == "战士乙"
    assert defense_only[0].ability == "集结呐喊"
    assert any(event.kind == "boss" for event in filtered.events)


def test_format_timeline_chinese_table() -> None:
    fight = _fight(phase_transitions=())
    analysis = analyze_timeline(
        fight,
        actors=_actors(),
        abilities={642: "Divine Shield", 451112: "刺骨尖啸"},
        defense_events=[
            {"timestamp": 112_500, "type": "cast", "sourceID": 11, "abilityGameID": 642},
        ],
        boss_events=[
            {"timestamp": 110_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    text = format_timeline(analysis)
    assert "减伤 / 药水时间线" in text
    assert "0:10.000" in text
    assert "首领" in text
    assert "圣盾术" in text
    assert "个减" in text
    assert format_fight_time(12_500) == "0:12.500"


def test_timeline_event_json_shape() -> None:
    event = TimelineEvent(
        offset_ms=1000,
        kind="defense",
        ability="寒冰屏障",
        ability_id=45438,
        category="个减",
        actor="法师甲",
        spec="火焰法师",
    )
    assert event.category == "个减"


def test_render_timeline_html_contains_markers_and_categories(tmp_path) -> None:
    fight = _fight()
    analysis = analyze_timeline(
        fight,
        actors=_actors(),
        abilities={
            451112: "刺骨尖啸",
            45438: "Ice Block",
            97462: "Rallying Cry",
            431416: "Algari Healing Potion",
            431932: "Tempered Potion",
            1232721: "Loom'ithar's Living Silk",
        },
        defense_events=[
            {
                "timestamp": 129_800,
                "type": "cast",
                "sourceID": 10,
                "targetID": 10,
                "abilityGameID": 45438,
            },
            {"timestamp": 130_200, "type": "cast", "sourceID": 11, "abilityGameID": 97462},
            {
                "timestamp": 150_000,
                "type": "cast",
                "sourceID": 12,
                "targetID": 12,
                "abilityGameID": 431416,
            },
            {"timestamp": 151_000, "type": "applybuff", "sourceID": 10, "abilityGameID": 431932},
            {
                "timestamp": 152_000,
                "type": "cast",
                "sourceID": 12,
                "targetID": 11,
                "abilityGameID": 1232721,
            },
        ],
        boss_events=[
            {
                "timestamp": 130_000,
                "type": "cast",
                "sourceID": 1,
                "targetID": 10,
                "abilityGameID": 451112,
            },
            {"timestamp": 160_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    store = SpellMetaStore(cache_path=tmp_path / "meta.json", fetch=False)
    store.seed_icons(
        {
            45438: "spell_frost_frost",
            97462: "ability_warrior_rallyingcry",
            451112: "spell_shadow_psychicscream",
        }
    )
    analysis = enrich_timeline_metadata(analysis, store, fetch=False)
    html = render_timeline_html(analysis)
    assert "<!DOCTYPE html>" in html
    assert "TIMELINE_DATA" in html
    assert "刺骨尖啸" in html
    assert "寒冰屏障" in html
    assert "集结呐喊" in html
    assert "阿加治疗药水" in html
    assert "回火药水" in html
    assert "法师甲" in html
    assert "战士乙" in html
    assert "个减" in html
    assert "团减" in html
    assert "治疗药水" in html
    assert "爆发药水" in html
    assert "治疗饰品" in html
    assert "卢米萨尔的活体丝绸" in html
    assert "目标:" in html
    assert '"target": "自身"' in html or '"target":"自身"' in html
    assert '"target": "法师甲"' in html or '"target":"法师甲"' in html
    assert '"actorClass": "Mage"' in html or '"actorClass":"Mage"' in html
    assert "class_mage.jpg" in html
    assert "class_warrior.jpg" in html
    assert "#3FC7EB" in html  # 法师职业色
    assert "position: sticky" in html
    assert "left: 0" in html
    assert "首领技能" in html
    assert "阶段" in html
    assert "阶段 2" in html
    assert "fight id 12" in html
    assert "首领技能间隔" in html
    assert "推算 CD" in html
    assert "wow.zamimg.com/images/wow/icons/large/spell_frost_frost.jpg" in html
    assert "iconUrl" in html
    # 图标不再使用类别色描边
    assert "border: 2px solid var(--c" not in html
    assert "referrerPolicy" in html or "referrerpolicy" in html.lower()
    assert "onerror" in html
    # 秒级时间轴：CSS 每秒竖线 + WowAnalyzer 风格 skipInterval 标尺
    assert "--sec-w" in html
    assert "--duration-s" in html
    assert "repeating-linear-gradient" in html
    assert "pickSecondWidth" in html
    assert "pickSkipInterval" in html
    assert "Math.ceil(40 / secWidth)" in html
    # 绝对时间标签防重叠（18:54 / 18:55 在大 secWidth 下）
    assert "placeAxisTick" in html
    assert "lastLabelRight" in html
    assert "estimateLabelWidth" in html
    assert "--ticks" not in html
    assert "时间轴含首领与小怪技能" in html
    assert "opt-interrupts" in html
    assert "显示打断" in html
    assert "showInterrupts" in html


def test_pot_only_player_gets_swimlane() -> None:
    """只喝药水、没有个减的玩家也要出现在泳道里。"""
    fight = _fight(phase_transitions=())
    actors = (
        ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        ActorInfo(id=20, name="猎手丁", type="Player", sub_type="Hunter"),
        ActorInfo(id=21, name="术士戊", type="Warlock", sub_type="Affliction"),
    )
    analysis = analyze_timeline(
        fight,
        actors=actors,
        abilities={
            431416: "Algari Healing Potion",
            431914: "Potion of Unwavering Focus",
            451112: "刺骨尖啸",
        },
        defense_events=[
            {
                "timestamp": 120_000,
                "type": "cast",
                "sourceID": 20,
                "targetID": 20,
                "abilityGameID": 431416,
            },
            {
                "timestamp": 140_000,
                "type": "applybuff",
                "sourceID": 21,
                "targetID": 21,
                "abilityGameID": 431914,
            },
        ],
        boss_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    defenses = [event for event in analysis.events if event.kind == "defense"]
    assert {event.actor for event in defenses} == {"猎手丁", "术士戊"}
    assert {event.category for event in defenses} == {"治疗药水", "爆发药水"}
    html = render_timeline_html(analysis)
    assert "猎手丁" in html
    assert "术士戊" in html
    assert "治疗药水" in html
    assert "爆发药水" in html


def test_midnight_potions_and_healer_trinkets_on_timeline() -> None:
    """Midnight 治疗/爆发药水与治疗饰品应按 Casts spell ID 进入泳道。"""
    fight = _fight(phase_transitions=())
    actors = (
        ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        ActorInfo(id=30, name="萨满己", type="Player", sub_type="Shaman"),
        ActorInfo(id=31, name="骑士庚", type="Player", sub_type="Paladin"),
        ActorInfo(id=32, name="战士辛", type="Warrior", sub_type="Fury"),
    )
    analysis = analyze_timeline(
        fight,
        actors=actors,
        abilities={
            1295247: "Concentrated Silvermoon Health Potion",
            1236994: "Potion of Recklessness",
            1295132: "Liquid Luster",
            1236616: "Light's Potential",
            1291894: "Soulcoiler Ritual Vessel",
            1219198: "Order Up!",
            451112: "刺骨尖啸",
        },
        defense_events=[
            {
                "timestamp": 110_000,
                "type": "cast",
                "sourceID": 30,
                "targetID": 30,
                "abilityGameID": 1295247,
            },
            {
                "timestamp": 120_000,
                "type": "cast",
                "sourceID": 30,
                "abilityGameID": 1219198,
            },
            {
                "timestamp": 130_000,
                "type": "cast",
                "sourceID": 31,
                "abilityGameID": 1291894,
            },
            {
                "timestamp": 140_000,
                "type": "cast",
                "sourceID": 32,
                "targetID": 32,
                "abilityGameID": 1236994,
            },
            {
                "timestamp": 150_000,
                "type": "cast",
                "sourceID": 31,
                "targetID": 31,
                "abilityGameID": 1295132,
            },
            {
                "timestamp": 160_000,
                "type": "cast",
                "sourceID": 30,
                "targetID": 30,
                "abilityGameID": 1236616,
            },
        ],
        boss_events=[
            {"timestamp": 125_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    defenses = [event for event in analysis.events if event.kind == "defense"]
    by_cat = {event.category for event in defenses}
    assert by_cat == {"治疗药水", "爆发药水", "治疗饰品"}
    assert {event.ability for event in defenses} == {
        "浓缩银月城生命药水",
        "鲁莽药水",
        "液态光泽",
        "圣光潜力",
        "盘魂者仪式容器",
        "上餐了！",
    }
    html = render_timeline_html(analysis)
    assert "浓缩银月城生命药水" in html
    assert "盘魂者仪式容器" in html
    assert "上餐了！" in html
    assert "鲁莽药水" in html
    assert "治疗饰品" in html


def test_format_timeline_includes_boss_cd_summary() -> None:
    fight = _fight(phase_transitions=())
    analysis = analyze_timeline(
        fight,
        actors=_actors(),
        abilities={451112: "刺骨尖啸"},
        defense_events=[],
        boss_events=[
            {"timestamp": 110_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
            {"timestamp": 140_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
            {"timestamp": 180_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    text = format_timeline(analysis)
    assert "fight id 12" in text
    assert "首领技能间隔" in text
    assert "刺骨尖啸" in text
    assert "推算 CD" in text
    assert "0:30" in text


def test_resolve_fight_token_pull_alias() -> None:
    assert resolve_fight_token(fight=None, pull="12", ref_fight=None) == "12"
    assert resolve_fight_token(fight="12", pull="12", ref_fight="9") == "12"
    assert resolve_fight_token(fight=None, pull=None, ref_fight="9") == "9"
    try:
        resolve_fight_token(fight="1", pull="2", ref_fight=None)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "--fight" in str(exc) and "--pull" in str(exc)


def test_fetch_timeline_inputs_forwards_ability_icons() -> None:
    """WCL masterData 的 icon 必须传到 enrich，否则大量技能会缺图。"""

    class FakeClient:
        def __init__(self) -> None:
            self.event_calls: list[dict] = []

        def get_master_data(self, code: str) -> dict:
            assert code == "Abcd1234"
            return {
                "actors": _actors(),
                "abilities": {45438: "Ice Block", 451112: "Piercing Screech"},
                "ability_icons": {
                    45438: "spell_frost_frost.jpg",
                    451112: "spell_shadow_psychicscream.jpg",
                },
            }

        def get_events(self, *args, **kwargs) -> list:
            self.event_calls.append(kwargs)
            return []

    client = FakeClient()
    payload = fetch_timeline_inputs(client, "Abcd1234", _fight())
    assert payload["ability_icons"][45438] == "spell_frost_frost.jpg"
    assert payload["ability_icons"][451112] == "spell_shadow_psychicscream.jpg"
    assert "health_events" in payload
    health_calls = [
        call
        for call in client.event_calls
        if call.get("data_type") == "DamageDone"
    ]
    assert health_calls
    assert health_calls[0].get("include_resources") is True


def test_build_health_series_samples_boss_and_add_pct() -> None:
    fight = _fight()
    actors = {
        1: ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        2: ActorInfo(id=2, name="甲虫", type="NPC", sub_type="NPC"),
        10: ActorInfo(id=10, name="法师甲", type="Player", sub_type="Mage"),
    }
    events = [
        {
            "timestamp": 110_000,
            "type": "damage",
            "sourceID": 10,
            "targetID": 1,
            "hitPoints": 900_000,
            "maxHitPoints": 1_000_000,
        },
        {
            "timestamp": 130_000,
            "type": "damage",
            "sourceID": 10,
            "targetID": 1,
            "hitPoints": 500_000,
            "maxHitPoints": 1_000_000,
        },
        {
            "timestamp": 140_000,
            "type": "damage",
            "sourceID": 10,
            "targetID": 2,
            "targetInstance": 1,
            "hitPoints": 20_000,
            "maxHitPoints": 40_000,
        },
        # 玩家承伤应忽略
        {
            "timestamp": 150_000,
            "type": "damage",
            "sourceID": 1,
            "targetID": 10,
            "hitPoints": 100,
            "maxHitPoints": 200,
        },
        # 嵌套 targetResources
        {
            "timestamp": 160_000,
            "type": "damage",
            "sourceID": 10,
            "targetID": 2,
            "targetInstance": 1,
            "targetResources": {"hitPoints": 0, "maxHitPoints": 40_000},
        },
    ]
    series = build_health_series(fight, events, actors)
    assert len(series) == 2
    boss = next(item for item in series if item.is_boss)
    add = next(item for item in series if not item.is_boss)
    assert boss.name == "虫巢女王"
    assert boss.samples[0].pct == 90.0
    assert boss.samples[-1].pct == 50.0
    assert add.name == "甲虫"
    assert add.samples[-1].pct == 0.0

    payload = health_series_payload(series)
    assert payload[0]["isBoss"] is True
    assert payload[0]["samples"][0]["offsetMs"] == 10_000
    assert "pct" in payload[0]["samples"][0]


def test_health_series_payload_keeps_series_for_each_boss_window() -> None:
    """早期小怪采样再多，也不能把后期首领时间窗的血量序列挤出 payload。"""
    from wcl_analyzer.models import HealthSample, HealthSeries

    early_adds = [
        HealthSeries(
            id=100 + index,
            name=f"Trash #{index}",
            is_boss=False,
            instance=1,
            samples=tuple(
                HealthSample(offset_ms=float(t), pct=100.0 - t / 100.0, current=1.0, max_hp=1.0)
                for t in range(0, 4000, 20)
            ),
        )
        for index in range(45)
    ]
    late_boss = HealthSeries(
        id=9,
        name="加瓦兹特",
        is_boss=False,
        instance=1,
        samples=(
            HealthSample(offset_ms=1_200_000.0, pct=100.0, current=1.0, max_hp=1.0),
            HealthSample(offset_ms=1_300_000.0, pct=40.0, current=0.4, max_hp=1.0),
        ),
    )
    series = tuple(early_adds + [late_boss])
    plain = health_series_payload(series)
    assert all(item["name"] != "加瓦兹特" for item in plain)

    windows = [(1_136_862.0, 1_365_872.0)]
    covered = health_series_payload(series, windows=windows)
    assert any(item["name"] == "加瓦兹特" for item in covered)


def test_analyze_timeline_includes_health_series_and_html_scrubber(tmp_path) -> None:
    fight = _fight()
    analysis = analyze_timeline(
        fight,
        actors=_actors()
        + (ActorInfo(id=2, name="甲虫", type="NPC", sub_type="NPC"),),
        abilities={451112: "刺骨尖啸", 45438: "Ice Block"},
        defense_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 10, "abilityGameID": 45438},
        ],
        boss_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
        health_events=[
            {
                "timestamp": 120_000,
                "type": "damage",
                "sourceID": 10,
                "targetID": 1,
                "hitPoints": 800_000,
                "maxHitPoints": 1_000_000,
            },
            {
                "timestamp": 150_000,
                "type": "damage",
                "sourceID": 10,
                "targetID": 2,
                "hitPoints": 10_000,
                "maxHitPoints": 40_000,
            },
        ],
    )
    assert len(analysis.health_series) == 2
    store = SpellMetaStore(cache_path=tmp_path / "meta.json", fetch=False)
    analysis = enrich_timeline_metadata(analysis, store, fetch=False)
    assert len(analysis.health_series) == 2
    html = render_timeline_html(analysis)
    assert "healthSeries" in html
    assert "hp-panel" in html
    assert "playhead" in html
    assert "scrub-handle" in html
    assert "playhead-hit" in html
    assert "setPointerCapture" in html
    assert "scrubMs" in html
    assert "updateHpPanel" in html
    assert "pickHealthSeriesForView" in html
    assert "seriesOverlapsView" in html
    assert "hp-empty" in html
    # 敌方血条：红底黑槽、名字和整数百分比压在条内，首领顶上有金色星标
    assert "#b3473e" in html
    assert "#edcd68" in html
    assert "hp-item.boss::before" in html
    assert "Math.round(pct)" in html
    # shownHealthSeries 必须在首次 setupHpPanel 调用之前声明，避免 TDZ 崩掉整页
    js = html.split("<script>", 2)[-1]
    decl = js.index("let shownHealthSeries")
    first_call = js.index("setupHpPanel();")
    assert decl < first_call
    assert "虫巢女王" in html
    assert "甲虫" in html


def test_temple_of_sethraliss_localized() -> None:
    from wcl_analyzer.models import fight_display_name, short_encounter_name

    assert short_encounter_name("Temple of Sethraliss") == "塞塔里斯神庙"
    assert short_encounter_name("Adderis and Aspix") == "阿德里斯和阿斯匹克斯"
    assert short_encounter_name("Merektha") == "米利克萨"
    fight = _fight(name="Temple of Sethraliss", encounter_id=0, difficulty=10, keystone_level=24)
    assert "塞塔里斯神庙" in fight_display_name(fight)


def test_tww_season2_dungeon_and_npc_aliases() -> None:
    from wcl_analyzer.models import FIGHT_NAME_ZH, short_encounter_name

    assert short_encounter_name("Cinderbrew Meadery") == "燧酿酒庄"
    assert short_encounter_name("Darkflame Cleft") == "暗焰裂口"
    assert short_encounter_name("The Rookery") == "驭雷栖巢"
    assert short_encounter_name("Priory of the Sacred Flame") == "圣焰隐修院"
    assert short_encounter_name("Operation: Floodgate") == "水闸行动"
    assert short_encounter_name("The MOTHERLODE!!") == "暴富矿区！！"
    assert short_encounter_name("Theater of Pain") == "伤逝剧场"
    assert short_encounter_name("Operation: Mechagon - Workshop") == "麦卡贡行动 - 车间"
    # 首领
    assert short_encounter_name("Brew Master Aldryr") == "酿造大师阿德里尔"
    assert short_encounter_name("Ol' Waxbeard") == "老蜡须"
    assert short_encounter_name("Kyrioss") == "凯里欧斯"
    assert short_encounter_name("Prioress Murrpray") == "隐修院长穆普雷"
    assert short_encounter_name("Big M.O.M.M.A.") == "老大娘"
    assert short_encounter_name("Swampface") == "沼面"
    assert short_encounter_name("Azerokk") == "艾泽洛克"
    assert short_encounter_name("Mordretha, the Endless Empress") == "无尽女皇莫德蕾莎"
    assert short_encounter_name("K.U.-J.0.") == "狂犬K.U.-J.0."
    # 小怪抽样
    assert short_encounter_name("Bee Wrangler") == "驯蜂者"
    assert short_encounter_name("Arathi Footman") == "阿拉希步兵"
    assert short_encounter_name("Darkfuse Hyena") == "暗索土狼"
    assert len(FIGHT_NAME_ZH) >= 200


def test_format_pulls_lists_fight_ids() -> None:
    report = Report(
        code="Abcd1234",
        title="进度之夜",
        start_time=1_700_000_000_000,
        end_time=1_700_003_600_000,
        owner="团长",
        zone_name="尼鲁巴尔王宫",
        fights=(
            _fight(id=12, kill=True, end_time=280_000),
            _fight(
                id=13,
                kill=False,
                boss_percentage=42.5,
                start_time=300_000,
                end_time=420_000,
                phase_transitions=(),
            ),
            _fight(id=14, name="小怪", encounter_id=0, phase_transitions=()),
        ),
    )
    text = format_pulls(report)
    assert "一场 pull = 一个 fight id" in text
    assert "12" in text
    assert "13" in text
    assert "虫巢女王" in text
    assert "团本/首领" in text
    assert "击杀" in text
    assert "灭团 42.5%" in text
    assert "小怪" not in text


def test_format_pulls_marks_keystone_dungeon() -> None:
    report = Report(
        code="FkZJD26b9aAndCRr",
        title="混合",
        start_time=1,
        end_time=2,
        owner="上传者",
        zone_name="The Venomous Abyss",
        fights=(
            _fight(id=5, name="Kith'ix", encounter_id=3513, difficulty=4, kill=True),
            _fight(
                id=11,
                name="Murder Row",
                encounter_id=12813,
                difficulty=10,
                keystone_level=22,
                kill=True,
                end_time=2_000_000,
            ),
        ),
    )
    text = format_pulls(report)
    assert "大秘境" in text
    assert "密谋小径" in text
    assert "Murder Row" in text
    assert "+22" in text
    assert "11" in text


def _murder_row_pulls() -> tuple[DungeonPull, ...]:
    # 相对 fight.start_time=100_000 的报告时间戳
    return (
        DungeonPull(
            id=5,
            name="Kystia Manaheart",
            encounter_id=3101,
            start_time=120_000,
            end_time=160_000,
            kill=True,
        ),
        DungeonPull(
            id=10,
            name="Zaen Bladesorrow",
            encounter_id=3102,
            start_time=180_000,
            end_time=230_000,
            kill=True,
        ),
        DungeonPull(
            id=99,
            name="Trash Pack",
            encounter_id=0,
            start_time=165_000,
            end_time=175_000,
            kill=None,
        ),
    )


def test_boss_dungeon_pulls_skips_trash_and_offsets() -> None:
    fight = _fight(
        name="Murder Row",
        encounter_id=12813,
        difficulty=10,
        keystone_level=22,
        end_time=280_000,
        dungeon_pulls=_murder_row_pulls(),
    )
    bosses = boss_dungeon_pulls(fight)
    assert len(bosses) == 2
    assert bosses[0].name == "Kystia Manaheart"
    start, end = pull_offsets(fight, bosses[0])
    assert start == 20_000
    assert end == 60_000
    resolved = resolve_boss_pulls(fight)
    assert len(resolved) == 2


def test_filter_events_by_window() -> None:
    events = (
        TimelineEvent(offset_ms=10_000, kind="boss", ability="A"),
        TimelineEvent(offset_ms=25_000, kind="defense", ability="B", actor="法师甲"),
        TimelineEvent(offset_ms=70_000, kind="boss", ability="C"),
        # 起点在窗外，但施法条伸进窗口
        TimelineEvent(
            offset_ms=18_000,
            kind="boss",
            ability="利斧投掷",
            duration_ms=5_000,
        ),
    )
    windowed = filter_events_by_window(events, 20_000, 60_000)
    assert [event.ability for event in windowed] == ["B", "利斧投掷"]


def test_merge_boss_begincast_into_duration_bar() -> None:
    """begincast→cast 合并为一条；同名同时刻触发的相关 cast 去重。"""
    fight = _fight(phase_transitions=())
    analysis = analyze_timeline(
        fight,
        actors=_actors(),
        abilities={
            1214637: "Axe Toss",
            1214641: "Axe Toss",
            451112: "刺骨尖啸",
        },
        defense_events=[],
        boss_events=[
            # 利斧投掷：begincast(1214641) + 同时刻触发 cast(1214637) + 3s 后完成 cast
            {
                "timestamp": 110_000,
                "type": "begincast",
                "sourceID": 1,
                "abilityGameID": 1214641,
            },
            {
                "timestamp": 110_000,
                "type": "cast",
                "sourceID": 1,
                "targetID": 11,
                "abilityGameID": 1214637,
            },
            {
                "timestamp": 113_010,
                "type": "cast",
                "sourceID": 1,
                "targetID": 11,
                "abilityGameID": 1214641,
            },
            # 瞬发首领技能：无 begincast
            {
                "timestamp": 130_000,
                "type": "cast",
                "sourceID": 1,
                "abilityGameID": 451112,
            },
        ],
    )
    bosses = [event for event in analysis.events if event.kind == "boss"]
    assert len(bosses) == 2
    axe = bosses[0]
    assert axe.ability == "Axe Toss"
    assert axe.ability_id == 1214641
    assert axe.offset_ms == 10_000
    assert axe.duration_ms == 3_010
    assert axe.target == "战士乙"
    instant = bosses[1]
    assert instant.ability == "刺骨尖啸"
    assert instant.duration_ms == 0.0

    html = render_timeline_html(analysis)
    assert "cast-bar" in html
    assert "boss-cast" in html
    assert "durationMs" in html
    assert "3010" in html
    assert "has-duration" in html
    assert "tipHtml" in html
    assert "cleanTipDescription" in html
    assert "施法者:" in html
    assert "boss-tip" in html
    assert "defenseTipHtml" not in html
    # 提示不再带英文名 / 类别前缀 / Wowhead 施法时间字段
    assert "ev.abilityEn" not in html.split("function tipHtml", 1)[-1].split("function cleanTipDescription", 1)[0]
    assert "ev.castLabel" not in html.split("function tipHtml", 1)[-1].split("function cleanTipDescription", 1)[0]
    assert "首领技能" not in html.split("function tipHtml", 1)[-1].split("function cleanTipDescription", 1)[0]


def test_boss_lane_includes_add_casts_and_interrupts_toggle() -> None:
    """多首领 / 小怪技能进首领轴；打断进数据但页面默认隐藏。"""
    fight = _fight(phase_transitions=())
    actors = (
        ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        ActorInfo(id=2, name="虫巢卫士", type="NPC", sub_type="NPC"),
        ActorInfo(id=10, name="法师甲", type="Player", sub_type="Mage"),
        ActorInfo(id=11, name="战士乙", type="Warrior", sub_type="Protection"),
    )
    analysis = analyze_timeline(
        fight,
        actors=actors,
        abilities={
            451112: "刺骨尖啸",
            999001: "卫士挥击",
            2139: "Counterspell",
            6552: "Pummel",
        },
        defense_events=[
            {"timestamp": 120_000, "type": "cast", "sourceID": 10, "abilityGameID": 2139},
            {"timestamp": 125_000, "type": "cast", "sourceID": 11, "abilityGameID": 6552},
        ],
        boss_events=[
            {"timestamp": 110_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
            {"timestamp": 115_000, "type": "cast", "sourceID": 2, "abilityGameID": 999001},
        ],
    )
    bosses = [event for event in analysis.events if event.kind == "boss"]
    assert {event.ability for event in bosses} == {"刺骨尖啸", "卫士挥击"}
    add_cast = next(event for event in bosses if event.ability == "卫士挥击")
    assert add_cast.actor == "虫巢卫士"
    assert add_cast.category == "小怪"
    interrupts = [
        event
        for event in analysis.events
        if event.kind == "defense" and event.category == "打断"
    ]
    assert {event.ability for event in interrupts} == {"法术反制", "拳击"}
    html = render_timeline_html(analysis)
    assert "卫士挥击" in html
    assert "法术反制" in html
    assert "拳击" in html
    assert "opt-interrupts" in html
    assert "showInterrupts = false" in html
    assert 'category === "打断"' in html
    # 仅小怪 + 单首领时不应推断出多段 pull
    assert resolve_boss_pulls(fight, analysis.events) == ()


def test_infer_boss_pulls_from_events_when_no_dungeon_pulls() -> None:
    fight = _fight(dungeon_pulls=(), phase_transitions=())
    events = (
        TimelineEvent(offset_ms=5_000, kind="boss", ability="X", actor="BossA"),
        TimelineEvent(offset_ms=12_000, kind="boss", ability="Y", actor="BossA"),
        TimelineEvent(offset_ms=40_000, kind="boss", ability="Z", actor="BossB"),
        TimelineEvent(offset_ms=55_000, kind="boss", ability="W", actor="BossB"),
    )
    inferred = infer_boss_pulls_from_events(fight, events)
    assert len(inferred) == 2
    assert inferred[0].name == "BossA"
    assert inferred[1].name == "BossB"
    # 单首领不应出现切换控件数据
    single = (
        TimelineEvent(offset_ms=5_000, kind="boss", ability="X", actor="OnlyBoss"),
        TimelineEvent(offset_ms=12_000, kind="boss", ability="Y", actor="OnlyBoss"),
    )
    assert resolve_boss_pulls(fight, single) == ()


def test_fight_from_api_parses_dungeon_pulls() -> None:
    fight = _fight_from_api(
        {
            "id": 11,
            "name": "Murder Row",
            "encounterID": 12813,
            "difficulty": 10,
            "kill": True,
            "startTime": 100_000,
            "endTime": 280_000,
            "keystoneLevel": 22,
            "dungeonPulls": [
                {
                    "id": 5,
                    "name": "Kystia Manaheart",
                    "encounterID": 3101,
                    "startTime": 120_000,
                    "endTime": 160_000,
                    "kill": True,
                },
                {
                    "id": 8,
                    "name": "Trash",
                    "encounterID": 0,
                    "startTime": 165_000,
                    "endTime": 170_000,
                    "kill": None,
                },
            ],
        }
    )
    assert len(fight.dungeon_pulls) == 2
    assert fight.dungeon_pulls[0].name == "Kystia Manaheart"
    assert fight.dungeon_pulls[0].is_boss
    assert not fight.dungeon_pulls[1].is_boss


def test_render_timeline_html_includes_boss_pull_controls(tmp_path) -> None:
    fight = _fight(
        name="Murder Row",
        encounter_id=12813,
        difficulty=10,
        keystone_level=22,
        end_time=280_000,
        dungeon_pulls=_murder_row_pulls(),
        phase_transitions=(),
    )
    analysis = analyze_timeline(
        fight,
        actors=_actors(),
        abilities={451112: "刺骨尖啸", 45438: "Ice Block"},
        defense_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 10, "abilityGameID": 45438},
        ],
        boss_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
            {"timestamp": 200_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    store = SpellMetaStore(cache_path=tmp_path / "meta.json", fetch=False)
    analysis = enrich_timeline_metadata(analysis, store, fetch=False)
    html = render_timeline_html(analysis)
    assert "boss-pull-wrap" in html
    assert "bossPulls" in html
    # 有多首领时不再提供「整场」；默认激活第一个首领 pull
    assert 'addPullButton("all", "整场")' not in html
    assert 'activePullId = String(bossPulls[0].id)' in html
    assert "凯斯媞亚·魔力之心" in html
    assert "赞恩·刃悲" in html
    assert "Kystia Manaheart" in html
    assert "startOffsetMs" in html
    assert "activePullId" in html
    # 首领按钮显示时间段，按钮之间有独立间距容器
    assert "pull-time" in html
    assert "pull-name" in html
    assert "#boss-pull-buttons" in html
    assert "fmtAxis(startMs)" in html or 'fmtAxis(startMs) + "–"' in html
    # 首领技能对照按钮 + 时间轴辅助竖线（可取消选中；无「全部」）
    assert "boss-ability-wrap" in html
    assert "boss-ability-buttons" in html
    assert "setupAbilityButtons" in html
    assert "applyAbilityHighlight" in html
    assert "ability-guides" in html
    assert "ability-guide-line" in html
    assert "selectedAbilityId" in html
    assert "boss-ability-btn" in html
    assert "navigateAbilityCast" in html
    assert "scrollToCast" in html
    assert "smooth" in html
    assert "refreshAbilityCountLabels" in html
    assert "ability-count" in html
    assert "player-cast" in html
    assert "effect-bar" in html
    assert "assignStackLevels" in html
    assert 'addAbilityRadio("all", "全部"' not in html
    assert "全部" not in html.split("boss-ability-bar", 1)[-1].split("board-wrap", 1)[0]
    assert "ability-filter-on" not in html
    assert "ability-hl" not in html
    assert "dataset.abilityKey" in html
    # 已移除类别图例行（个减 / 团减等）
    assert 'id="legend"' not in html
    assert "class=\"legend\"" not in html
    assert '"legend"' not in html
    # 时间轴宽度贴合可见窗口，不因 min-width/max-content 拖出空白尾
    assert "calc(var(--label-w) + var(--track-w))" in html
    assert "min-width: 100%" not in html
    # 已移除「首领技能较多」密度过滤复选框；默认始终显示全部首领技能
    assert "dense-toggle" not in html
    assert "denseBoss" not in html
    assert "首领技能较多" not in html

    # 单首领团本无 dungeonPulls：控件数据为空，模板仍有挂载点但 JS 会隐藏
    raid = analyze_timeline(
        _fight(dungeon_pulls=(), phase_transitions=()),
        actors=_actors(),
        abilities={451112: "刺骨尖啸"},
        defense_events=[],
        boss_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    raid_html = render_timeline_html(raid)
    assert '"bossPulls": []' in raid_html or '"bossPulls":[]' in raid_html
    assert "boss-ability-wrap" in raid_html
    assert 'addPullButton("all", "整场")' not in raid_html
    assert 'id="legend"' not in raid_html
