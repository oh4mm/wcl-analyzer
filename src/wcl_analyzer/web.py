from __future__ import annotations

import html
import json
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from wcl_analyzer.client import WclClient, WclError
from wcl_analyzer.html_timeline import render_timeline_html
from wcl_analyzer.service import build_timeline_analysis


def serve_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
    fetch_meta: bool = True,
    client_id: str,
    client_secret: str,
) -> None:
    """启动本地入口页 + 时间线分析服务（阻塞直到 Ctrl+C）。"""
    state = {
        "client_id": client_id,
        "client_secret": client_secret,
        "fetch_meta": fetch_meta,
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "WclAnalyzer/0.1"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)
            try:
                if path == "/":
                    self._send_html(200, render_entry_page(query))
                    return
                if path == "/analyze":
                    self._handle_analyze(query)
                    return
                self._send_html(404, render_error_page("页面不存在", status=404))
            except Exception as exc:  # noqa: BLE001 — 入口页要给出可读错误
                self._send_html(
                    500,
                    render_error_page(
                        str(exc) or exc.__class__.__name__,
                        detail=traceback.format_exc(),
                        status=500,
                    ),
                )

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[wcl serve] {self.address_string()} - {fmt % args}")

        def _handle_analyze(self, query: dict[str, list[str]]) -> None:
            url = (query.get("url") or [""])[0].strip()
            fight = (query.get("fight") or [""])[0].strip() or None
            player = (query.get("player") or [""])[0].strip() or None
            if not url:
                self._send_html(
                    400,
                    render_entry_page(
                        query,
                        error="请粘贴 Warcraft Logs 报告链接或报告代码。",
                    ),
                )
                return
            try:
                with WclClient(state["client_id"], state["client_secret"]) as client:
                    analysis = build_timeline_analysis(
                        client,
                        url,
                        fight=fight,
                        player=player,
                        fetch_meta=bool(state["fetch_meta"]),
                    )
            except (WclError, ValueError, RuntimeError) as exc:
                self._send_html(
                    400,
                    render_entry_page(query, error=str(exc), url=url, fight=fight or "", player=player or ""),
                )
                return
            body = render_timeline_html(analysis, home_href="/")
            self._send_html(200, body)

        def _send_html(self, status: int, body: str) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

    httpd = ThreadingHTTPServer((host, port), Handler)
    base = f"http://{host}:{port}/"
    print(f"WCL 分析入口：{base}")
    print("在浏览器粘贴报告链接即可；Ctrl+C 结束。")
    if open_browser:
        webbrowser.open(base)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()


def render_entry_page(
    query: dict[str, list[str]] | None = None,
    *,
    error: str | None = None,
    url: str | None = None,
    fight: str | None = None,
    player: str | None = None,
) -> str:
    query = query or {}
    url_value = url if url is not None else (query.get("url") or [""])[0]
    fight_value = fight if fight is not None else (query.get("fight") or [""])[0]
    player_value = player if player is not None else (query.get("player") or [""])[0]
    error_html = ""
    if error:
        error_html = f'<div class="error" role="alert">{html.escape(error)}</div>'
    return (
        _ENTRY_TEMPLATE.replace("__ERROR_HTML__", error_html)
        .replace("__URL__", html.escape(url_value, quote=True))
        .replace("__FIGHT__", html.escape(fight_value, quote=True))
        .replace("__PLAYER__", html.escape(player_value, quote=True))
    )


def render_error_page(
    message: str,
    *,
    detail: str | None = None,
    status: int = 500,
) -> str:
    detail_html = ""
    if detail:
        detail_html = f"<pre class='detail'>{html.escape(detail)}</pre>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>出错了 · wcl-analyzer</title>
<style>{_SHARED_CSS}</style>
</head>
<body class="entry">
  <main class="card">
    <p class="brand">wcl-analyzer</p>
    <h1>{status}</h1>
    <div class="error" role="alert">{html.escape(message)}</div>
    {detail_html}
    <p class="actions"><a class="back" href="/">返回入口</a></p>
  </main>
</body>
</html>
"""


def analyze_query_string(*, url: str, fight: str | None = None, player: str | None = None) -> str:
    """测试辅助：构造 /analyze 查询串。"""
    params: dict[str, str] = {"url": url}
    if fight:
        params["fight"] = fight
    if player:
        params["player"] = player
    return "/analyze?" + urlencode(params)


_SHARED_CSS = """
:root {
  --bg: #eef2f7;
  --card: #ffffff;
  --ink: #0f172a;
  --muted: #64748b;
  --line: #dbe3ef;
  --accent: #1d4ed8;
  --accent-ink: #ffffff;
  --danger-bg: #fef2f2;
  --danger: #b91c1c;
  --pad: 22px;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  min-height: 100%;
  background:
    radial-gradient(1200px 500px at 10% -10%, #dbeafe 0%, transparent 55%),
    radial-gradient(900px 420px at 100% 0%, #e2e8f0 0%, transparent 50%),
    var(--bg);
  color: var(--ink);
  font: 15px/1.45 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
body.entry {
  display: grid;
  place-items: center;
  padding: 32px 16px;
}
.card {
  width: min(640px, 100%);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: var(--pad);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}
.brand {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
h1 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 650;
  letter-spacing: -0.02em;
}
.lead {
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 14px;
}
label {
  display: block;
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
}
input[type="text"] {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 11px 12px;
  font: inherit;
  color: var(--ink);
  background: #f8fafc;
}
input[type="text"]:focus {
  outline: 2px solid rgba(29, 78, 216, 0.28);
  border-color: #93c5fd;
  background: #fff;
}
.field { margin-bottom: 14px; }
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 560px) {
  .row { grid-template-columns: 1fr; }
}
.hint {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 18px;
}
button {
  appearance: none;
  border: 0;
  border-radius: 10px;
  background: var(--accent);
  color: var(--accent-ink);
  font: inherit;
  font-weight: 600;
  padding: 11px 16px;
  cursor: pointer;
}
button:disabled {
  opacity: 0.65;
  cursor: wait;
}
.back {
  color: var(--accent);
  text-decoration: none;
  font-size: 13px;
}
.back:hover { text-decoration: underline; }
.error {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--danger-bg);
  color: var(--danger);
  font-size: 13px;
  white-space: pre-wrap;
}
.detail {
  margin: 12px 0 0;
  padding: 10px;
  overflow: auto;
  max-height: 240px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 11px;
}
.overlay {
  position: fixed;
  inset: 0;
  display: none;
  place-items: center;
  background: rgba(15, 23, 42, 0.35);
  color: #fff;
  font-weight: 600;
  z-index: 20;
}
.overlay.show { display: grid; }
.overlay span {
  padding: 14px 18px;
  border-radius: 12px;
  background: #0f172a;
}
"""

_ENTRY_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>粘贴 WCL 链接 · wcl-analyzer</title>
<style>""" + _SHARED_CSS + """</style>
</head>
<body class="entry">
  <div class="overlay" id="overlay" aria-live="polite"><span>正在拉取战斗数据…</span></div>
  <main class="card">
    <p class="brand">wcl-analyzer</p>
    <h1>分析一场战斗</h1>
    <p class="lead">粘贴 Warcraft Logs 报告链接（含 <code>#fight=</code> / <code>?fight=</code>），生成减伤 / 药水 / 首领技能时间线。</p>
    __ERROR_HTML__
    <form id="analyze-form" method="get" action="/analyze">
      <div class="field">
        <label for="url">报告链接或代码</label>
        <input id="url" name="url" type="text" required
          placeholder="https://cn.warcraftlogs.com/reports/……?fight=12"
          value="__URL__" autocomplete="off" spellcheck="false">
        <p class="hint">支持 cn / www；也可只填报告代码（默认取最后一次击杀）。</p>
      </div>
      <div class="row">
        <div class="field">
          <label for="fight">fight id（可选）</label>
          <input id="fight" name="fight" type="text" placeholder="覆盖链接中的 fight"
            value="__FIGHT__" autocomplete="off">
        </div>
        <div class="field">
          <label for="player">只看某玩家（可选）</label>
          <input id="player" name="player" type="text" placeholder="例如：法师甲"
            value="__PLAYER__" autocomplete="off">
        </div>
      </div>
      <div class="actions">
        <button type="submit" id="submit-btn">开始分析</button>
      </div>
    </form>
  </main>
  <script>
  (function () {
    const form = document.getElementById("analyze-form");
    const overlay = document.getElementById("overlay");
    const btn = document.getElementById("submit-btn");
    form.addEventListener("submit", function () {
      overlay.classList.add("show");
      btn.disabled = true;
    });
  })();
  </script>
</body>
</html>
"""
