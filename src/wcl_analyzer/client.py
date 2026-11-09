from __future__ import annotations

import time
from typing import Any

import httpx

from wcl_analyzer.models import ActorInfo, DungeonPull, Fight, PhaseTransition, Report

TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
GRAPHQL_URL = "https://www.warcraftlogs.com/api/v2/client"

REPORT_QUERY = """
query ReportOverview($code: String!) {
  reportData {
    report(code: $code) {
      code
      title
      startTime
      endTime
      owner { name }
      zone { name }
      fights {
        id
        name
        encounterID
        difficulty
        kill
        startTime
        endTime
        fightPercentage
        bossPercentage
        size
        averageItemLevel
        lastPhase
        inProgress
        keystoneLevel
        phaseTransitions {
          id
          startTime
        }
        dungeonPulls {
          id
          name
          encounterID
          startTime
          endTime
          kill
        }
      }
    }
  }
}
"""

FIGHT_TABLES_QUERY = """
query FightTables($code: String!, $fightIDs: [Int]!) {
  reportData {
    report(code: $code) {
      damageDone: table(fightIDs: $fightIDs, dataType: DamageDone)
      healing: table(fightIDs: $fightIDs, dataType: Healing)
      damageTaken: table(fightIDs: $fightIDs, dataType: DamageTaken)
      deaths: table(fightIDs: $fightIDs, dataType: Deaths)
    }
  }
}
"""

MASTER_DATA_QUERY = """
query ReportMasterData($code: String!) {
  reportData {
    report(code: $code) {
      masterData {
        actors {
          id
          name
          type
          subType
          server
          petOwner
        }
        abilities {
          gameID
          name
          icon
        }
      }
    }
  }
}
"""

EVENTS_QUERY = """
query FightEvents(
  $code: String!
  $fightIDs: [Int]!
  $startTime: Float!
  $endTime: Float!
  $dataType: EventDataType
  $hostilityType: HostilityType
  $filterExpression: String
  $includeResources: Boolean
) {
  reportData {
    report(code: $code) {
      events(
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        dataType: $dataType
        hostilityType: $hostilityType
        filterExpression: $filterExpression
        includeResources: $includeResources
        translate: true
      ) {
        data
        nextPageTimestamp
      }
    }
  }
}
"""


class WclError(RuntimeError):
    pass


class WclClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        http: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http or httpx.Client(timeout=30.0)
        self._owns_http = http is None
        self._token = ""
        self._token_deadline = 0.0

    def __enter__(self) -> WclClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def get_report(self, code: str) -> Report:
        payload = self.query(REPORT_QUERY, {"code": code})
        report = payload["reportData"]["report"]
        if report is None:
            raise WclError(f"找不到报告 {code}。确认代码是否正确，以及日志是否公开。")
        owner = report.get("owner") or {}
        zone = report.get("zone") or {}
        fights = tuple(_fight_from_api(item) for item in report.get("fights") or [])
        return Report(
            code=report.get("code") or code,
            title=report.get("title") or code,
            start_time=float(report.get("startTime") or 0),
            end_time=float(report.get("endTime") or 0),
            owner=owner.get("name"),
            zone_name=zone.get("name"),
            fights=fights,
        )

    def get_fight_tables(self, code: str, fight_id: int) -> dict[str, Any]:
        payload = self.query(FIGHT_TABLES_QUERY, {"code": code, "fightIDs": [fight_id]})
        report = payload["reportData"]["report"]
        if report is None:
            raise WclError(f"找不到报告 {code}。")
        return report

    def get_master_data(self, code: str) -> dict[str, Any]:
        payload = self.query(MASTER_DATA_QUERY, {"code": code})
        report = payload["reportData"]["report"]
        if report is None:
            raise WclError(f"找不到报告 {code}。")
        master = report.get("masterData") or {}
        actors = tuple(_actor_from_api(item) for item in master.get("actors") or [])
        abilities: dict[int, str] = {}
        ability_icons: dict[int, str] = {}
        for item in master.get("abilities") or []:
            if item.get("gameID") is None:
                continue
            game_id = int(item["gameID"])
            abilities[game_id] = item.get("name") or f"#{game_id}"
            icon = item.get("icon")
            if icon:
                # WCL 常见形式：spell_frost_frost.jpg
                ability_icons[game_id] = str(icon)
        return {
            "actors": actors,
            "abilities": abilities,
            "ability_icons": ability_icons,
        }

    def get_events(
        self,
        code: str,
        fight: Fight,
        *,
        data_type: str | None = None,
        hostility_type: str | None = None,
        filter_expression: str | None = None,
        include_resources: bool = False,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> list[dict[str, Any]]:
        """分页拉取一场战斗的事件，直到 nextPageTimestamp 为 null。

        ``include_resources=True`` 才会带上 hitPoints / maxHitPoints（默认关闭，省流量）。
        """
        cursor = fight.start_time if start_time is None else start_time
        end = fight.end_time if end_time is None else end_time
        events: list[dict[str, Any]] = []
        seen_cursors: set[float] = set()

        while True:
            if cursor in seen_cursors:
                break
            seen_cursors.add(cursor)
            variables: dict[str, Any] = {
                "code": code,
                "fightIDs": [fight.id],
                "startTime": cursor,
                "endTime": end,
                "dataType": data_type,
                "hostilityType": hostility_type,
                "filterExpression": filter_expression,
                "includeResources": include_resources or None,
            }
            payload = self.query(EVENTS_QUERY, variables)
            report = payload["reportData"]["report"]
            if report is None:
                raise WclError(f"找不到报告 {code}。")
            page = report.get("events") or {}
            chunk = page.get("data") or []
            if isinstance(chunk, list):
                events.extend(item for item in chunk if isinstance(item, dict))
            next_ts = page.get("nextPageTimestamp")
            if next_ts is None:
                break
            cursor = float(next_ts)
        return events

    def query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = self._post_graphql(query, variables)
        if response.status_code == 401:
            self._token = ""
            response = self._post_graphql(query, variables)
        if response.status_code >= 400:
            raise WclError(f"Warcraft Logs 请求失败（HTTP {response.status_code}）：{response.text[:300]}")
        body = response.json()
        if body.get("errors"):
            message = "; ".join(error.get("message", "未知错误") for error in body["errors"])
            raise WclError(message)
        data = body.get("data")
        if not isinstance(data, dict):
            raise WclError("Warcraft Logs 没有返回数据。")
        return data

    def _post_graphql(self, query: str, variables: dict[str, Any]) -> httpx.Response:
        for attempt in range(4):
            response = self._http.post(
                GRAPHQL_URL,
                headers={"Authorization": f"Bearer {self._access_token()}"},
                json={"query": query, "variables": variables},
            )
            if response.status_code != 429:
                return response
            delay = _retry_delay(response, attempt)
            time.sleep(delay)
        return response

    def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_deadline:
            return self._token
        response = self._http.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
        )
        if response.status_code >= 400:
            raise WclError(
                "Warcraft Logs 认证失败。检查 WCL_CLIENT_ID 和 WCL_CLIENT_SECRET 是否正确。"
            )
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise WclError("Warcraft Logs 没有返回 access_token。")
        expires_in = float(payload.get("expires_in") or 3600)
        self._token = token
        self._token_deadline = time.monotonic() + max(30.0, expires_in - 60.0)
        return token


def _fight_from_api(item: dict[str, Any]) -> Fight:
    transitions = tuple(
        PhaseTransition(id=int(raw["id"]), start_time=float(raw.get("startTime") or 0))
        for raw in item.get("phaseTransitions") or []
        if raw.get("id") is not None
    )
    dungeon_pulls = tuple(
        _dungeon_pull_from_api(raw)
        for raw in item.get("dungeonPulls") or []
        if raw.get("id") is not None
    )
    return Fight(
        id=int(item["id"]),
        name=item.get("name") or "未知战斗",
        encounter_id=int(item.get("encounterID") or 0),
        difficulty=_optional_int(item.get("difficulty")),
        kill=item.get("kill"),
        start_time=float(item.get("startTime") or 0),
        end_time=float(item.get("endTime") or 0),
        fight_percentage=_optional_float(item.get("fightPercentage")),
        boss_percentage=_optional_float(item.get("bossPercentage")),
        size=_optional_int(item.get("size")),
        average_item_level=_optional_float(item.get("averageItemLevel")),
        last_phase=_optional_int(item.get("lastPhase")),
        in_progress=bool(item.get("inProgress")),
        keystone_level=_positive_int(item.get("keystoneLevel")),
        phase_transitions=transitions,
        dungeon_pulls=dungeon_pulls,
    )


def _dungeon_pull_from_api(item: dict[str, Any]) -> DungeonPull:
    return DungeonPull(
        id=int(item["id"]),
        name=item.get("name") or "未知",
        encounter_id=int(item.get("encounterID") or 0),
        start_time=float(item.get("startTime") or 0),
        end_time=float(item.get("endTime") or 0),
        kill=item.get("kill"),
    )


def _actor_from_api(item: dict[str, Any]) -> ActorInfo:
    return ActorInfo(
        id=int(item["id"]),
        name=item.get("name") or "未知",
        type=item.get("type") or "Unknown",
        sub_type=item.get("subType"),
        pet_owner=_optional_int(item.get("petOwner")),
        server=item.get("server"),
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _positive_int(value: Any) -> int | None:
    number = _optional_int(value)
    if number is None or number <= 0:
        return None
    return number


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return max(0.5, float(header))
        except ValueError:
            pass
    return float(2**attempt)
