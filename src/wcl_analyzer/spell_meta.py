"""按 spell ID 解析图标与中文名（Wowhead + 本地缓存）。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

import httpx

from wcl_analyzer.defenses import DEFENSE_ABILITIES, lookup_defense
from wcl_analyzer.models import BossAbilityCd, TimelineAnalysis, TimelineEvent

ICON_CDN_TMPL = "https://wow.zamimg.com/images/wow/icons/{size}/{icon}.jpg"
WOWHEAD_TOOLTIP_TMPL = (
    "https://nether.wowhead.com/tooltip/spell/{spell_id}?dataEnv=1&locale={locale}"
)
# Wowhead locale：0=enUS，4=zhCN
_LOCALE_ZH = 4
_LOCALE_EN = 0

_PACKAGE_CACHE = Path(__file__).resolve().parent / "data" / "spell_cache.json"
_USER_CACHE = Path.home() / ".cache" / "wcl-analyzer" / "spell_cache.json"

# 失败 ID 短期记忆，避免同一进程反复打 Wowhead
_NEGATIVE_CACHE: set[int] = set()

# 技能说明解析策略版本：升级后清空旧 description，让全部技能按新逻辑重拉
# v2 = 优先解析 Wowhead HTML div.q（修复粘连「天赋瞬发需要职业」误吞正文）
_DETAIL_CACHE_VERSION = "2"


@dataclass(frozen=True)
class SpellMeta:
    spell_id: int
    name_zh: str | None = None
    name_en: str | None = None
    icon: str | None = None
    description: str | None = None
    cast_label: str | None = None
    duration_label: str | None = None

    @property
    def display_name(self) -> str:
        return self.name_zh or self.name_en or f"#{self.spell_id}"


@dataclass(frozen=True)
class ParsedSpellTooltip:
    description: str | None = None
    cast_label: str | None = None
    duration_label: str | None = None
    is_instant: bool | None = None


_TOOLTIP_TAG_RE = re.compile(r"<[^>]+>")
_TOOLTIP_BR_RE = re.compile(r"<br\s*/?>", re.I)
_TOOLTIP_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
# Wowhead 用注释夹数值：<!--spX:0-->40<!--spX-->
_TOOLTIP_SP_VALUE_RE = re.compile(r"<!--[^>]*:0-->([^<]*)<!--[^>]*-->")
_TOOLTIP_DESC_DIV_RE = re.compile(
    r'<div class="q">(.*?)</div>',
    re.I | re.S,
)
_CAST_INSTANT_RE = re.compile(r"瞬发|(?<![A-Za-z])Instant(?![A-Za-z])", re.I)
_CAST_TIME_CN_RE = re.compile(r"([\d.]+)\s*秒\s*施法(?:时间)?")
_CAST_TIME_EN_RE = re.compile(r"([\d.]+)\s*sec(?:ond)?s?\s*cast", re.I)
_DURATION_UNTIL_CANCEL_RE = re.compile(
    r"(?:效果一直持续直到主动取消|直到主动取消|直到取消|Lasts until cancelled|until canceled)",
    re.I,
)
_DURATION_CN_RE = re.compile(r"持续\s*([\d.]+)\s*(分钟|秒|小时)")
_DURATION_CN_WITHIN_RE = re.compile(r"在\s*([\d.]+)\s*(分钟|秒|小时)\s*内")
_DURATION_EN_RE = re.compile(
    r"(?:Lasts|for|lasting)\s*([\d.]+)\s*(sec(?:ond)?s?|min(?:ute)?s?|hour?s?)",
    re.I,
)
_PLAYER_CLASS_CN = (
    "死亡骑士|恶魔猎手|德鲁伊|唤魔师|猎人|法师|武僧|圣骑士|牧师|潜行者|萨满|术士|战士"
)
_PLAYER_CLASS_EN = (
    "Death\\s*Knight|Demon\\s*Hunter|Druid|Evoker|Hunter|Mage|Monk|"
    "Paladin|Priest|Rogue|Shaman|Warlock|Warrior"
)
# 粘连文本里「需要 萨满」后的正文；职业名后立即跟说明，不能用 [^\n]{0,40} 吞掉
_REQUIRE_SPLIT_CN_RE = re.compile(rf"需要\s*(?:{_PLAYER_CLASS_CN})")
_REQUIRE_SPLIT_EN_RE = re.compile(rf"Requires\s+(?:{_PLAYER_CLASS_EN})", re.I)
_DESC_META_PREFIX_RE = re.compile(
    r"^(?:"
    r"Talent|"
    r"Passive|"
    r"天赋|"
    r"被动|"
    r"等级\s*\d+|"
    r"Rank\s*\d+|"
    r"\[Item Effect\]|"
    r"Item Effect|"
    r"\d+\s*码范围|"
    r"\d+(?:\.\d+)?\s*(?:yd|yard)s?\s*range|"
    r"\d+%\s*法力值(?:\s*值)?|"
    r"\d+(?:\.\d+)?\s*%?\s*(?:of\s+base\s+)?mana|"
    r"瞬发|"
    r"Instant|"
    r"[\d.]+\s*秒\s*施法(?:时间)?|"
    r"[\d.]+\s*sec(?:ond)?s?\s*cast(?:\s*time)?|"
    r"\d+\s*(?:分钟|秒)\s*冷却|"
    r"\d+\s*min(?:ute)?s?\s*cooldown|"
    r"\d+\s*次充能|"
    r"\d+\s*Charges?"
    r")+",
    re.I,
)
# Wowhead 英文 tooltip 常把 Talent + Instant 粘成 TalentInstant
_GLUED_EN_META_RE = re.compile(
    r"^(?:Talent|Instant|Passive|Cast(?:Time)?|Cooldown|Recharge|Requires|Rank\d*)+",
    re.I,
)


def tooltip_html_to_text(tooltip_html: str | None) -> str:
    if not tooltip_html:
        return ""
    text = _normalize_wowhead_html_fragment(str(tooltip_html))
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_wowhead_html_fragment(fragment: str) -> str:
    """去掉 Wowhead 注释/标签，保留 <!--sp:0-->数值<!--sp--> 中的数值。"""
    text = _TOOLTIP_SP_VALUE_RE.sub(r"\1", fragment)
    text = _TOOLTIP_COMMENT_RE.sub("", text)
    text = _TOOLTIP_BR_RE.sub("\n", text)
    text = _TOOLTIP_TAG_RE.sub("", text)
    return (
        text.replace("\u200b", "")
        .replace("\xa0", " ")
        .replace("&nbsp;", " ")
        .replace("&nbsp", " ")
    )


def parse_wowhead_tooltip(
    tooltip_html: str | None,
    *,
    spell_name: str | None = None,
) -> ParsedSpellTooltip:
    """从 Wowhead tooltip HTML 提取说明、是否瞬发/施法时间、效果持续。

    优先解析 HTML 结构（``div.q`` 正文），避免中文 tooltip 把
    「天赋瞬发需要 萨满」与说明粘成一行后被正则误吞。
    """
    if not tooltip_html:
        return ParsedSpellTooltip()

    html = str(tooltip_html)
    description = _extract_html_description(html)
    cast_label, is_instant = _extract_cast_label(html)
    duration_label = _extract_duration_label(description or "") if description else None

    text = tooltip_html_to_text(html)
    if not cast_label:
        cast_label, is_instant = _extract_cast_label(text)
    if not duration_label:
        duration_label = _extract_duration_label(text)
    if not description and text:
        description = scrub_spell_description(text, spell_name=spell_name)

    return ParsedSpellTooltip(
        description=description,
        cast_label=cast_label,
        duration_label=duration_label,
        is_instant=is_instant,
    )


def _extract_html_description(tooltip_html: str) -> str | None:
    """取 Wowhead 技能正文：通常在要求行之后的 ``<div class="q">``。"""
    candidates: list[str] = []
    for match in _TOOLTIP_DESC_DIV_RE.finditer(tooltip_html):
        cleaned = scrub_spell_description(_normalize_wowhead_html_fragment(match.group(1)))
        if cleaned and not _is_garbage_description(cleaned):
            candidates.append(cleaned)
    if not candidates:
        return None
    # 取最长的一段正文（名称旁的短 q 类样式较少见；正文通常最长）
    return max(candidates, key=len)


def _extract_cast_label(text: str) -> tuple[str | None, bool | None]:
    cast_cn = _CAST_TIME_CN_RE.search(text)
    cast_en = _CAST_TIME_EN_RE.search(text)
    if cast_cn:
        return f"{_format_seconds_label(cast_cn.group(1))}秒施法", False
    if cast_en:
        return f"{_format_seconds_label(cast_en.group(1))}秒施法", False
    if _CAST_INSTANT_RE.search(text):
        return "瞬发", True
    return None, None


def parse_effect_duration_ms(duration_label: str | None) -> float | None:
    """把「持续12秒 / 持续1分钟」转成毫秒；直到取消 / 无法解析则返回 None。"""
    if not duration_label:
        return None
    text = str(duration_label).strip()
    if not text or "直到取消" in text:
        return None
    match = re.search(r"持续\s*([\d.]+)\s*(小时|分钟|秒)", text)
    if not match:
        match = re.search(r"([\d.]+)\s*(小时|分钟|秒)", text)
    if not match:
        return None
    try:
        amount = float(match.group(1))
    except ValueError:
        return None
    unit = match.group(2)
    if unit == "小时":
        return amount * 3_600_000.0
    if unit == "分钟":
        return amount * 60_000.0
    return amount * 1_000.0


def _extract_duration_label(text: str) -> str | None:
    if not text:
        return None
    if _DURATION_UNTIL_CANCEL_RE.search(text):
        return "直到取消"
    duration_cn = _DURATION_CN_RE.search(text) or _DURATION_CN_WITHIN_RE.search(text)
    if duration_cn:
        amount, unit = duration_cn.group(1), duration_cn.group(2)
        return f"持续{_format_seconds_label(amount)}{unit}"
    duration_en = _DURATION_EN_RE.search(text)
    if duration_en:
        amount, unit = duration_en.group(1), duration_en.group(2).lower()
        if unit.startswith("min"):
            zh_unit = "分钟"
        elif unit.startswith("hour"):
            zh_unit = "小时"
        else:
            zh_unit = "秒"
        return f"持续{_format_seconds_label(amount)}{zh_unit}"
    return None


def _format_seconds_label(raw: str) -> str:
    try:
        number = float(raw)
    except ValueError:
        return raw
    if number.is_integer():
        return str(int(number))
    text = f"{number:.2f}".rstrip("0").rstrip(".")
    return text


def _extract_description(text: str, *, spell_name: str | None) -> str | None:
    return scrub_spell_description(text, spell_name=spell_name)


def scrub_spell_description(
    text: str | None,
    *,
    spell_name: str | None = None,
) -> str | None:
    """去掉 TalentInstant / 天赋瞬发 等开头元信息，只保留技能说明正文。"""
    if not text:
        return None
    body = str(text).strip()
    if not body:
        return None
    if spell_name:
        name = spell_name.strip()
        if name and body.startswith(name):
            body = body[len(name) :].lstrip(" \n\r\t:：-")

    # 粘连中文：……需要 萨满将部分身体…… → 从职业名后开始取正文
    require_cn = _REQUIRE_SPLIT_CN_RE.search(body)
    if require_cn:
        body = body[require_cn.end() :].lstrip(" \n\r\t，,;；")
    else:
        require_en = _REQUIRE_SPLIT_EN_RE.search(body)
        if require_en:
            body = body[require_en.end() :].lstrip(" \n\r\t，,;；")

    # 反复剥掉开头的施法/冷却/范围，以及粘连的 TalentInstant
    for _ in range(12):
        updated = _GLUED_EN_META_RE.sub("", body, count=1)
        updated = _DESC_META_PREFIX_RE.sub("", updated, count=1)
        updated = updated.lstrip(" \n\r\t，,;；|/-+")
        if updated == body:
            break
        body = updated
    body = re.sub(r"[ \t]{2,}", " ", body).strip()
    body = re.sub(r"\n{2,}", "\n", body)
    if not body or _is_garbage_description(body):
        return None
    # 仍以英文元信息开头则视为无效说明
    if _GLUED_EN_META_RE.match(body):
        return None
    # 悬停提示不宜过长
    if len(body) > 280:
        body = body[:277].rstrip() + "…"
    return body


def _is_mostly_english(text: str) -> bool:
    """没有中日韩字符、却有连续拉丁词，视为英文说明。"""
    if _looks_chinese(text):
        return False
    return bool(re.search(r"[A-Za-z]{3,}", text))


def _is_garbage_description(text: str) -> bool:
    """被旧正则啃剩的碎片（如「秒。」「ec.」）视为无效。"""
    cleaned = text.strip()
    if len(cleaned) < 8:
        return True
    if cleaned in {"秒。", "秒", "ec.", "。", "...", "…"}:
        return True
    if re.fullmatch(r"[。.\s秒sec]+", cleaned, re.I):
        return True
    return False


_ICON_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def normalize_icon(icon: str | None) -> str | None:
    """把 Wowhead / WCL 的 icon 字段收成 CDN 文件名（无扩展名、小写）。

    兼容：``inv_foo``、``inv_foo.jpg``、带路径的 URL、重复扩展名 ``.jpg.jpg``。
    """
    if not icon:
        return None
    name = str(icon).strip()
    if not name:
        return None
    # 已是完整 CDN / 站点 URL 时只取最后一段文件名
    if "/" in name or "\\" in name:
        name = name.replace("\\", "/").rsplit("/", 1)[-1]
    # 反复剥扩展名，避免 seed 里写成 inv_foo.jpg 后又拼出 .jpg.jpg
    lowered = name.lower()
    while any(lowered.endswith(suffix) for suffix in _ICON_SUFFIXES):
        name = name.rsplit(".", 1)[0]
        lowered = name.lower()
    # Wow 图标名用下划线；空格 / 点统一成下划线
    name = name.strip().lower().replace(" ", "_").replace(".", "_")
    name = name.strip("_")
    return name or None


def icon_url(icon: str | None, *, size: str = "large") -> str | None:
    """拼 Wowhead CDN 地址。``size`` 常用 ``large`` / ``medium`` / ``small``。"""
    normalized = normalize_icon(icon)
    if not normalized:
        return None
    safe_size = size if size in {"large", "medium", "small", "tiny"} else "large"
    return ICON_CDN_TMPL.format(size=safe_size, icon=normalized)


def default_user_cache_path() -> Path:
    return _USER_CACHE


class SpellMetaStore:
    """合并包内种子缓存、用户缓存、WCL 图标与 Wowhead 查询。"""

    def __init__(
        self,
        *,
        cache_path: Path | None = None,
        http: httpx.Client | None = None,
        fetch: bool = True,
        fetcher: Callable[[int, int], dict[str, Any] | None] | None = None,
    ) -> None:
        self._cache_path = cache_path or default_user_cache_path()
        self._fetch = fetch
        self._http = http
        self._owns_http = http is None
        self._fetcher = fetcher
        self._entries: dict[int, dict[str, str | None]] = {}
        self._dirty = False
        self._load_seed(_PACKAGE_CACHE)
        self._load_seed(self._cache_path)
        self._seed_from_defenses()
        self._invalidate_stale_detail_cache()

    def close(self) -> None:
        self.flush()
        if self._owns_http and self._http is not None:
            self._http.close()
            self._http = None

    def __enter__(self) -> SpellMetaStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def seed_icons(self, icons: dict[int, str] | None) -> None:
        if not icons:
            return
        for spell_id, icon in icons.items():
            normalized = normalize_icon(icon)
            if not normalized:
                continue
            entry = self._entries.setdefault(int(spell_id), {})
            if entry.get("icon") != normalized:
                entry["icon"] = normalized
                self._dirty = True

    def seed_names(
        self,
        names: dict[int, str] | None,
        *,
        as_zh: bool = False,
    ) -> None:
        if not names:
            return
        field = "name_zh" if as_zh else "name_en"
        for spell_id, name in names.items():
            if not name:
                continue
            entry = self._entries.setdefault(int(spell_id), {})
            if not entry.get(field):
                entry[field] = str(name)
                self._dirty = True

    def resolve(
        self,
        spell_id: int | None,
        *,
        fallback_name: str | None = None,
    ) -> SpellMeta | None:
        if spell_id is None:
            return None
        sid = int(spell_id)
        entry = self._entries.setdefault(sid, {})
        defense = lookup_defense(sid)
        if defense is not None:
            entry.setdefault("name_zh", defense.name)
            if defense.aliases and not entry.get("name_en"):
                entry["name_en"] = defense.aliases[0]

        # 清洗旧缓存：TalentInstant 前缀、被误吞后的「秒。」碎片、纯英文说明
        if entry.get("description"):
            cleaned = scrub_spell_description(
                entry.get("description"),
                spell_name=entry.get("name_zh") or entry.get("name_en"),
            )
            bad = (
                cleaned is None
                or _is_garbage_description(cleaned)
                or _is_mostly_english(cleaned)
            )
            if bad:
                entry.pop("description", None)
                entry.pop("detail_fetched", None)
                self._dirty = True
            elif cleaned != entry.get("description"):
                entry["description"] = cleaned
                self._dirty = True

        needs_zh = not entry.get("name_zh")
        needs_icon = not entry.get("icon")
        # 旧缓存可能只有名字/图标；用 detail_fetched 标记只补拉一次说明
        needs_detail = not entry.get("detail_fetched")
        if self._fetch and sid not in _NEGATIVE_CACHE and (
            needs_zh or needs_icon or needs_detail
        ):
            self._fetch_and_merge(sid, entry)

        if fallback_name and not entry.get("name_zh") and not entry.get("name_en"):
            if _looks_chinese(fallback_name):
                entry["name_zh"] = fallback_name
            else:
                entry["name_en"] = fallback_name

        if not entry:
            return SpellMeta(spell_id=sid, name_en=fallback_name)

        description = scrub_spell_description(
            entry.get("description"),
            spell_name=entry.get("name_zh") or entry.get("name_en"),
        )
        if description and _is_mostly_english(description):
            description = None

        return SpellMeta(
            spell_id=sid,
            name_zh=entry.get("name_zh"),
            name_en=entry.get("name_en"),
            icon=normalize_icon(entry.get("icon")),
            description=description,
            cast_label=entry.get("cast_label"),
            duration_label=entry.get("duration_label"),
        )

    def flush(self) -> None:
        if not self._dirty:
            return
        path = self._cache_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            str(spell_id): {
                key: value
                for key, value in entry.items()
                if value
            }
            for spell_id, entry in sorted(self._entries.items())
            if entry
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._dirty = False

    def _seed_from_defenses(self) -> None:
        for ability in DEFENSE_ABILITIES:
            entry = self._entries.setdefault(ability.spell_id, {})
            entry.setdefault("name_zh", ability.name)
            if ability.aliases and not entry.get("name_en"):
                entry["name_en"] = ability.aliases[0]

    def _load_seed(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        for key, value in raw.items():
            try:
                spell_id = int(key)
            except (TypeError, ValueError):
                continue
            if not isinstance(value, dict):
                continue
            entry = self._entries.setdefault(spell_id, {})
            for field in (
                "name_zh",
                "name_en",
                "icon",
                "description",
                "cast_label",
                "duration_label",
                "detail_fetched",
                "detail_version",
            ):
                if value.get(field) and not entry.get(field):
                    if field == "icon":
                        entry[field] = normalize_icon(str(value[field]))
                    else:
                        entry[field] = str(value[field])

    def _invalidate_stale_detail_cache(self) -> None:
        """解析策略升级后，丢掉全部旧说明，下次 resolve 按 HTML 正文重拉。

        对目录里每一个技能、以及战斗中出现的首领技能都生效，不只是个别 ID。
        """
        changed = False
        for entry in self._entries.values():
            if entry.get("detail_version") == _DETAIL_CACHE_VERSION:
                continue
            for field in (
                "description",
                "cast_label",
                "duration_label",
                "detail_fetched",
                "detail_version",
            ):
                if field in entry:
                    entry.pop(field, None)
                    changed = True
        if changed:
            self._dirty = True

    def _fetch_and_merge(self, spell_id: int, entry: dict[str, str | None]) -> None:
        zh = self._fetch_locale(spell_id, _LOCALE_ZH)
        changed = self._merge_tooltip_payload(entry, zh, locale_zh=True)
        need_en = (
            not entry.get("name_en")
            or not entry.get("description")
            or not entry.get("cast_label")
        )
        en = self._fetch_locale(spell_id, _LOCALE_EN) if need_en else None
        if en is not None:
            changed = self._merge_tooltip_payload(entry, en, locale_zh=False) or changed
        if zh is None and en is None:
            _NEGATIVE_CACHE.add(spell_id)
            return
        if not entry.get("detail_fetched"):
            entry["detail_fetched"] = "1"
            changed = True
        if entry.get("detail_version") != _DETAIL_CACHE_VERSION:
            entry["detail_version"] = _DETAIL_CACHE_VERSION
            changed = True
        if changed:
            self._dirty = True

    def _merge_tooltip_payload(
        self,
        entry: dict[str, str | None],
        payload: dict[str, Any] | None,
        *,
        locale_zh: bool,
    ) -> bool:
        if not payload:
            return False
        changed = False
        name = payload.get("name")
        raw_icon = payload.get("icon")
        if raw_icon is None and isinstance(payload.get("iconName"), str):
            raw_icon = payload.get("iconName")
        icon = normalize_icon(raw_icon if isinstance(raw_icon, str) else None)
        if name and locale_zh and not entry.get("name_zh"):
            entry["name_zh"] = str(name)
            changed = True
        if name and not locale_zh and not entry.get("name_en"):
            entry["name_en"] = str(name)
            changed = True
        if icon and not entry.get("icon"):
            entry["icon"] = icon
            changed = True
        parsed = parse_wowhead_tooltip(
            payload.get("tooltip") if isinstance(payload.get("tooltip"), str) else None,
            spell_name=str(name) if name else entry.get("name_zh") or entry.get("name_en"),
        )
        # 说明只收中文 tooltip，避免 TalentInstant 英文正文进悬停
        if locale_zh and parsed.description and not entry.get("description"):
            cleaned = scrub_spell_description(
                parsed.description,
                spell_name=str(name) if name else entry.get("name_zh"),
            )
            if cleaned and not _is_mostly_english(cleaned):
                entry["description"] = cleaned
                changed = True
        if parsed.cast_label and not entry.get("cast_label"):
            entry["cast_label"] = parsed.cast_label
            changed = True
        if parsed.duration_label and not entry.get("duration_label"):
            entry["duration_label"] = parsed.duration_label
            changed = True
        return changed

    def _fetch_locale(self, spell_id: int, locale: int) -> dict[str, Any] | None:
        if self._fetcher is not None:
            try:
                return self._fetcher(spell_id, locale)
            except Exception:
                return None
        url = WOWHEAD_TOOLTIP_TMPL.format(spell_id=spell_id, locale=locale)
        client = self._ensure_http()
        try:
            response = client.get(url)
            if response.status_code >= 400:
                return None
            data = response.json()
            if not isinstance(data, dict):
                return None
            return data
        except Exception:
            return None

    def _ensure_http(self) -> httpx.Client:
        if self._http is None:
            # Wowhead 对缺 Referer / 过简 UA 可能 403；用浏览器风格头提高成功率
            self._http = httpx.Client(
                timeout=20.0,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; wcl-analyzer/0.1; "
                        "+https://github.com/local/wcl-analyzer)"
                    ),
                    "Accept": "application/json,text/javascript,*/*;q=0.8",
                    "Referer": "https://www.wowhead.com/",
                },
                follow_redirects=True,
            )
        return self._http


def enrich_timeline_metadata(
    analysis: TimelineAnalysis,
    store: SpellMetaStore | None = None,
    *,
    ability_icons: dict[int, str] | None = None,
    ability_names: dict[int, str] | None = None,
    fetch: bool = True,
) -> TimelineAnalysis:
    """为时间线事件补齐图标 / 中文名，并计算首领技能间隔摘要。"""
    owns = store is None
    meta_store = store or SpellMetaStore(fetch=fetch)
    try:
        meta_store.seed_icons(ability_icons)
        meta_store.seed_names(ability_names, as_zh=False)
        events = tuple(
            _enrich_event(event, meta_store) for event in analysis.events
        )
        boss_cds = summarize_boss_cds(events)
        return TimelineAnalysis(
            fight=analysis.fight,
            events=events,
            boss_cds=boss_cds,
            health_series=analysis.health_series,
        )
    finally:
        if owns:
            meta_store.close()


def summarize_boss_cds(
    events: tuple[TimelineEvent, ...] | list[TimelineEvent],
) -> tuple[BossAbilityCd, ...]:
    """按技能汇总本场施法间隔，推算表观 CD（非必然真实冷却）。"""
    buckets: dict[tuple[int | None, str], list[TimelineEvent]] = {}
    for event in events:
        if event.kind != "boss":
            continue
        key = (event.ability_id, event.ability)
        buckets.setdefault(key, []).append(event)

    summaries: list[BossAbilityCd] = []
    for (ability_id, ability), group in buckets.items():
        group = sorted(group, key=lambda item: item.offset_ms)
        timestamps = tuple(event.offset_ms for event in group)
        intervals = tuple(
            timestamps[index] - timestamps[index - 1]
            for index in range(1, len(timestamps))
        )
        icon = next((event.icon for event in group if event.icon), None)
        ability_en = next((event.ability_en for event in group if event.ability_en), None)
        summaries.append(
            BossAbilityCd(
                ability_id=ability_id,
                ability=ability,
                ability_en=ability_en,
                icon=icon,
                cast_count=len(timestamps),
                timestamps_ms=timestamps,
                intervals_ms=intervals,
                median_interval_ms=_median(intervals),
                min_interval_ms=min(intervals) if intervals else None,
                max_interval_ms=max(intervals) if intervals else None,
            )
        )
    summaries.sort(
        key=lambda item: (
            -(item.cast_count),
            item.timestamps_ms[0] if item.timestamps_ms else 0.0,
            item.ability,
        )
    )
    return tuple(summaries)


def _enrich_event(event: TimelineEvent, store: SpellMetaStore) -> TimelineEvent:
    if event.ability_id is None or event.kind == "phase":
        return event
    meta = store.resolve(event.ability_id, fallback_name=event.ability)
    if meta is None:
        return event

    icon = meta.icon or event.icon
    description = meta.description or event.description
    cast_label = meta.cast_label or event.cast_label
    duration_label = meta.duration_label or event.duration_label
    if event.kind == "defense":
        # 目录中文名优先；图标 / 英文名 / 说明来自元数据
        # 玩家减伤条优先用效果持续（如星界转移 12 秒），而非读条时长
        effect_ms = parse_effect_duration_ms(duration_label)
        duration_ms = event.duration_ms
        if effect_ms and effect_ms > 0:
            duration_ms = effect_ms
        return replace(
            event,
            icon=icon,
            ability_en=meta.name_en or event.ability_en,
            description=description,
            cast_label=cast_label,
            duration_label=duration_label,
            duration_ms=duration_ms,
        )

    display = meta.name_zh or event.ability
    ability_en = meta.name_en
    if meta.name_zh and event.ability and event.ability != meta.name_zh:
        ability_en = ability_en or event.ability
    elif not ability_en and event.ability and event.ability != display:
        ability_en = event.ability
    return replace(
        event,
        ability=display,
        ability_en=ability_en,
        icon=icon,
        description=description,
        cast_label=cast_label,
        duration_label=duration_label,
    )


def _median(values: tuple[float, ...] | list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _looks_chinese(text: str) -> bool:
    return bool(_CJK_RE.search(text))
