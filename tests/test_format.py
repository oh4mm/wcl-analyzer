import csv
import io

from wcl_analyzer.format import (
    format_amount,
    format_defense_csv,
    format_duration,
    format_report,
)
from wcl_analyzer.models import (
    ActorInfo,
    Fight,
    PhaseTransition,
    Report,
    TimelineAnalysis,
    TimelineEvent,
)
from wcl_analyzer.timeline import analyze_timeline


def test_format_amount_and_duration() -> None:
    assert format_amount(12_340_000) == "1234.0万"
    assert format_amount(250_000_000) == "2.50亿"
    assert format_duration(125_000) == "2:05"
    assert format_duration(3_700_000) == "1:01:40"


def test_format_report_lists_boss_only() -> None:
    report = Report(
        code="Abcd1234",
        title="进度之夜",
        start_time=1_700_000_000_000,
        end_time=1_700_003_600_000,
        owner="团长",
        zone_name="尼鲁巴尔王宫",
        fights=(
            Fight(
                id=1,
                name="虫巢女王",
                encounter_id=2902,
                difficulty=5,
                kill=True,
                start_time=0,
                end_time=180_000,
                fight_percentage=None,
                boss_percentage=0,
                size=20,
                average_item_level=640,
                last_phase=3,
                in_progress=False,
                keystone_level=None,
            ),
            Fight(
                id=2,
                name="小怪",
                encounter_id=0,
                difficulty=None,
                kill=None,
                start_time=0,
                end_time=10_000,
                fight_percentage=None,
                boss_percentage=None,
                size=None,
                average_item_level=None,
                last_phase=None,
                in_progress=False,
                keystone_level=None,
            ),
        ),
    )
    text = format_report(report)
    assert "虫巢女王" in text
    assert "史诗" in text
    assert "小怪" not in text
    assert "3:00" in text


def _timeline_fight() -> Fight:
    return Fight(
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
    )


def _csv_rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def test_format_defense_csv_exports_defense_events_only() -> None:
    fight = Fight(
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
    actors = (
        ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        ActorInfo(id=10, name="法师甲", type="Player", sub_type="Mage"),
        ActorInfo(id=11, name="战士乙", type="Warrior", sub_type="Protection"),
        ActorInfo(id=12, name="牧师丙", type="Player", sub_type="Priest"),
        ActorInfo(id=50, name="小恶魔", type="Pet", sub_type="Pet", pet_owner=10),
    )
    analysis = analyze_timeline(
        fight,
        actors=actors,
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
        ],
        boss_events=[
            {
                "timestamp": 130_000,
                "type": "cast",
                "sourceID": 1,
                "targetID": 11,
                "abilityGameID": 451112,
            },
        ],
    )
    text = format_defense_csv(analysis)
    rows = _csv_rows(text)
    defenses = [event for event in analysis.events if event.kind == "defense"]
    assert rows[0] == [
        "时间",
        "偏移毫秒",
        "类别",
        "玩家",
        "专精",
        "职业",
        "技能",
        "技能ID",
        "英文名",
        "目标",
    ]
    assert len(rows) == len(defenses) + 1
    assert rows[1] == [
        "0:29.800",
        "29800",
        "个减",
        "法师甲",
        "法师",
        "Mage",
        "寒冰屏障",
        "45438",
        "",
        "自身",
    ]
    assert "刺骨尖啸" not in text
    assert "阶段" not in text


def test_format_defense_csv_respects_player_and_category_filter() -> None:
    fight = _timeline_fight()
    actors = (
        ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        ActorInfo(id=10, name="法师甲", type="Player", sub_type="Mage"),
        ActorInfo(id=11, name="战士乙", type="Warrior", sub_type="Protection"),
    )
    analysis = analyze_timeline(
        fight,
        actors=actors,
        abilities={45438: "Ice Block", 97462: "Rallying Cry", 451112: "刺骨尖啸"},
        defense_events=[
            {"timestamp": 129_800, "type": "cast", "sourceID": 10, "abilityGameID": 45438},
            {"timestamp": 130_200, "type": "cast", "sourceID": 11, "abilityGameID": 97462},
        ],
        boss_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
        player="战士乙",
        category="团减",
    )
    rows = _csv_rows(format_defense_csv(analysis))
    assert len(rows) == 2
    assert rows[1][2] == "团减"
    assert rows[1][3] == "战士乙"
    assert rows[1][6] == "集结呐喊"


def test_format_defense_csv_header_only_when_no_defense_events() -> None:
    analysis = analyze_timeline(
        _timeline_fight(),
        actors=(ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),),
        abilities={451112: "刺骨尖啸"},
        defense_events=[],
        boss_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )
    text = format_defense_csv(analysis)
    assert text == "时间,偏移毫秒,类别,玩家,专精,职业,技能,技能ID,英文名,目标\n"
    assert "刺骨尖啸" not in text


def test_format_defense_csv_quotes_commas() -> None:
    analysis = TimelineAnalysis(
        fight=_timeline_fight(),
        events=(
            TimelineEvent(
                offset_ms=1_500,
                kind="defense",
                ability="药水, 大瓶",
                ability_id=1,
                category="治疗药水",
                actor="牧师丙",
                ability_en="Potion, Large",
            ),
            TimelineEvent(offset_ms=2_000, kind="boss", ability="刺骨尖啸, 强化"),
        ),
    )
    text = format_defense_csv(analysis)
    assert '"药水, 大瓶"' in text
    assert '"Potion, Large"' in text
    assert "刺骨尖啸" not in text
    rows = _csv_rows(text)
    assert rows[1][6] == "药水, 大瓶"
    assert rows[1][8] == "Potion, Large"
