from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .cpa_quota import map_cpa_plan, mask_cpa_account, parse_auth_files, parse_cpa_usage_payload
from .db import CPAMPChannelRow
from .quota import LABEL_MONTHLY, LABEL_ROLLING, LABEL_WEEKLY
from .secrets import keyed_fingerprint
from .version import APP_VERSION

TIMEOUT = httpx.Timeout(20.0, connect=10.0)
USER_AGENT = f"QuotaHub/{APP_VERSION}"
QUERY_BATCH_SIZE = 200
HEADER_SNAPSHOT_MAX_AGE = timedelta(hours=6)
HEADER_SNAPSHOT_FUTURE_TOLERANCE = timedelta(minutes=5)


class CPAMPError(ValueError):
    pass


class CPAMPAuthenticationError(CPAMPError):
    pass


class CPAMPQueryUnsupported(CPAMPError):
    pass


@dataclass(frozen=True)
class CPAMPAccount:
    row_key: str
    auth_index: str
    auth_file_name: str
    account_snapshot: str
    account_key_hash: str
    account_display: str
    plan: str
    locator_hash: str = ""
    subject_hash: str = ""
    header_subject_hash: str = ""
    legacy_account_key_hashes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CPAMPQuotaSnapshot:
    account: CPAMPAccount
    plan: str
    windows: list[dict[str, Any]]
    observed_at: str
    stale: bool
    source: str


def _management_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _management_headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }


def _text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            numeric = float(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
    else:
        return None
    if numeric > 10_000_000_000:
        numeric /= 1000
    try:
        return datetime.fromtimestamp(numeric, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _identity_hash(auth_file: str, auth_index: str, fallback: str) -> str:
    if auth_file and auth_index:
        material = f"file-index\x00{auth_file.casefold()}\x00{auth_index}"
    elif auth_index:
        material = f"auth-index\x00{auth_index}"
    elif auth_file:
        material = f"auth-file\x00{auth_file.casefold()}"
    else:
        material = f"fallback\x00{fallback.casefold()}"
    return keyed_fingerprint("cpa-locator-v1", material)


def _subject_hash(value: str) -> str:
    if not value:
        return ""
    return keyed_fingerprint("cpa-canonical-subject-v1", value.strip().casefold())


def _header_subject_hash(value: str) -> str:
    if not value:
        return ""
    return keyed_fingerprint("cpa-header-subject-v1", value.strip().casefold())


def _account_from_parts(
    *,
    row_key: str,
    auth_index: str,
    auth_file_name: str,
    account_snapshot: str,
    display_source: str,
    plan: str,
) -> CPAMPAccount | None:
    fallback = account_snapshot or display_source
    if not auth_index and not auth_file_name and not fallback:
        return None
    locator_hash = _identity_hash(auth_file_name, auth_index, fallback)
    return CPAMPAccount(
        row_key=row_key,
        auth_index=auth_index,
        auth_file_name=auth_file_name,
        account_snapshot=account_snapshot,
        account_key_hash=locator_hash,
        account_display=mask_cpa_account(display_source or account_snapshot),
        plan=plan,
        locator_hash=locator_hash,
        subject_hash=_subject_hash(account_snapshot),
        header_subject_hash=_header_subject_hash(account_snapshot),
    )


def parse_cpamp_auth_files(payload: Any) -> list[CPAMPAccount]:
    parsed = parse_auth_files(payload)
    raw_by_locator: dict[tuple[str, str], dict[str, Any]] = {}
    if isinstance(payload, dict) and isinstance(payload.get("files"), list):
        for raw in payload["files"]:
            if not isinstance(raw, dict):
                continue
            auth_index = _text(raw, "auth_index", "authIndex", "AuthIndex")
            auth_file = _text(raw, "name", "file_name", "fileName", "filename")
            raw_by_locator[(auth_file.casefold(), auth_index)] = raw
    accounts: list[CPAMPAccount] = []
    for index, item in enumerate(parsed):
        legacy_hash = _identity_hash(
            item.auth_file_name, item.auth_index, item.account_display
        )
        raw = raw_by_locator.get(
            (item.auth_file_name.casefold(), item.auth_index), {}
        )
        account_snapshot = _text(
            raw, "account", "email", "display_account", "displayAccount"
        )
        accounts.append(
            CPAMPAccount(
                row_key=f"account-{index}",
                auth_index=item.auth_index,
                auth_file_name=item.auth_file_name,
                account_snapshot=account_snapshot,
                account_key_hash=item.account_key_hash,
                account_display=item.account_display,
                plan=item.plan,
                locator_hash=legacy_hash,
                subject_hash=item.subject_hash or _subject_hash(account_snapshot),
                header_subject_hash=_header_subject_hash(account_snapshot),
                legacy_account_key_hashes=(
                    keyed_fingerprint("cpamp-account-v2", item.account_key_hash),
                    legacy_hash,
                ),
            )
        )
    return accounts


async def discover_cpamp_accounts(
    channel: CPAMPChannelRow, client: httpx.AsyncClient
) -> list[CPAMPAccount]:
    response = await client.get(
        _management_url(channel.base_url, "/v0/management/auth-files"),
        headers=_management_headers(channel.management_key),
    )
    if response.status_code in (401, 403):
        raise CPAMPAuthenticationError("CPAMP 管理认证失败")
    if response.status_code < 200 or response.status_code >= 300:
        raise CPAMPError(f"CPAMP 账号发现返回 HTTP {response.status_code}")
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise CPAMPError("CPAMP 账号列表响应不是有效 JSON") from exc
    return parse_cpamp_auth_files(payload)


def _query_target(account: CPAMPAccount) -> dict[str, Any]:
    identity: dict[str, str] = {"auth_provider_snapshot": "codex"}
    if account.auth_file_name:
        identity["auth_file_snapshot"] = account.auth_file_name
    if account.auth_index:
        identity["auth_index"] = account.auth_index
    if account.account_snapshot:
        identity["account_snapshot"] = account.account_snapshot
    return {"row_key": account.row_key, "provider": "codex", "account": identity}


async def query_cpamp_snapshots_batch(
    channel: CPAMPChannelRow,
    accounts: list[CPAMPAccount],
    client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    if not accounts or len(accounts) > QUERY_BATCH_SIZE:
        raise ValueError("CPAMP snapshot batch must contain 1-200 accounts")
    response = await client.post(
        _management_url(channel.base_url, "/v0/management/quota-snapshots/query"),
        headers={
            **_management_headers(channel.management_key),
            "Content-Type": "application/json",
        },
        json={"accounts": [_query_target(account) for account in accounts]},
    )
    if response.status_code in (401, 403):
        raise CPAMPAuthenticationError("CPAMP 管理认证失败")
    if response.status_code in (404, 405):
        raise CPAMPQueryUnsupported("CPAMP 不支持 quota snapshot query")
    if response.status_code < 200 or response.status_code >= 300:
        raise CPAMPError(f"CPAMP 快照查询返回 HTTP {response.status_code}")
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise CPAMPError("CPAMP 快照查询响应不是有效 JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise CPAMPError("CPAMP 快照查询响应缺少 items")
    return [item for item in payload["items"] if isinstance(item, dict)]


async def fetch_cpamp_header_snapshots(
    channel: CPAMPChannelRow, client: httpx.AsyncClient
) -> list[dict[str, Any]]:
    response = await client.get(
        _management_url(
            channel.base_url, "/v0/management/monitoring/header-snapshots"
        ),
        headers=_management_headers(channel.management_key),
        params={"days": 30, "limit": 5000},
    )
    if response.status_code in (401, 403):
        raise CPAMPAuthenticationError("CPAMP 管理认证失败")
    if response.status_code < 200 or response.status_code >= 300:
        raise CPAMPError(f"CPAMP Header Snapshot 返回 HTTP {response.status_code}")
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise CPAMPError("CPAMP Header Snapshot 响应不是有效 JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise CPAMPError("CPAMP Header Snapshot 响应缺少 items")
    return [item for item in payload["items"] if isinstance(item, dict)]


def _window_label(raw: dict[str, Any], duration_sec: int | None) -> str:
    kind = _text(raw, "window_kind", "provider_window_id").casefold()
    if "month" in kind:
        return LABEL_MONTHLY
    if "week" in kind or "secondary" in kind:
        return LABEL_WEEKLY
    if duration_sec is not None:
        if duration_sec <= 6 * 3600:
            return LABEL_ROLLING
        if duration_sec <= 10 * 24 * 3600:
            return LABEL_WEEKLY
        return LABEL_MONTHLY
    return LABEL_ROLLING if "primary" in kind else LABEL_WEEKLY


def _normalized_window(raw: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    used = _number(raw.get("used_percent"))
    remaining = _number(raw.get("remaining_percent"))
    if used is None and remaining is not None:
        used = 100.0 - remaining
    if used is None:
        return None
    used = max(0.0, min(100.0, used))
    duration_value = _number(raw.get("duration_seconds"))
    duration_sec = max(0, int(duration_value)) if duration_value is not None else None
    cycle_end = _timestamp(raw.get("cycle_end_ms"))
    if cycle_end is None and isinstance(raw.get("current_cycle"), dict):
        current_cycle = raw["current_cycle"]
        cycle_end = _timestamp(
            current_cycle.get("scheduled_end_ms")
            or current_cycle.get("actual_end_ms")
        )
    reset_in_sec = max(0, int((cycle_end - now).total_seconds())) if cycle_end else 0
    window: dict[str, Any] = {
        "label": _window_label(raw, duration_sec),
        "used": round(used, 2),
        "remaining": round(100.0 - used, 2),
        "total": 100.0,
        "unit": "%",
        "reset_at": cycle_end.isoformat().replace("+00:00", "Z") if cycle_end else "",
        "reset_in_sec": reset_in_sec,
    }
    if duration_sec is not None:
        window["duration_sec"] = duration_sec
    return window


def parse_cpamp_query_items(
    items: list[dict[str, Any]], accounts: list[CPAMPAccount]
) -> list[CPAMPQuotaSnapshot]:
    by_row_key = {account.row_key: account for account in accounts}
    snapshots: list[CPAMPQuotaSnapshot] = []
    now = datetime.now(UTC)
    for item in items:
        account = by_row_key.get(_text(item, "row_key"))
        windows_raw = item.get("windows")
        if account is None or not isinstance(windows_raw, list):
            continue
        selected: dict[str, tuple[int, dict[str, Any], dict[str, Any]]] = {}
        for raw in windows_raw:
            if not isinstance(raw, dict):
                continue
            window = _normalized_window(raw, now)
            if window is None:
                continue
            observed_number = _number(raw.get("observed_at_ms")) or 0
            observed_ms = max(0, int(observed_number))
            label = str(window["label"])
            if label not in selected or observed_ms >= selected[label][0]:
                selected[label] = (observed_ms, window, raw)
        if not selected:
            continue
        selected_values = list(selected.values())
        plan_candidates = [
            (observed_ms, map_cpa_plan(raw.get("plan_type")))
            for observed_ms, _window, raw in selected_values
            if map_cpa_plan(raw.get("plan_type")) != "未知套餐"
        ]
        plan = max(plan_candidates, key=lambda item: item[0])[1] if plan_candidates else account.plan
        stale = any(bool(raw.get("stale")) for _observed_ms, _window, raw in selected_values)
        newest_ms = max(observed_ms for observed_ms, _window, _raw in selected_values)
        windows = [value[1] for value in selected_values]
        order = {LABEL_ROLLING: 0, LABEL_WEEKLY: 1, LABEL_MONTHLY: 2}
        windows.sort(key=lambda window: order.get(str(window.get("label")), 99))
        observed = _timestamp(newest_ms)
        snapshots.append(
            CPAMPQuotaSnapshot(
                account=account,
                plan=plan,
                windows=windows,
                observed_at=(
                    observed.isoformat().replace("+00:00", "Z")
                    if observed is not None
                    else now.isoformat().replace("+00:00", "Z")
                ),
                stale=stale,
                source="quota_snapshots",
            )
        )
    return snapshots


def _account_from_header_snapshot(
    item: dict[str, Any], row_key: str
) -> CPAMPAccount | None:
    auth_index = _text(item, "auth_index")
    auth_file = _text(item, "auth_file_snapshot")
    account_snapshot = _text(item, "account_snapshot")
    label_snapshot = _text(item, "auth_label_snapshot")
    plan = map_cpa_plan(item.get("header_quota_plan_type"))
    return _account_from_parts(
        row_key=row_key,
        auth_index=auth_index,
        auth_file_name=auth_file,
        account_snapshot=account_snapshot,
        display_source=account_snapshot or label_snapshot,
        plan=plan,
    )


def parse_cpamp_header_items(
    items: list[dict[str, Any]],
    accounts: list[CPAMPAccount] | None = None,
    *,
    allow_ephemeral_accounts: bool = True,
) -> list[CPAMPQuotaSnapshot]:
    known = {
        (
            account.locator_hash
            or _identity_hash(
                account.auth_file_name,
                account.auth_index,
                account.account_snapshot or account.account_display,
            )
        ): account
        for account in accounts or []
    }
    newest: dict[
        str, tuple[int, CPAMPAccount, dict[str, Any], dict[str, Any], list[dict[str, Any]]]
    ] = {}
    for index, item in enumerate(items):
        auth_file = _text(item, "auth_file_snapshot")
        auth_index = _text(item, "auth_index")
        account_snapshot = _text(item, "account_snapshot")
        locator_hash = _identity_hash(
            auth_file, auth_index, account_snapshot or _text(item, "auth_label_snapshot")
        )
        account = known.get(locator_hash)
        header_subject_hash = _header_subject_hash(account_snapshot)
        if (
            account is not None
            and header_subject_hash
            and account.header_subject_hash
            and header_subject_hash != account.header_subject_hash
        ):
            continue
        if account is None and allow_ephemeral_accounts:
            account = _account_from_header_snapshot(item, f"snapshot-{index}")
        if account is None:
            continue
        observed_number = _number(item.get("timestamp_ms")) or 0
        observed_ms = max(0, int(observed_number))
        observed = _timestamp(observed_ms)
        if observed is None:
            continue
        metadata = item.get("response_metadata")
        quota = metadata.get("quota") if isinstance(metadata, dict) else None
        if not isinstance(quota, dict):
            continue
        try:
            windows = parse_cpa_usage_payload({"quota": quota}, now=observed)
        except ValueError:
            continue
        current = newest.get(account.account_key_hash)
        if current is None or observed_ms >= current[0]:
            newest[account.account_key_hash] = (observed_ms, account, item, quota, windows)

    snapshots: list[CPAMPQuotaSnapshot] = []
    for observed_ms, account, item, quota, windows in newest.values():
        observed = _timestamp(observed_ms)
        if observed is None:
            continue
        plan = map_cpa_plan(item.get("header_quota_plan_type"))
        if plan == "未知套餐":
            plan = map_cpa_plan(quota.get("plan_type"))
        if plan == "未知套餐":
            plan = account.plan
        snapshots.append(
            CPAMPQuotaSnapshot(
                account=account,
                plan=plan,
                windows=windows,
                observed_at=observed.isoformat().replace("+00:00", "Z"),
                stale=_windows_are_stale(windows, observed),
                source="header_snapshots",
            )
        )
    return snapshots


def _windows_are_stale(
    windows: list[dict[str, Any]],
    observed_at: datetime,
    *,
    now: datetime | None = None,
) -> bool:
    current = now or datetime.now(UTC)
    age = current - observed_at
    if age > HEADER_SNAPSHOT_MAX_AGE or age < -HEADER_SNAPSHOT_FUTURE_TOLERANCE:
        return True
    reset_times = [
        reset_at
        for window in windows
        if (reset_at := _timestamp(window.get("reset_at"))) is not None
    ]
    return bool(reset_times) and all(reset_at <= current for reset_at in reset_times)
