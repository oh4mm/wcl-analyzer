from wcl_analyzer.analysis import analyze_fight, select_fight, summarize_bosses
from wcl_analyzer.models import Fight, Report


def _fight(**overrides) -> Fight:
    data = dict(
        id=1,
        name="虫巢女王",
        encounter_id=2902,
        difficulty=5,
        kill=False,
        start_time=10_000,
        end_time=70_000,
        fight_percentage=40.0,
        boss_percentage=60.0,
        size=20,
        average_item_level=639.2,
        last_phase=2,
        in_progress=False,
        keystone_level=None,
    )
    data.update(overrides)
    return Fight(**data)


def _report(*fights: Fight) -> Report:
    return Report(
        code="Abcd1234",
        title="进度之夜",
        start_time=1_700_000_000_000,
        end_time=1_700_003_600_000,
        owner="团长",
        zone_name="尼鲁巴尔王宫",
        fights=fights,
    )


def test_summarize_groups_attempts_and_picks_best_wipe() -> None:
    early = _fight(id=1, fight_percentage=20, boss_percentage=80)
    later = _fight(id=2, fight_percentage=75, boss_percentage=25, end_time=130_000)
    kill = _fight(id=3, kill=True, fight_percentage=None, boss_percentage=0, end_time=250_000)
    trash = _fight(id=4, name="小怪", encounter_id=0, difficulty=None)
    summary = summarize_bosses(_report(early, trash, later, kill))

    assert len(summary) == 1
    assert summary[0].attempts == 3
    assert summary[0].kills == 1
    assert summary[0].fastest_kill_ms == 240_000
    assert summary[0].best_wipe is not None
    assert summary[0].best_wipe.id == 2


def test_select_fight_defaults_to_last_kill() -> None:
    wipe = _fight(id=1)
    kill = _fight(id=2, kill=True)
    another = _fight(id=5, name="下一只", encounter_id=3000, kill=False)
    report = _report(wipe, kill, another)

    assert select_fight(report, None).id == 2
    assert select_fight(report, "last").id == 5
    assert select_fight(report, "1").id == 1


def test_select_fight_explicit_id_allows_trash_and_keystone() -> None:
    trash = _fight(id=9, name="Row Hooligan", encounter_id=0, difficulty=None, kill=None)
    key = _fight(
        id=11,
        name="Murder Row",
        encounter_id=12813,
        difficulty=10,
        keystone_level=22,
        kill=True,
    )
    raid = _fight(id=5, name="Kith'ix", encounter_id=3513, difficulty=4, kill=True)
    report = _report(trash, key, raid)
    assert select_fight(report, "11").name == "Murder Row"
    assert select_fight(report, "11").keystone_level == 22
    assert select_fight(report, "9").id == 9
    assert select_fight(report, "9").encounter_id == 0


def test_select_fight_missing_id_mentions_list_pulls() -> None:
    report = _report(_fight(id=1, kill=True))
    try:
        select_fight(report, "99")
        assert False, "expected ValueError"
    except ValueError as exc:
        message = str(exc)
        assert "99" in message
        assert "list-pulls" in message


def test_analyze_fight_ranks_players_and_deaths() -> None:
    fight = _fight(kill=True, start_time=1_000, end_time=61_000)
    tables = {
        "damageDone": {
            "entries": [
                {
                    "name": "法师甲",
                    "type": "Mage",
                    "icon": "Mage-Fire",
                    "total": 6_000_000,
                    "activeTime": 50_000,
                    "abilities": [{"name": "火焰冲击", "total": 4_000_000}],
                },
                {
                    "name": "宠物",
                    "type": "Pet",
                    "icon": "Pet",
                    "total": 9_000_000,
                },
                {
                    "name": "战士乙",
                    "type": "Warrior",
                    "icon": "Warrior-Fury",
                    "total": 3_000_000,
                    "activeTime": 60_000,
                },
            ],
            "totalTime": 60_000,
        },
        "healing": {
            "data": {
                "entries": [
                    {
                        "name": "牧师丙",
                        "type": "Priest",
                        "icon": "Priest-Holy",
                        "total": 2_000_000,
                        "overheal": 500_000,
                        "activeTime": 60_000,
                    }
                ]
            }
        },
        "damageTaken": {"entries": []},
        "deaths": {
            "entries": [
                {
                    "name": "战士乙",
                    "type": "Warrior",
                    "icon": "Warrior-Protection",
                    "deathTime": 31_000,
                    "ability": {"name": "粉碎"},
                }
            ]
        },
    }

    analysis = analyze_fight(fight, tables)

    assert [row.name for row in analysis.damage] == ["法师甲", "战士乙"]
    assert analysis.damage[0].spec == "火焰法师"
    assert analysis.damage[0].per_second == 100_000
    assert analysis.damage[0].top_ability == "火焰冲击"
    assert analysis.healing[0].overheal_percent == 20
    assert analysis.deaths[0].offset_ms == 30_000
    assert analysis.deaths[0].ability == "粉碎"
    assert analysis.deaths[0].spec == "防护战士"
