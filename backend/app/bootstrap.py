from __future__ import annotations

from . import db
from .config import _parse_accounts_from_raw, _read_config_raw


def ensure_accounts_imported() -> None:
    db.init_db()
    if db.imported_flag_path().exists():
        return
    if db.count_opencode_accounts() > 0 or db.count_ollama_accounts() > 0:
        db.imported_flag_path().write_text("imported\n", encoding="utf-8")
        return

    raw = _read_config_raw()
    opencode_accounts, ollama_accounts = _parse_accounts_from_raw(raw)

    for account in opencode_accounts:
        if not account.auth_cookie.strip():
            continue
        db.create_opencode_account(
            name=account.name,
            workspace_id=account.workspace_id,
            auth_cookie=account.auth_cookie,
            show_rolling=account.show_rolling,
            show_weekly=account.show_weekly,
            show_monthly=account.show_monthly,
        )

    for account in ollama_accounts:
        if not account.session_cookie.strip():
            continue
        db.create_ollama_account(
            name=account.name,
            session_cookie=account.session_cookie,
            show_session=account.show_session,
            show_weekly=account.show_weekly,
        )

    if opencode_accounts or ollama_accounts:
        db.imported_flag_path().write_text("imported\n", encoding="utf-8")
