from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv() -> None:
    """读取 .env。已经存在的环境变量优先。"""
    for path in (Path.cwd() / ".env", PROJECT_ROOT / ".env"):
        if path.is_file():
            _apply_env_file(path)


def _apply_env_file(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def credentials() -> tuple[str, str]:
    load_dotenv()
    client_id = os.environ.get("WCL_CLIENT_ID", "").strip()
    client_secret = os.environ.get("WCL_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError(
            "缺少 WCL_CLIENT_ID 或 WCL_CLIENT_SECRET。"
            "复制 .env.example 为 .env 并填入 Warcraft Logs 应用凭证。"
        )
    return client_id, client_secret
