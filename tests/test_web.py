from wcl_analyzer.html_timeline import render_timeline_html
from wcl_analyzer.models import Fight, TimelineAnalysis, TimelineEvent
from wcl_analyzer.web import analyze_query_string, render_entry_page, render_error_page


def test_render_entry_page_has_form_and_error() -> None:
    html = render_entry_page(
        error="无法识别的报告",
        url="https://cn.warcraftlogs.com/reports/Abcd1234?fight=11",
        fight="11",
    )
    assert "开始分析" in html
    assert 'action="/analyze"' in html
    assert "无法识别的报告" in html
    assert "Abcd1234" in html
    assert 'value="11"' in html
    assert "正在拉取战斗数据" in html


def test_render_error_page_links_home() -> None:
    html = render_error_page("boom", status=404)
    assert "404" in html
    assert "boom" in html
    assert 'href="/"' in html


def test_analyze_query_string() -> None:
    assert analyze_query_string(url="Abcd", fight="12", player="甲") == (
        "/analyze?url=Abcd&fight=12&player=%E7%94%B2"
    )


def test_timeline_home_link_optional() -> None:
    fight = Fight(
        id=12,
        name="虫巢女王",
        encounter_id=2902,
        difficulty=5,
        kill=True,
        start_time=0,
        end_time=60_000,
        fight_percentage=None,
        boss_percentage=0,
        size=20,
        average_item_level=640,
        last_phase=1,
        in_progress=False,
        keystone_level=None,
        phase_transitions=(),
    )
    analysis = TimelineAnalysis(
        fight=fight,
        events=(
            TimelineEvent(
                offset_ms=1000,
                kind="defense",
                ability="寒冰屏障",
                ability_id=45438,
                category="个减",
                actor="法师甲",
                actor_class="Mage",
            ),
        ),
        boss_cds=(),
    )
    plain = render_timeline_html(analysis)
    assert "换一场" not in plain
    assert "__HOME_LINK__" not in plain
    with_home = render_timeline_html(analysis, home_href="/")
    assert 'href="/"' in with_home
    assert "换一场" in with_home
