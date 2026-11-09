import json

import httpx

from wcl_analyzer.client import WclClient


def test_get_report_parses_fights_and_reuses_token() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"access_token": "token-1", "expires_in": 3600})
        body = json.loads(request.content)
        assert body["variables"] == {"code": "Abcd1234"}
        assert request.headers["Authorization"] == "Bearer token-1"
        return httpx.Response(
            200,
            json={
                "data": {
                    "reportData": {
                        "report": {
                            "code": "Abcd1234",
                            "title": "进度之夜",
                            "startTime": 10,
                            "endTime": 20,
                            "owner": {"name": "团长"},
                            "zone": {"name": "尼鲁巴尔王宫"},
                            "fights": [
                                {
                                    "id": 3,
                                    "name": "虫巢女王",
                                    "encounterID": 2902,
                                    "difficulty": 5,
                                    "kill": True,
                                    "startTime": 1000,
                                    "endTime": 2000,
                                    "fightPercentage": None,
                                    "bossPercentage": 0,
                                    "size": 20,
                                    "averageItemLevel": 639.5,
                                    "lastPhase": 3,
                                    "inProgress": False,
                                    "keystoneLevel": 0,
                                }
                            ],
                        }
                    }
                }
            },
        )

    client = WclClient("id", "secret", http=httpx.Client(transport=httpx.MockTransport(handler)))
    first = client.get_report("Abcd1234")
    second = client.get_report("Abcd1234")

    assert first.title == "进度之夜"
    assert first.boss_fights[0].name == "虫巢女王"
    assert first.boss_fights[0].kill is True
    assert second.code == "Abcd1234"
    assert sum(1 for url in calls if url.endswith("/oauth/token")) == 1


def test_get_master_data_includes_ability_icons() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"access_token": "token-1", "expires_in": 3600})
        return httpx.Response(
            200,
            json={
                "data": {
                    "reportData": {
                        "report": {
                            "masterData": {
                                "actors": [
                                    {
                                        "id": 1,
                                        "name": "法师甲",
                                        "type": "Player",
                                        "subType": "Mage",
                                        "server": "测试服",
                                        "petOwner": None,
                                    }
                                ],
                                "abilities": [
                                    {
                                        "gameID": 45438,
                                        "name": "Ice Block",
                                        "icon": "spell_frost_frost.jpg",
                                    }
                                ],
                            }
                        }
                    }
                }
            },
        )

    client = WclClient("id", "secret", http=httpx.Client(transport=httpx.MockTransport(handler)))
    master = client.get_master_data("Abcd1234")
    assert master["abilities"][45438] == "Ice Block"
    assert master["ability_icons"][45438] == "spell_frost_frost.jpg"
    assert master["actors"][0].name == "法师甲"


def test_get_events_follows_next_page_timestamp() -> None:
    pages = [
        {
            "data": [{"timestamp": 1000, "type": "cast", "sourceID": 1, "abilityGameID": 642}],
            "nextPageTimestamp": 1500,
        },
        {
            "data": [{"timestamp": 1600, "type": "cast", "sourceID": 2, "abilityGameID": 45438}],
            "nextPageTimestamp": None,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"access_token": "token-1", "expires_in": 3600})
        body = json.loads(request.content)
        start = body["variables"]["startTime"]
        page = pages.pop(0)
        assert start in {1000, 1500}
        # 默认不拉资源字段；显式打开时才为 true
        assert body["variables"].get("includeResources") in {None, False}
        return httpx.Response(
            200,
            json={"data": {"reportData": {"report": {"events": page}}}},
        )

    from wcl_analyzer.models import Fight

    fight = Fight(
        id=3,
        name="虫巢女王",
        encounter_id=2902,
        difficulty=5,
        kill=True,
        start_time=1000,
        end_time=5000,
        fight_percentage=None,
        boss_percentage=0,
        size=20,
        average_item_level=640,
        last_phase=1,
        in_progress=False,
        keystone_level=None,
    )
    client = WclClient("id", "secret", http=httpx.Client(transport=httpx.MockTransport(handler)))
    events = client.get_events("Abcd1234", fight, data_type="Casts", filter_expression="ability.id in (642)")
    assert len(events) == 2
    assert events[1]["abilityGameID"] == 45438
