from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(frozen=True)
class ReportRef:
    code: str
    fight: str | None = None


def parse_report_ref(value: str) -> ReportRef:
    """接受报告代码，或 warcraftlogs 报告链接。

    支持：
    - 裸代码：``Abcd1234``
    - 片段：``.../reports/CODE#fight=12&type=damage-done``
    - 查询：``.../reports/CODE?fight=12``
    - 编码后的 ``#``（``%23fight=12``），避免 shell 吃掉未加引号的片段后只能靠编码保留

    注意：在 zsh/bash 里未加引号的 ``#fight=`` 会被当成注释剥掉，请给链接加引号，
    或改用 ``--fight`` / ``--pull``。
    """
    text = value.strip()
    if "://" not in text and "/" not in text and "%23" not in text.casefold():
        return ReportRef(code=_validate_code(text))

    # 先把 %23 还原成 #，再交给 urlparse，否则 fight 会粘在 path 里
    text = _restore_encoded_fragment(text)
    parsed = urlparse(text)
    parts = [part for part in parsed.path.split("/") if part]
    code = ""
    if "reports" in parts:
        index = parts.index("reports")
        if index + 1 < len(parts):
            code = parts[index + 1]
    elif parts:
        code = parts[-1]

    code = unquote(code)
    # WCL 界面选中的 fight 写在 hash 里；query 里的 fight 作兜底
    fight = _fight_from_query(parsed.fragment) or _fight_from_query(parsed.query)
    return ReportRef(code=_validate_code(code), fight=fight)


def _restore_encoded_fragment(text: str) -> str:
    """把 URL 中的 %23 还原成 #（仅当尚未有真实 fragment 时）。"""
    if "#" in text:
        return text
    lower = text.casefold()
    marker = "%23"
    index = lower.find(marker)
    if index < 0:
        return text
    return text[:index] + "#" + unquote(text[index + len(marker) :])


def _fight_from_query(raw: str) -> str | None:
    if not raw:
        return None
    query = raw[1:] if raw.startswith(("?", "#")) else raw
    values = parse_qs(query, keep_blank_values=False).get("fight")
    if not values:
        return None
    fight = unquote(values[0]).strip()
    return fight or None


def _validate_code(code: str) -> str:
    if not code or not code.isalnum():
        raise ValueError(f"无法识别的 Warcraft Logs 报告：{code or '空'}")
    return code
