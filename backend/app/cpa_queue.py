from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from . import db
from .cpa_quota import (
    CPAAuthAccount,
    CPAChannelAuthenticationError,
    CPAError,
    TIMEOUT,
    discover_cpa_accounts,
    map_cpa_plan,
)
from .logging_config import get_logger, log_event, safe_exception_fields
from .quota import LABEL_MONTHLY, LABEL_ROLLING, LABEL_WEEKLY
from .scheduler import SchedulerLease
from .version import APP_VERSION

CPA_QUEUE_LEASE_NAME = "cpa-usage-queue"
CPA_QUEUE_POLL_SECONDS = 15
CPA_QUEUE_BATCH_SIZE = 100
CPA_QUEUE_MAX_BATCHES = 10
CPA_QUEUE_DB_RETRY_DELAYS = (0.05, 0.1, 0.2)
USER_AGENT = f"QuotaHub/{APP_VERSION}"

logger = get_logger("cpa_queue")
_queue_lock = asyncio.Lock()
_queue_wakeup = asyncio.Event()


class CPAQueueUnsupported(CPAError):
    pass


class CPAQueueCollectionInterrupted(RuntimeError):
    pass


@dataclass(frozen=True)
class CPAQueueObservation:
    provider: str
    auth_index: str
    observed_at: str
    plan: str
    windows: list[dict[str, Any]]


@dataclass
class _CachedAccounts:
    endpoint_revision: int
    loaded_at: float
    accounts: dict[str, CPAAuthAccount]


_account_cache: dict[str, _CachedAccounts] = {}


def wake_cpa_usage_queue() -> None:
    _queue_wakeup.set()


def cache_cpa_accounts(
    channel: db.CPAChannelRow, accounts: list[CPAAuthAccount]
) -> None:
    _account_cache[channel.id] = _CachedAccounts(
        endpoint_revision=channel.cpa_endpoint_revision,
        loaded_at=time.monotonic(),
        accounts={account.auth_index: account for account in accounts},
    )


def invalidate_cpa_account_cache(channel_id: str) -> None:
    _account_cache.pop(channel_id, None)


def _management_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _management_headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }


def _current_queue_channel(original: db.CPAChannelRow) -> db.CPAChannelRow | None:
    current = db.get_cpa_channel(original.id)
    if (
        current is None
        or not current.enabled
        or current.quota_source != "native_queue"
        or not current.queue_enabled
        or not current.exclusive_confirmed_at
        or current.cpa_endpoint_revision != original.cpa_endpoint_revision
        or current.base_url != original.base_url
        or current.management_key != original.management_key
    ):
        return None
    return current


def _header_values(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, (str, int, float)) and not isinstance(item, bool):
                text = str(item).strip()
                if text:
                    result[key.strip().lower()] = text
                    break
    return result


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
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


def _window_label(kind: str, duration_sec: int | None) -> str:
    if duration_sec is not None:
        if duration_sec <= 6 * 3600:
            return LABEL_ROLLING
        if duration_sec <= 10 * 24 * 3600:
            return LABEL_WEEKLY
        return LABEL_MONTHLY
    return LABEL_ROLLING if kind == "primary" else LABEL_WEEKLY


def _parse_window(
    headers: dict[str, str], kind: str, observed: datetime
) -> dict[str, Any] | None:
    prefix = f"x-codex-{kind}-"
    used = _number(headers.get(prefix + "used-percent"))
    if used is None:
        return None
    used = max(0.0, min(100.0, used))
    window_minutes = _number(headers.get(prefix + "window-minutes"))
    duration_sec = (
        max(0, int(window_minutes * 60)) if window_minutes is not None else None
    )
    reset_after = _number(headers.get(prefix + "reset-after-seconds"))
    reset_in_sec = max(0, int(reset_after)) if reset_after is not None else 0
    reset_at = _timestamp(headers.get(prefix + "reset-at"))
    if reset_at is None and reset_in_sec:
        reset_at = observed + timedelta(seconds=reset_in_sec)
    if reset_at is not None and not reset_in_sec:
        reset_in_sec = max(0, int((reset_at - observed).total_seconds()))
    window: dict[str, Any] = {
        "label": _window_label(kind, duration_sec),
        "used": round(used, 2),
        "remaining": round(100.0 - used, 2),
        "total": 100.0,
        "unit": "%",
        "reset_at": (
            reset_at.isoformat().replace("+00:00", "Z") if reset_at else ""
        ),
        "reset_in_sec": reset_in_sec,
    }
    if duration_sec is not None:
        window["duration_sec"] = duration_sec
    return window


def parse_cpa_usage_queue_event(payload: Any) -> CPAQueueObservation | None:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    provider = str(payload.get("provider") or "").strip().lower()
    auth_index = str(payload.get("auth_index") or "").strip()
    observed = _timestamp(payload.get("timestamp"))
    headers = _header_values(payload.get("response_headers"))
    if provider != "codex" or not auth_index or observed is None or not headers:
        return None
    windows = [
        window
        for kind in ("primary", "secondary")
        if (window := _parse_window(headers, kind, observed)) is not None
    ]
    if not windows:
        return None
    order = {LABEL_ROLLING: 0, LABEL_WEEKLY: 1, LABEL_MONTHLY: 2}
    windows.sort(key=lambda item: order.get(str(item.get("label")), 99))
    return CPAQueueObservation(
        provider=provider,
        auth_index=auth_index,
        observed_at=observed.isoformat().replace("+00:00", "Z"),
        plan=map_cpa_plan(headers.get("x-codex-plan-type")),
        windows=windows,
    )


async def _usage_statistics_enabled(
    channel: db.CPAChannelRow, client: httpx.AsyncClient
) -> bool:
    response = await client.get(
        _management_url(channel.base_url, "/v0/management/usage-statistics-enabled"),
        headers=_management_headers(channel.management_key),
    )
    if response.status_code in (401, 403):
        raise CPAChannelAuthenticationError("CPA 管理认证失败")
    if response.status_code in (404, 405):
        raise CPAQueueUnsupported("CPA 不支持 usage statistics 状态接口")
    if response.status_code < 200 or response.status_code >= 300:
        raise CPAError(f"CPA usage statistics 状态返回 HTTP {response.status_code}")
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise CPAError("CPA usage statistics 状态不是有效 JSON") from exc
    if not isinstance(payload, dict):
        raise CPAError("CPA usage statistics 状态格式无效")
    return bool(payload.get("usage-statistics-enabled"))


async def _pop_usage_queue(
    channel: db.CPAChannelRow, client: httpx.AsyncClient
) -> list[Any]:
    response = await client.get(
        _management_url(channel.base_url, "/v0/management/usage-queue"),
        headers=_management_headers(channel.management_key),
        params={"count": CPA_QUEUE_BATCH_SIZE},
    )
    if response.status_code in (401, 403):
        raise CPAChannelAuthenticationError("CPA 管理认证失败")
    if response.status_code in (404, 405):
        raise CPAQueueUnsupported("CPA 不支持 usage queue")
    if response.status_code < 200 or response.status_code >= 300:
        raise CPAError(f"CPA usage queue 返回 HTTP {response.status_code}")
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise CPAError("CPA usage queue 响应不是有效 JSON") from exc
    if not isinstance(payload, list):
        raise CPAError("CPA usage queue 响应格式无效")
    return payload


async def _load_accounts(
    channel: db.CPAChannelRow,
    client: httpx.AsyncClient,
    *,
    force: bool = False,
) -> dict[str, CPAAuthAccount]:
    cached = _account_cache.get(channel.id)
    cache_ttl_seconds = max(300, int(channel.interval_sec))
    if (
        not force
        and cached is not None
        and cached.endpoint_revision == channel.cpa_endpoint_revision
        and time.monotonic() - cached.loaded_at < cache_ttl_seconds
    ):
        return cached.accounts
    accounts = await discover_cpa_accounts(channel, client)
    cache_cpa_accounts(channel, accounts)
    return _account_cache[channel.id].accounts


def _discovery_account(account: CPAAuthAccount) -> db.CPADiscoveryAccount:
    return db.CPADiscoveryAccount(
        account_key_hash=account.account_key_hash,
        legacy_account_key_hashes=tuple(
            value
            for value in (
                account.previous_account_key_hash,
                account.legacy_account_key_hash,
            )
            if value
        ),
        locator_hash=account.locator_hash,
        subject_hash=account.subject_hash,
        account_display=account.account_display,
        plan=account.plan,
    )


def _prepare_account_mapping(
    channel: db.CPAChannelRow, accounts: dict[str, CPAAuthAccount]
) -> None:
    db.prepare_cpa_channel_discovery(
        channel.id,
        [_discovery_account(account) for account in accounts.values()],
        source_mode="native_queue",
    )


async def _record_popped_batch(
    channel: db.CPAChannelRow, snapshots: list[dict[str, Any]]
) -> list[db.SnapshotWriteResult]:
    for attempt in range(len(CPA_QUEUE_DB_RETRY_DELAYS) + 1):
        try:
            return db.record_cpa_quota_batch(
                channel.id,
                snapshots,
                expected_collection_revision=channel.collection_revision,
                endpoint_revision=channel.cpa_endpoint_revision,
            )
        except sqlite3.OperationalError:
            if attempt >= len(CPA_QUEUE_DB_RETRY_DELAYS):
                raise
            await asyncio.sleep(CPA_QUEUE_DB_RETRY_DELAYS[attempt])
    raise RuntimeError("unreachable")


async def collect_cpa_usage_queue_channel(
    channel: db.CPAChannelRow,
    *,
    lease: SchedulerLease,
    run_id: str,
) -> tuple[int, int]:
    processed_count = 0
    discarded_count = 0
    last_poll_at: str | None = None
    started_at = time.monotonic()
    try:
        if not lease.is_valid():
            raise CPAQueueCollectionInterrupted("scheduler lease lost")
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
            cached_before = _account_cache.get(channel.id)
            accounts = await _load_accounts(channel, client)
            mapping_refreshed = (
                cached_before is None
                or _account_cache.get(channel.id) is not cached_before
            )
            if not lease.is_valid():
                raise CPAQueueCollectionInterrupted("scheduler lease lost")
            current = _current_queue_channel(channel)
            if current is None:
                return 0, 0
            if mapping_refreshed:
                _prepare_account_mapping(current, accounts)
            if not await _usage_statistics_enabled(current, client):
                db.record_cpa_queue_state(
                    channel.id,
                    status="config_disabled",
                    error_code="usage_statistics_disabled",
                    expected_collection_revision=channel.collection_revision,
                )
                log_event(
                    logger,
                    logging.WARNING,
                    "cpa_queue_config_disabled",
                    scheduler=CPA_QUEUE_LEASE_NAME,
                    provider="cpa",
                    quota_source="native_queue",
                    channel_id=channel.id,
                    run_id=run_id,
                )
                return 0, 0
            if not accounts:
                db.record_cpa_queue_state(
                    channel.id,
                    status="degraded",
                    error_code="account_mapping_empty",
                    expected_collection_revision=channel.collection_revision,
                )
                log_event(
                    logger,
                    logging.WARNING,
                    "cpa_queue_account_mapping_empty",
                    scheduler=CPA_QUEUE_LEASE_NAME,
                    provider="cpa",
                    quota_source="native_queue",
                    channel_id=channel.id,
                    run_id=run_id,
                )
                return 0, 0

            for batch_index in range(CPA_QUEUE_MAX_BATCHES):
                if not lease.is_valid():
                    raise CPAQueueCollectionInterrupted("scheduler lease lost")
                current = _current_queue_channel(channel)
                if current is None:
                    return processed_count, discarded_count
                last_poll_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                items = await _pop_usage_queue(current, client)

                observations = [
                    observation
                    for item in items
                    if (observation := parse_cpa_usage_queue_event(item)) is not None
                ]
                post_pop_channel = _current_queue_channel(channel)
                if observations and not mapping_refreshed and post_pop_channel is not None:
                    # A popped batch is irreversible. Finish its identity refresh and
                    # persistence; the loop checks the lease before the next pop.
                    try:
                        accounts = await _load_accounts(
                            post_pop_channel, client, force=True
                        )
                        _prepare_account_mapping(post_pop_channel, accounts)
                        mapping_refreshed = True
                    except db.CollectionGuardRejected:
                        discarded_count += len(items)
                        return processed_count, discarded_count
                    except Exception as exc:
                        discarded_count += len(items)
                        try:
                            db.record_cpa_queue_state(
                                channel.id,
                                status="degraded",
                                polled_at=last_poll_at,
                                error_code="account_discovery_refresh_failed",
                                expected_collection_revision=channel.collection_revision,
                            )
                        except (db.CollectionGuardRejected, sqlite3.Error):
                            pass
                        log_event(
                            logger,
                            logging.WARNING,
                            "cpa_queue_account_refresh_failed",
                            scheduler=CPA_QUEUE_LEASE_NAME,
                            provider="cpa",
                            quota_source="native_queue",
                            channel_id=channel.id,
                            run_id=run_id,
                            event_count=len(items),
                            **safe_exception_fields(
                                exc, "account_discovery_refresh_failed"
                            ),
                        )
                        return processed_count, discarded_count

                newest_event_at: str | None = None
                batch_discarded = len(items) - len(observations)
                batch_processed = 0
                candidates: list[tuple[CPAQueueObservation, CPAAuthAccount, str]] = []
                for observation in observations:
                    account = accounts.get(observation.auth_index)
                    if account is None:
                        batch_discarded += 1
                        continue
                    plan = (
                        observation.plan
                        if observation.plan != "未知套餐"
                        else account.plan
                    )
                    candidates.append((observation, account, plan))

                write_results: list[db.SnapshotWriteResult] = []
                if candidates:
                    try:
                        write_results = await _record_popped_batch(
                            channel,
                            [
                                {
                                    "account_key_hash": account.account_key_hash,
                                    "account_display": account.account_display,
                                    "plan": plan,
                                    "windows": observation.windows,
                                    "observed_at": observation.observed_at,
                                }
                                for observation, account, plan in candidates
                            ],
                        )
                    except db.CollectionGuardRejected:
                        batch_discarded += len(candidates)
                        discarded_count += batch_discarded
                        return processed_count, discarded_count
                    except Exception as exc:
                        batch_discarded += len(candidates)
                        discarded_count += batch_discarded
                        try:
                            db.record_cpa_queue_state(
                                channel.id,
                                status="degraded",
                                polled_at=last_poll_at,
                                error_code="event_persistence_failed",
                                expected_collection_revision=channel.collection_revision,
                            )
                        except (db.CollectionGuardRejected, sqlite3.Error):
                            pass
                        log_event(
                            logger,
                            logging.WARNING,
                            "cpa_queue_event_failed",
                            scheduler=CPA_QUEUE_LEASE_NAME,
                            provider="cpa",
                            quota_source="native_queue",
                            channel_id=channel.id,
                            run_id=run_id,
                            event_count=len(candidates),
                            **safe_exception_fields(exc, "event_persistence_failed"),
                        )
                        return processed_count, discarded_count

                for (observation, _account, _plan), result in zip(
                    candidates, write_results, strict=True
                ):
                    if not result.applied:
                        batch_discarded += 1
                        log_event(
                            logger,
                            logging.WARNING,
                            "cpa_queue_result_discarded",
                            scheduler=CPA_QUEUE_LEASE_NAME,
                            provider="cpa",
                            quota_source="native_queue",
                            channel_id=channel.id,
                            public_id=result.public_id,
                            run_id=run_id,
                            reason=result.reason or "snapshot_not_applied",
                            event_count=1,
                        )
                        continue
                    processed_count += 1
                    batch_processed += 1
                    if newest_event_at is None or observation.observed_at > newest_event_at:
                        newest_event_at = observation.observed_at
                    log_event(
                        logger,
                        logging.INFO,
                        "cpa_queue_event_processed",
                        scheduler=CPA_QUEUE_LEASE_NAME,
                        provider="cpa",
                        quota_source="native_queue",
                        channel_id=channel.id,
                        public_id=result.public_id,
                        run_id=run_id,
                        windows_count=len(observation.windows),
                    )
                discarded_count += batch_discarded
                status = "active" if batch_processed else "empty"
                error_code = "invalid_or_unknown_event" if batch_discarded else None
                if batch_discarded and not batch_processed:
                    status = "degraded"
                db.record_cpa_queue_state(
                    channel.id,
                    status=status,
                    polled_at=last_poll_at,
                    event_at=newest_event_at,
                    error_code=error_code,
                    expected_collection_revision=channel.collection_revision,
                )
                log_event(
                    logger,
                    logging.DEBUG if not items else logging.INFO,
                    "cpa_queue_batch_empty" if not items else "cpa_queue_batch_processed",
                    scheduler=CPA_QUEUE_LEASE_NAME,
                    provider="cpa",
                    quota_source="native_queue",
                    channel_id=channel.id,
                    run_id=run_id,
                    batch_index=batch_index,
                    event_count=len(items),
                    success_count=batch_processed,
                    skipped_count=batch_discarded,
                )
                if len(items) < CPA_QUEUE_BATCH_SIZE:
                    break

        log_event(
            logger,
            logging.INFO if processed_count or discarded_count else logging.DEBUG,
            "cpa_queue_channel_completed",
            scheduler=CPA_QUEUE_LEASE_NAME,
            provider="cpa",
            quota_source="native_queue",
            channel_id=channel.id,
            run_id=run_id,
            success_count=processed_count,
            skipped_count=discarded_count,
            duration_ms=round((time.monotonic() - started_at) * 1000),
        )
        return processed_count, discarded_count
    except CPAQueueCollectionInterrupted:
        log_event(
            logger,
            logging.WARNING,
            "cpa_queue_lease_lost",
            scheduler=CPA_QUEUE_LEASE_NAME,
            provider="cpa",
            quota_source="native_queue",
            channel_id=channel.id,
            run_id=run_id,
        )
        raise
    except CPAChannelAuthenticationError as exc:
        if _current_queue_channel(channel) is not None:
            db.record_cpa_queue_state(
                channel.id,
                status="auth_error",
                polled_at=last_poll_at,
                error_code="channel_authentication_failed",
                expected_collection_revision=channel.collection_revision,
            )
        log_event(
            logger,
            logging.WARNING,
            "cpa_queue_authentication_failed",
            scheduler=CPA_QUEUE_LEASE_NAME,
            provider="cpa",
            quota_source="native_queue",
            channel_id=channel.id,
            run_id=run_id,
            **safe_exception_fields(exc, "channel_authentication_failed"),
        )
        return processed_count, discarded_count
    except CPAQueueUnsupported as exc:
        if _current_queue_channel(channel) is not None:
            db.record_cpa_queue_state(
                channel.id,
                status="unsupported",
                polled_at=last_poll_at,
                error_code="queue_unsupported",
                expected_collection_revision=channel.collection_revision,
            )
        log_event(
            logger,
            logging.WARNING,
            "cpa_queue_unsupported",
            scheduler=CPA_QUEUE_LEASE_NAME,
            provider="cpa",
            quota_source="native_queue",
            channel_id=channel.id,
            run_id=run_id,
            **safe_exception_fields(exc, "queue_unsupported"),
        )
        return processed_count, discarded_count
    except Exception as exc:
        if _current_queue_channel(channel) is not None:
            try:
                db.record_cpa_queue_state(
                    channel.id,
                    status="degraded",
                    polled_at=last_poll_at,
                    error_code="queue_collection_error",
                    expected_collection_revision=channel.collection_revision,
                )
            except db.CollectionGuardRejected:
                pass
        log_event(
            logger,
            logging.WARNING,
            "cpa_queue_channel_failed",
            scheduler=CPA_QUEUE_LEASE_NAME,
            provider="cpa",
            quota_source="native_queue",
            channel_id=channel.id,
            run_id=run_id,
            **safe_exception_fields(exc, "queue_collection_error"),
        )
        return processed_count, discarded_count


async def collect_cpa_usage_queues(*, owner_id: str | None = None) -> None:
    if _queue_lock.locked():
        return
    async with _queue_lock:
        lease = SchedulerLease(
            CPA_QUEUE_LEASE_NAME, **({"owner_id": owner_id} if owner_id else {})
        )
        if not await lease.acquire():
            return
        run_id: str | None = None
        try:
            channels = [
                channel
                for channel in db.list_cpa_channels(enabled_only=True)
                if channel.quota_source == "native_queue"
                and channel.queue_enabled
                and channel.exclusive_confirmed_at
            ]
            if not channels:
                return
            run_id = uuid.uuid4().hex[:8]
            cycle_processed = 0
            cycle_discarded = 0
            log_event(
                logger,
                logging.DEBUG,
                "cpa_queue_cycle_started",
                scheduler=CPA_QUEUE_LEASE_NAME,
                owner_id=lease.owner_id,
                provider="cpa",
                quota_source="native_queue",
                run_id=run_id,
                channel_count=len(channels),
            )
            for channel in channels:
                if not lease.is_valid():
                    break
                try:
                    processed, discarded = await collect_cpa_usage_queue_channel(
                        channel, lease=lease, run_id=run_id
                    )
                    cycle_processed += processed
                    cycle_discarded += discarded
                except CPAQueueCollectionInterrupted:
                    break
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "cpa_queue_cycle_failed",
                scheduler=CPA_QUEUE_LEASE_NAME,
                owner_id=lease.owner_id,
                provider="cpa",
                quota_source="native_queue",
                **safe_exception_fields(exc, "unexpected_cycle_error"),
                **({"run_id": run_id} if run_id else {}),
            )
        finally:
            if run_id is not None:
                log_event(
                    logger,
                    (
                        logging.INFO
                        if cycle_processed or cycle_discarded
                        else logging.DEBUG
                    ),
                    "cpa_queue_cycle_completed",
                    scheduler=CPA_QUEUE_LEASE_NAME,
                    owner_id=lease.owner_id,
                    provider="cpa",
                    quota_source="native_queue",
                    run_id=run_id,
                    success_count=cycle_processed,
                    skipped_count=cycle_discarded,
                )
            await lease.release()


async def cpa_usage_queue_loop() -> None:
    log_event(
        logger,
        logging.INFO,
        "scheduler_started",
        scheduler=CPA_QUEUE_LEASE_NAME,
        poll_seconds=CPA_QUEUE_POLL_SECONDS,
    )
    while True:
        try:
            await collect_cpa_usage_queues()
        except asyncio.CancelledError:
            log_event(
                logger,
                logging.INFO,
                "scheduler_stopped",
                scheduler=CPA_QUEUE_LEASE_NAME,
                reason="cancelled",
            )
            raise
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "scheduler_loop_recovered",
                scheduler=CPA_QUEUE_LEASE_NAME,
                **safe_exception_fields(exc, "unexpected_loop_error"),
            )
        try:
            await asyncio.wait_for(
                _queue_wakeup.wait(), timeout=CPA_QUEUE_POLL_SECONDS
            )
        except TimeoutError:
            pass
        except asyncio.CancelledError:
            log_event(
                logger,
                logging.INFO,
                "scheduler_stopped",
                scheduler=CPA_QUEUE_LEASE_NAME,
                reason="cancelled",
            )
            raise
        finally:
            _queue_wakeup.clear()
