from wcl_analyzer.format import format_amount, format_duration, format_report
from wcl_analyzer.models import Fight, Report


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
