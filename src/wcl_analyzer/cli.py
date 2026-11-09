from __future__ import annotations

import argparse
import json
import tempfile
import webbrowser
from dataclasses import asdict
from pathlib import Path

from wcl_analyzer.analysis import analyze_fight, resolve_fight_token, select_fight, summarize_bosses
from wcl_analyzer.client import WclClient, WclError
from wcl_analyzer.config import credentials
from wcl_analyzer.format import format_fight, format_pulls, format_report, format_timeline
from wcl_analyzer.html_timeline import write_timeline_html
from wcl_analyzer.models import Report, TimelineAnalysis, fight_display_name, fight_kind_label
from wcl_analyzer.refs import parse_report_ref
from wcl_analyzer.service import build_timeline_analysis
from wcl_analyzer.web import serve_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wcl", description="分析 Warcraft Logs 中的首领战斗")
    sub = parser.add_subparsers(dest="command", required=True)

    report_cmd = sub.add_parser("report", help="汇总一份报告里的首领尝试")
    report_cmd.add_argument("report", help="报告代码或链接")
    report_cmd.add_argument(
        "--list-pulls",
        action="store_true",
        help="列出每场首领 pull 的 fight id / 结果 / 时长，便于挑选 --fight / --pull",
    )
    report_cmd.add_argument("--json", action="store_true", help="输出 JSON")
    report_cmd.set_defaults(func=_cmd_report)

    fight_cmd = sub.add_parser("fight", help="分析一场首领战斗的伤害、治疗、承伤和死亡")
    fight_cmd.add_argument("report", help="报告代码或链接")
    _add_fight_selectors(fight_cmd)
    fight_cmd.add_argument(
        "--list-pulls",
        action="store_true",
        help="只列出 pull，不分析",
    )
    fight_cmd.add_argument("--json", action="store_true", help="输出 JSON")
    fight_cmd.set_defaults(func=_cmd_fight)

    timeline_cmd = sub.add_parser(
        "timeline",
        help="分析一场首领战斗（pull）的减伤 / 药水时间线，并对照首领技能",
    )
    timeline_cmd.add_argument("report", help="报告代码或链接")
    _add_fight_selectors(timeline_cmd)
    timeline_cmd.add_argument(
        "--list-pulls",
        action="store_true",
        help="只列出本报告的首领 pull（fight id），不拉时间线",
    )
    timeline_cmd.add_argument("--player", help="只显示该玩家的减伤 / 药水（仍保留首领技能）")
    timeline_cmd.add_argument(
        "--category",
        help="只显示该类别：个减、团减、治疗药水、爆发药水、治疗饰品、打断",
    )
    timeline_cmd.add_argument(
        "--html",
        metavar="FILE",
        help="写出可视化泳道时间线为 HTML 文件（技能图标走 Wowhead CDN）",
    )
    timeline_cmd.add_argument(
        "--open",
        action="store_true",
        help="在默认浏览器中打开可视化时间线（可与 --html 合用）",
    )
    timeline_cmd.add_argument(
        "--no-fetch-meta",
        action="store_true",
        help="不请求 Wowhead 补全未知技能的中文名 / 图标（仍用本地缓存与 WCL 图标）",
    )
    timeline_cmd.add_argument("--json", action="store_true", help="输出 JSON")
    timeline_cmd.set_defaults(func=_cmd_timeline)

    serve_cmd = sub.add_parser(
        "serve",
        help="启动本地网页：先输入 WCL 链接，再打开减伤 / 药水时间线",
    )
    serve_cmd.add_argument(
        "--host",
        default="127.0.0.1",
        help="监听地址（默认 127.0.0.1）",
    )
    serve_cmd.add_argument(
        "--port",
        type=int,
        default=8765,
        help="监听端口（默认 8765）",
    )
    serve_cmd.add_argument(
        "--open",
        action="store_true",
        help="启动后在默认浏览器打开入口页",
    )
    serve_cmd.add_argument(
        "--no-fetch-meta",
        action="store_true",
        help="不请求 Wowhead 补全未知技能的中文名 / 图标",
    )
    serve_cmd.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (WclError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")
    return 0


def _with_client(func):
    def wrapper(args: argparse.Namespace) -> None:
        client_id, client_secret = credentials()
        with WclClient(client_id, client_secret) as client:
            func(client, args)

    return wrapper


def _add_fight_selectors(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fight",
        help=(
            "战斗编号（pull = fight id）。优先于链接里的 #fight= / ?fight=；"
            "都省略时取最后一次首领/钥石击杀。"
            "链接必须加引号：否则 zsh 会把 ? 当通配符、把 & 当后台、把 # 后当注释"
        ),
    )
    parser.add_argument(
        "--pull",
        help="--fight 的别名：指定某一场 pull 的 fight id（与 --fight 同时给出时必须一致）",
    )


@_with_client
def _cmd_report(client: WclClient, args: argparse.Namespace) -> None:
    ref = parse_report_ref(args.report)
    report = client.get_report(ref.code)
    if args.list_pulls:
        _print_pulls(report, as_json=args.json)
        return
    if args.json:
        payload = {
            "report": asdict(report),
            "bosses": [asdict(summary) for summary in summarize_bosses(report)],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(format_report(report))


@_with_client
def _cmd_fight(client: WclClient, args: argparse.Namespace) -> None:
    ref = parse_report_ref(args.report)
    report = client.get_report(ref.code)
    if args.list_pulls:
        _print_pulls(report, as_json=False)
        return
    fight_token = resolve_fight_token(
        fight=args.fight,
        pull=args.pull,
        ref_fight=ref.fight,
    )
    fight = select_fight(report, fight_token)
    tables = client.get_fight_tables(report.code, fight.id)
    analysis = analyze_fight(fight, tables)
    if args.json:
        print(json.dumps(asdict(analysis), ensure_ascii=False, indent=2))
        return
    print(format_fight(analysis))


@_with_client
def _cmd_timeline(client: WclClient, args: argparse.Namespace) -> None:
    ref = parse_report_ref(args.report)
    report = client.get_report(ref.code)
    if args.list_pulls:
        _print_pulls(report, as_json=args.json)
        return

    analysis = build_timeline_analysis(
        client,
        args.report,
        fight=args.fight,
        pull=args.pull,
        player=args.player,
        category=args.category,
        fetch_meta=not args.no_fetch_meta,
    )

    visual = bool(args.html or args.open)
    if visual:
        html_path = _write_timeline_visual(analysis, args.html, open_browser=args.open)
        print(f"已写出可视化时间线：{html_path}")
    if args.json:
        print(json.dumps(asdict(analysis), ensure_ascii=False, indent=2))
        return
    if not visual:
        print(format_timeline(analysis))


def _cmd_serve(args: argparse.Namespace) -> None:
    client_id, client_secret = credentials()
    serve_app(
        host=args.host,
        port=args.port,
        open_browser=args.open,
        fetch_meta=not args.no_fetch_meta,
        client_id=client_id,
        client_secret=client_secret,
    )


def _print_pulls(report: Report, *, as_json: bool) -> None:
    if as_json:
        payload = [
            {
                "id": fight.id,
                "name": fight.name,
                "display_name": fight_display_name(fight),
                "kind": fight_kind_label(fight),
                "encounter_id": fight.encounter_id,
                "difficulty": fight.difficulty,
                "keystone_level": fight.keystone_level,
                "kill": fight.kill,
                "boss_percentage": fight.boss_percentage,
                "duration_ms": fight.duration_ms,
            }
            for fight in report.boss_fights
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(format_pulls(report))


def _write_timeline_visual(
    analysis: TimelineAnalysis,
    html_path: str | None,
    *,
    open_browser: bool,
) -> Path:
    if html_path:
        path = Path(html_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        fight = analysis.fight
        safe_name = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "_"
            for ch in fight.name
        ) or "fight"
        handle = tempfile.NamedTemporaryFile(
            prefix=f"wcl-timeline-{fight.id}-{safe_name}-",
            suffix=".html",
            delete=False,
        )
        path = Path(handle.name)
        handle.close()
    write_timeline_html(analysis, str(path))
    if open_browser:
        webbrowser.open(path.resolve().as_uri())
    return path.resolve()
