from wcl_analyzer.cli import main
from wcl_analyzer.models import Fight, TimelineAnalysis, TimelineEvent


def _fight() -> Fight:
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


def test_timeline_export_csv_writes_file(tmp_path, monkeypatch, capsys) -> None:
    analysis = TimelineAnalysis(
        fight=_fight(),
        events=(
            TimelineEvent(offset_ms=0, kind="phase", ability="阶段 1"),
            TimelineEvent(
                offset_ms=10_000,
                kind="defense",
                ability="寒冰屏障",
                ability_id=45438,
                category="个减",
                actor="法师甲",
                spec="法师",
                actor_class="Mage",
                target="自身",
            ),
            TimelineEvent(offset_ms=20_000, kind="boss", ability="刺骨尖啸"),
        ),
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_report(self, code: str):
            assert code == "Abcd1234"
            return object()

    monkeypatch.setattr("wcl_analyzer.cli.credentials", lambda: ("id", "secret"))
    monkeypatch.setattr("wcl_analyzer.cli.WclClient", lambda *args, **kwargs: FakeClient())
    monkeypatch.setattr(
        "wcl_analyzer.cli.build_timeline_analysis",
        lambda *args, **kwargs: analysis,
    )

    dest = tmp_path / "nested" / "out.csv"
    code = main(["timeline", "Abcd1234", "--pull", "12", "--export-csv", str(dest)])
    assert code == 0
    assert dest.read_bytes().startswith(b"\xef\xbb\xbf")
    text = dest.read_text(encoding="utf-8-sig")
    assert text.startswith("时间,偏移毫秒,")
    assert "寒冰屏障" in text
    assert "法师甲" in text
    assert "刺骨尖啸" not in text
    assert "阶段" not in text
    captured = capsys.readouterr()
    assert f"已导出减伤 / 药水事件：{dest.resolve()}（1 条）" in captured.out
    assert "减伤 / 药水时间线" not in captured.out
