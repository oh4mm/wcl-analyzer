import pytest

from wcl_analyzer.analysis import resolve_fight_token, select_fight
from wcl_analyzer.models import Fight, Report
from wcl_analyzer.refs import parse_report_ref


def _fight(**overrides) -> Fight:
    data = dict(
        id=1,
        name="虫巢女王",
        encounter_id=2902,
        difficulty=5,
        kill=False,
        start_time=0,
        end_time=100_000,
        fight_percentage=40.0,
        boss_percentage=60.0,
        size=20,
        average_item_level=640,
        last_phase=1,
        in_progress=False,
        keystone_level=None,
        phase_transitions=(),
    )
    data.update(overrides)
    return Fight(**data)


def test_bare_code() -> None:
    ref = parse_report_ref("aB3xYz0123456789")
    assert ref.code == "aB3xYz0123456789"
    assert ref.fight is None


def test_report_url_with_fight_fragment() -> None:
    ref = parse_report_ref(
        "https://www.warcraftlogs.com/reports/aB3xYz0123456789#fight=12&type=damage-done"
    )
    assert ref.code == "aB3xYz0123456789"
    assert ref.fight == "12"


def test_report_url_with_fight_query() -> None:
    ref = parse_report_ref(
        "https://www.warcraftlogs.com/reports/aB3xYz0123456789?fight=5&type=damage-done"
    )
    assert ref.code == "aB3xYz0123456789"
    assert ref.fight == "5"


def test_fragment_wins_over_stale_query() -> None:
    ref = parse_report_ref(
        "https://www.warcraftlogs.com/reports/aB3xYz0123456789?fight=last#fight=5&type=damage-done"
    )
    assert ref.fight == "5"


def test_encoded_hash_fragment_still_parses() -> None:
    ref = parse_report_ref(
        "https://www.warcraftlogs.com/reports/aB3xYz0123456789%23fight=12&type=damage-done"
    )
    assert ref.code == "aB3xYz0123456789"
    assert ref.fight == "12"


def test_cn_url_and_last_fight() -> None:
    ref = parse_report_ref("https://cn.warcraftlogs.com/reports/Abcd1234?fight=last")
    assert ref.code == "Abcd1234"
    assert ref.fight == "last"


def test_rejects_empty_code() -> None:
    with pytest.raises(ValueError):
        parse_report_ref("https://www.warcraftlogs.com/reports/")


def test_url_fight_selects_exact_pull_not_last_kill() -> None:
    """链接 #fight=5 必须选中 5，不能落到最后一次击杀。"""
    report = Report(
        code="aB3xYz0123456789",
        title="进度之夜",
        start_time=1,
        end_time=2,
        owner="团长",
        zone_name="测试",
        fights=(
            _fight(id=5, kill=False, end_time=90_000),
            _fight(id=8, kill=True, end_time=200_000),
            _fight(id=12, kill=True, end_time=300_000),
        ),
    )
    url = "https://www.warcraftlogs.com/reports/aB3xYz0123456789#fight=5&type=damage-done"
    ref = parse_report_ref(url)
    token = resolve_fight_token(fight=None, pull=None, ref_fight=ref.fight)
    assert token == "5"
    assert select_fight(report, token).id == 5
    # 省略 fight 时才是最后一次击杀
    assert select_fight(report, None).id == 12


def test_cli_fight_overrides_url_fight() -> None:
    assert (
        resolve_fight_token(fight="12", pull=None, ref_fight="5") == "12"
    )
    assert (
        resolve_fight_token(fight=None, pull="12", ref_fight="5") == "12"
    )
    assert resolve_fight_token(fight=None, pull=None, ref_fight="5") == "5"


def test_cn_query_fight_selects_mplus_not_raid_kill() -> None:
    """cn.warcraftlogs.com?fight=11 必须选中钥石场，不能落到同报告里的团本击杀。"""
    report = Report(
        code="FkZJD26b9aAndCRr",
        title="The Venomous Abyss",
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
            _fight(
                id=41,
                name="Murder Row",
                encounter_id=12813,
                difficulty=10,
                keystone_level=23,
                kill=False,
                end_time=3_000_000,
            ),
        ),
    )
    url = (
        "https://cn.warcraftlogs.com/reports/FkZJD26b9aAndCRr"
        "?fight=11&type=damage-done"
    )
    ref = parse_report_ref(url)
    assert ref.code == "FkZJD26b9aAndCRr"
    assert ref.fight == "11"
    token = resolve_fight_token(fight=None, pull=None, ref_fight=ref.fight)
    selected = select_fight(report, token)
    assert selected.id == 11
    assert selected.name == "Murder Row"
    assert selected.keystone_level == 22
    # 没有显式 fight 时仍是「最后一次击杀」= 本例中的钥石 11（不是团本 5）
    assert select_fight(report, None).id == 11
