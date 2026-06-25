from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AccountConfig:
    name: str
    workspace_id: str
    auth_cookie: str
    show_rolling: bool = True
    show_weekly: bool = True
    show_monthly: bool = True


@dataclass
class OllamaAccountConfig:
    name: str
    session_cookie: str
    show_session: bool = True
    show_weekly: bool = True


@dataclass
class RefreshSettings:
    auto_refresh: bool = True
    interval_sec: int = 60


@dataclass
class AppConfig:
    listen_host: str
    listen_port: int
    opencode_accounts: list[AccountConfig]
    ollama_accounts: list[OllamaAccountConfig]
    refresh_ollama: RefreshSettings
    refresh_opencode_go: RefreshSettings


def _parse_refresh_settings(raw: dict[str, Any] | None, *, default_interval: int) -> RefreshSettings:
    if not isinstance(raw, dict):
        return RefreshSettings(interval_sec=default_interval)
    interval = raw.get("interval_sec", default_interval)
    try:
        interval_sec = int(interval)
    except (TypeError, ValueError):
        interval_sec = default_interval
    interval_sec = max(15, interval_sec)
    return RefreshSettings(
        auto_refresh=bool(raw.get("auto_refresh", True)),
        interval_sec=interval_sec,
    )


def _project_root() -> Path:
    env_path = os.environ.get("QUOTAHUB_CONFIG")
    if env_path:
        return Path(env_path).resolve().parent
    return Path(__file__).resolve().parents[2]


def config_path() -> Path:
    env_path = os.environ.get("QUOTAHUB_CONFIG")
    if env_path:
        return Path(env_path).resolve()
    return _project_root() / "config.json"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}，请复制 config.json.example 为 config.json")

    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    opencode_accounts_raw = raw.get("opencode_accounts") or []
    ollama_accounts_raw = raw.get("ollama_accounts") or []

    opencode_accounts: list[AccountConfig] = []
    for i, item in enumerate(opencode_accounts_raw):
        if not isinstance(item, dict):
            continue
        opencode_accounts.append(
            AccountConfig(
                name=str(item.get("name") or f"opencode-{i + 1}"),
                workspace_id=str(item.get("workspace_id") or "Default").strip() or "Default",
                auth_cookie=str(item.get("auth_cookie") or "").strip(),
                show_rolling=bool(item.get("show_rolling", True)),
                show_weekly=bool(item.get("show_weekly", True)),
                show_monthly=bool(item.get("show_monthly", True)),
            )
        )

    ollama_accounts: list[OllamaAccountConfig] = []
    for i, item in enumerate(ollama_accounts_raw):
        if not isinstance(item, dict):
            continue
        ollama_accounts.append(
            OllamaAccountConfig(
                name=str(item.get("name") or f"ollama-{i + 1}"),
                session_cookie=str(item.get("session_cookie") or "").strip(),
                show_session=bool(item.get("show_session", True)),
                show_weekly=bool(item.get("show_weekly", True)),
            )
        )

    if not opencode_accounts and not ollama_accounts:
        raise ValueError("config.json 中 opencode_accounts 与 ollama_accounts 不能同时为空")

    refresh_raw = raw.get("refresh") if isinstance(raw.get("refresh"), dict) else {}
    refresh_ollama = _parse_refresh_settings(refresh_raw.get("ollama"), default_interval=300)
    refresh_opencode_go = _parse_refresh_settings(refresh_raw.get("opencode_go"), default_interval=60)

    return AppConfig(
        listen_host=str(os.environ.get("QUOTAHUB_LISTEN_HOST") or raw.get("listen_host") or "127.0.0.1"),
        listen_port=int(os.environ.get("QUOTAHUB_LISTEN_PORT") or raw.get("listen_port") or 8788),
        opencode_accounts=opencode_accounts,
        ollama_accounts=ollama_accounts,
        refresh_ollama=refresh_ollama,
        refresh_opencode_go=refresh_opencode_go,
    )


def _mask_secret(value: str, prefix: str) -> str:
    secret = value.strip()
    if len(secret) <= 8:
        return f"{prefix}****"
    return f"{prefix}{secret[:4]}…{secret[-4:]}"


def mask_cookie(cookie: str) -> str:
    value = cookie.strip()
    if not value:
        return ""
    if value.lower().startswith("cookie:"):
        value = value[7:].strip()
    auth = value
    if "auth=" in value:
        for part in value.split(";"):
            part = part.strip()
            if part.startswith("auth="):
                auth = part[5:]
                break
    return _mask_secret(auth, "auth=")


def mask_ollama_cookie(cookie: str) -> str:
    value = cookie.strip()
    if not value:
        return ""
    if value.lower().startswith("cookie:"):
        value = value[7:].strip()
    if "__Secure-session=" in value:
        for part in value.split(";"):
            part = part.strip()
            if part.startswith("__Secure-session="):
                return _mask_secret(part[17:], "__Secure-session=")
    if "=" not in value:
        return _mask_secret(value, "__Secure-session=")
    return "cookie=****"
