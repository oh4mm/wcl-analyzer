from pathlib import Path

from wcl_analyzer.models import ActorInfo, Fight, TimelineEvent
from wcl_analyzer.spell_meta import (
    SpellMetaStore,
    enrich_timeline_metadata,
    icon_url,
    normalize_icon,
    parse_effect_duration_ms,
    parse_wowhead_tooltip,
    summarize_boss_cds,
)
from wcl_analyzer.timeline import analyze_timeline


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
        last_phase=1,
        in_progress=False,
        keystone_level=None,
        phase_transitions=(),
    )
    data.update(overrides)
    return Fight(**data)


def _actors() -> tuple[ActorInfo, ...]:
    return (
        ActorInfo(id=1, name="虫巢女王", type="NPC", sub_type="Boss"),
        ActorInfo(id=10, name="法师甲", type="Player", sub_type="Mage"),
    )


def test_detail_cache_version_invalidates_all_spell_descriptions(tmp_path: Path) -> None:
    """说明解析升级后，缓存中所有技能的旧 description 都应失效并重拉。"""
    cache = tmp_path / "cache.json"
    cache.write_text(
        """
{
  "108271": {
    "name_zh": "星界转移",
    "description": "秒。",
    "cast_label": "瞬发",
    "detail_fetched": "1",
    "detail_version": "1"
  },
  "871": {
    "name_zh": "盾墙",
    "description": "ec.",
    "detail_fetched": "1"
  }
}
""".strip(),
        encoding="utf-8",
    )
    calls: list[int] = []

    def fetcher(spell_id: int, locale: int) -> dict | None:
        calls.append(spell_id)
        if locale != 4:
            return {"name": "x"}
        if spell_id == 108271:
            return {
                "name": "星界转移",
                "tooltip": (
                    '<div class="q">将部分身体移入元素位面，'
                    "使受到的伤害降低40%，持续12秒。</div>"
                ),
            }
        if spell_id == 871:
            return {
                "name": "盾墙",
                "tooltip": '<div class="q">你受到的所有伤害降低40%，持续8秒。</div>',
            }
        return None

    store = SpellMetaStore(cache_path=cache, fetch=True, fetcher=fetcher)
    astral = store.resolve(108271)
    wall = store.resolve(871)
    assert astral is not None and astral.description is not None
    assert astral.description.startswith("将部分身体移入元素位面")
    assert wall is not None and wall.description is not None
    assert "伤害降低40%" in wall.description
    assert 108271 in calls and 871 in calls


def test_parse_effect_duration_ms() -> None:
    assert parse_effect_duration_ms("持续12秒") == 12_000
    assert parse_effect_duration_ms("持续1.5分钟") == 90_000
    assert parse_effect_duration_ms("直到取消") is None
    assert parse_effect_duration_ms(None) is None


def test_scrub_talent_instant_english_prefix() -> None:
    from wcl_analyzer.spell_meta import scrub_spell_description

    cleaned = scrub_spell_description(
        "TalentInstantSurrounds you in a block of ice for 10 sec.",
        spell_name="Ice Block",
    )
    assert cleaned is not None
    assert not cleaned.startswith("Talent")
    assert "Surrounds you" in cleaned

    # 纯英文说明在入库前会被丢弃；这里只验证前缀剥离
    assert scrub_spell_description("TalentInstant") is None


def test_parse_compact_cn_and_html_descriptions() -> None:
    """中文 Wowhead 常把元信息粘成一行；应以 HTML div.q / 需要职业 正确切分。"""
    astral_html = (
        '<table><tr><td><b class="whtt-name">星界转移</b>'
        '<div class="q0">天赋</div>'
        "<table><tr><td>瞬发</td><th>2分钟 冷却</th></tr></table>"
        '<div class="wowhead-tooltip-requirements">需要 萨满</div></td></tr></table>'
        '<table><tr><td><div class="q">将部分身体移入元素位面，'
        "使受到的伤害降低<!--sp377933:0-->40<!--sp377933-->%，持续12秒。</div>"
        "</td></tr></table>"
    )
    astral = parse_wowhead_tooltip(astral_html, spell_name="星界转移")
    assert astral.cast_label == "瞬发"
    assert astral.duration_label == "持续12秒"
    assert astral.description is not None
    assert astral.description.startswith("将部分身体移入元素位面")
    assert "40%" in astral.description
    assert "需要" not in astral.description

    earth_html = (
        '<b class="whtt-name">土元素</b><div class="q0">天赋</div>40 码范围'
        "<table><tr><td>瞬发</td><th>3分钟 冷却</th></tr></table>"
        '<div class="wowhead-tooltip-requirements">需要 萨满</div>'
        '<div class="q">召唤一个巨型土元素保护你和你的盟友，'
        "产生大量威胁值并周期性嘲讽敌人，持续30秒。</div>"
    )
    earth = parse_wowhead_tooltip(earth_html, spell_name="土元素")
    assert earth.cast_label == "瞬发"
    assert earth.duration_label == "持续30秒"
    assert earth.description is not None
    assert earth.description.startswith("召唤一个巨型土元素")
    assert earth.description.endswith("持续30秒。") or "持续30秒" in earth.description


def test_parse_wowhead_tooltip_instant_and_duration() -> None:
    ice = parse_wowhead_tooltip(
        "寒冰屏障<br>天赋<br>瞬发<br>4​分钟 冷却<br>"
        "一道寒冰屏障笼罩了你，使你在10秒内不会受到任何伤害。<br>持续10秒。",
        spell_name="寒冰屏障",
    )
    assert ice.cast_label == "瞬发"
    assert ice.is_instant is True
    assert ice.duration_label == "持续10秒"
    assert ice.description is not None
    assert "不会受到任何伤害" in ice.description

    poly = parse_wowhead_tooltip(
        "变形术<br>30 码范围<br>1.7​秒 施法时间<br>将敌人变成一只绵羊，瘫痪1分钟。",
        spell_name="变形术",
    )
    assert poly.cast_label == "1.7秒施法"
    assert poly.is_instant is False
    assert poly.description is not None
    assert "绵羊" in poly.description

    stance = parse_wowhead_tooltip(
        "防御姿态<br>瞬发<br>效果一直持续直到主动取消。",
        spell_name="防御姿态",
    )
    assert stance.cast_label == "瞬发"
    assert stance.duration_label == "直到取消"


def test_normalize_icon_and_cdn_url() -> None:
    assert normalize_icon("spell_frost_frost.jpg") == "spell_frost_frost"
    assert normalize_icon("inv_foo.jpg.jpg") == "inv_foo"
    assert normalize_icon("Ability/Spell_Frost_Frost") == "spell_frost_frost"
    assert normalize_icon(
        "https://wow.zamimg.com/images/wow/icons/large/spell_shadow_psychicscream.jpg"
    ) == "spell_shadow_psychicscream"
    assert icon_url("spell_frost_frost") == (
        "https://wow.zamimg.com/images/wow/icons/large/spell_frost_frost.jpg"
    )
    assert icon_url("spell_frost_frost.jpg") == (
        "https://wow.zamimg.com/images/wow/icons/large/spell_frost_frost.jpg"
    )
    assert icon_url(None) is None


def test_spell_meta_store_uses_seed_and_mock_fetch(tmp_path: Path) -> None:
    cache = tmp_path / "cache.json"
    calls: list[tuple[int, int]] = []

    def fetcher(spell_id: int, locale: int) -> dict | None:
        calls.append((spell_id, locale))
        if locale == 4:
            return {
                "name": "刺骨尖啸",
                "icon": "spell_shadow_psychicscream",
                "tooltip": "刺骨尖啸<br>瞬发<br>发出刺骨尖啸，持续6秒。",
            }
        return {"name": "Piercing Screech", "icon": "spell_shadow_psychicscream"}

    store = SpellMetaStore(cache_path=cache, fetch=True, fetcher=fetcher)
    meta = store.resolve(451112, fallback_name="Piercing Screech")
    assert meta is not None
    assert meta.name_zh == "刺骨尖啸"
    assert meta.name_en == "Piercing Screech"
    assert meta.icon == "spell_shadow_psychicscream"
    assert meta.cast_label == "瞬发"
    assert meta.duration_label == "持续6秒"
    assert meta.description is not None
    store.flush()
    assert cache.is_file()

    store2 = SpellMetaStore(cache_path=cache, fetch=True, fetcher=fetcher)
    again = store2.resolve(451112)
    assert again is not None
    assert again.name_zh == "刺骨尖啸"
    assert again.cast_label == "瞬发"
    assert len(calls) == 2  # zh + en once


def test_spell_meta_fetch_failure_falls_back(tmp_path: Path) -> None:
    def fetcher(spell_id: int, locale: int) -> dict | None:
        return None

    store = SpellMetaStore(cache_path=tmp_path / "empty.json", fetch=True, fetcher=fetcher)
    meta = store.resolve(999001, fallback_name="Weird Boss Bolt")
    assert meta is not None
    assert meta.name_en == "Weird Boss Bolt"
    assert meta.icon is None


def test_summarize_boss_cds_intervals_and_median() -> None:
    events = [
        TimelineEvent(0, "boss", "尖啸", ability_id=1),
        TimelineEvent(30_000, "boss", "尖啸", ability_id=1),
        TimelineEvent(50_000, "boss", "尖啸", ability_id=1),
        TimelineEvent(10_000, "boss", "扫尾", ability_id=2),
        TimelineEvent(5_000, "defense", "寒冰屏障", ability_id=45438, category="个减"),
    ]
    cds = summarize_boss_cds(events)
    assert len(cds) == 2
    scream = next(item for item in cds if item.ability_id == 1)
    assert scream.cast_count == 3
    assert scream.intervals_ms == (30_000, 20_000)
    assert scream.median_interval_ms == 25_000
    assert scream.min_interval_ms == 20_000
    assert scream.max_interval_ms == 30_000
    sweep = next(item for item in cds if item.ability_id == 2)
    assert sweep.cast_count == 1
    assert sweep.intervals_ms == ()
    assert sweep.median_interval_ms is None


def test_enrich_timeline_applies_zh_and_icons(tmp_path: Path) -> None:
    fight = _fight()
    analysis = analyze_timeline(
        fight,
        actors=_actors(),
        abilities={451112: "Piercing Screech", 45438: "Ice Block"},
        defense_events=[
            {"timestamp": 120_000, "type": "cast", "sourceID": 10, "abilityGameID": 45438},
        ],
        boss_events=[
            {"timestamp": 130_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
            {"timestamp": 160_000, "type": "cast", "sourceID": 1, "abilityGameID": 451112},
        ],
    )

    def fetcher(spell_id: int, locale: int) -> dict | None:
        if spell_id == 451112:
            if locale == 4:
                return {
                    "name": "刺骨尖啸",
                    "icon": "ability_warrior_warcry",
                    "tooltip": "刺骨尖啸<br>1.5​秒 施法时间<br>发出尖啸。",
                }
            return {"name": "Piercing Screech", "icon": "ability_warrior_warcry"}
        if spell_id == 45438 and locale == 4:
            return {
                "name": "寒冰屏障",
                "icon": "spell_frost_frost",
                "tooltip": "寒冰屏障<br>瞬发<br>使你在10秒内免疫伤害。<br>持续10秒。",
            }
        return None

    store = SpellMetaStore(cache_path=tmp_path / "c.json", fetch=True, fetcher=fetcher)
    store.seed_icons({45438: "spell_frost_frost.jpg"})
    enriched = enrich_timeline_metadata(analysis, store, fetch=True)

    boss = [event for event in enriched.events if event.kind == "boss"]
    assert all(event.ability == "刺骨尖啸" for event in boss)
    assert all(event.icon == "ability_warrior_warcry" for event in boss)
    assert all(event.cast_label == "1.5秒施法" for event in boss)
    defense = next(event for event in enriched.events if event.kind == "defense")
    assert defense.ability == "寒冰屏障"
    assert defense.icon == "spell_frost_frost"
    assert defense.cast_label == "瞬发"
    assert defense.duration_label == "持续10秒"
    assert defense.duration_ms == 10_000
    assert defense.description is not None
    assert enriched.boss_cds
    assert enriched.boss_cds[0].ability == "刺骨尖啸"
    assert enriched.boss_cds[0].median_interval_ms == 30_000
