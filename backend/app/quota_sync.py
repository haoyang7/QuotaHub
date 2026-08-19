from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Callable

import httpx

from . import db
from .config import AccountConfig, OllamaAccountConfig, load_service_config
from .cpa_quota import (
    CPAAuthAccount,
    CPAChannelAuthenticationError,
    TIMEOUT as CPA_TIMEOUT,
    discover_cpa_accounts,
)
from .cpa_queue import cache_cpa_accounts
from .cpamp_quota import (
    CPAMPAccount,
    CPAMPAuthenticationError,
    CPAMPError,
    CPAMPQueryUnsupported,
    QUERY_BATCH_SIZE as CPAMP_QUERY_BATCH_SIZE,
    TIMEOUT as CPAMP_TIMEOUT,
    discover_cpamp_accounts,
    fetch_cpamp_header_snapshots,
    parse_cpamp_header_items,
    parse_cpamp_query_items,
    query_cpamp_snapshots_batch,
)
from .ollama_quota import fetch_ollama_quota_for_account
from .quota import fetch_quota_for_account
from .logging_config import get_logger, log_event, safe_exception_fields
from .scheduler import SchedulerLease

POLL_SECONDS = 30
REQUEST_PACING_SECONDS = 1.0
QUOTA_LEASE_NAME = "quota-collection"

_collection_lock = asyncio.Lock()
_wakeup = asyncio.Event()
logger = get_logger("quota_sync")

LeaseCheck = Callable[[], bool]


class QuotaCollectionInterrupted(RuntimeError):
    pass


def _require_lease(lease_check: LeaseCheck | None) -> None:
    if lease_check is not None and not lease_check():
        raise QuotaCollectionInterrupted("scheduler lease lost")


def _run_fields(run_id: str | None) -> dict[str, str]:
    return {"run_id": run_id} if run_id else {}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _is_due(last_attempt_at: str | None, interval_sec: int) -> bool:
    if not last_attempt_at:
        return True
    return (datetime.now(UTC) - _parse_time(last_attempt_at)).total_seconds() >= interval_sec


def _safe_error(value: Any) -> str:
    text = str(value or "")
    if "认证失败" in text or "未登录" in text:
        return "认证失败，请检查账号凭证"
    if "未配置" in text or "为空" in text:
        return "账号凭证未配置"
    return "额度采集失败"


def _safe_cpa_error(value: Any) -> str:
    if isinstance(value, CPAChannelAuthenticationError):
        return "CPA 管理认证失败，请检查管理密钥"
    return "CPA 账号发现失败"


def _safe_cpamp_error(value: Any) -> str:
    if isinstance(value, CPAMPAuthenticationError):
        return "CPAMP 管理认证失败，请检查管理密钥"
    return "CPAMP 快照同步失败"


def _cpamp_discovery_account(account: CPAMPAccount) -> db.CPAMPDiscoveryAccount:
    return db.CPAMPDiscoveryAccount(
        account_key_hash=account.account_key_hash,
        legacy_account_key_hashes=account.legacy_account_key_hashes,
        locator_hash=account.locator_hash,
        subject_hash=account.subject_hash,
        account_display=account.account_display,
        plan=account.plan,
    )


def _cpa_discovery_account(account: CPAAuthAccount) -> db.CPADiscoveryAccount:
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


def _stored_cpamp_accounts(channel_id: str) -> list[CPAMPAccount]:
    return [
        CPAMPAccount(
            row_key=f"stored-{index}",
            auth_index="",
            auth_file_name="",
            account_snapshot="",
            account_key_hash=account.account_key_hash,
            account_display=account.account_display,
            plan=account.plan,
            locator_hash=account.locator_hash,
            subject_hash=account.subject_hash,
        )
        for index, account in enumerate(
            db.list_cpamp_snapshot_identities(channel_id)
        )
    ]


def _current_opencode_account(
    original: db.OpenCodeAccountRow,
) -> db.OpenCodeAccountRow | None:
    current = db.get_opencode_account(original.id)
    if (
        current is None
        or not current.enabled
        or current.collection_revision != original.collection_revision
        or current.auth_cookie != original.auth_cookie
        or current.workspace_id != original.workspace_id
    ):
        return None
    return current


def _current_ollama_account(original: db.OllamaAccountRow) -> db.OllamaAccountRow | None:
    current = db.get_ollama_account(original.id)
    if (
        current is None
        or not current.enabled
        or current.collection_revision != original.collection_revision
        or current.session_cookie != original.session_cookie
    ):
        return None
    return current


def _current_cpa_channel(original: db.CPAChannelRow) -> db.CPAChannelRow | None:
    current = db.get_cpa_channel(original.id)
    if (
        current is None
        or not current.enabled
        or current.quota_source != original.quota_source
        or current.quota_source not in {"none", "native_queue"}
        or current.cpa_endpoint_revision != original.cpa_endpoint_revision
        or current.base_url != original.base_url
        or current.management_key != original.management_key
    ):
        return None
    return current


def _current_cpamp_channel(
    original: db.CPAMPChannelRow,
) -> db.CPAMPChannelRow | None:
    unified = db.get_cpa_channel(original.id)
    current = db.get_cpamp_channel(original.id)
    if (
        unified is None
        or current is None
        or not current.enabled
        or unified.quota_source != "cpamp_snapshot"
        or current.collection_revision != original.collection_revision
        or current.base_url != original.base_url
        or current.management_key != original.management_key
    ):
        return None
    return current


async def collect_opencode_account(
    account: db.OpenCodeAccountRow,
    *,
    lease_check: LeaseCheck | None = None,
    lease_name: str | None = None,
    lease_owner_id: str | None = None,
    run_id: str | None = None,
) -> bool:
    started_at = time.monotonic()
    config = AccountConfig(
        name=account.name,
        workspace_id=account.workspace_id,
        auth_cookie=account.auth_cookie,
        show_rolling=account.show_rolling,
        show_weekly=account.show_weekly,
        show_monthly=account.show_monthly,
    )
    try:
        _require_lease(lease_check)
        result = await fetch_quota_for_account(config, 0)
        _require_lease(lease_check)
        if _current_opencode_account(account) is None:
            log_event(
                logger,
                logging.WARNING,
                "quota_result_discarded",
                provider="opencode",
                account_id=account.id,
                reason="source_deleted_disabled_or_changed",
                **_run_fields(run_id),
            )
            return False
        payload = result.to_dict()
        success = bool(payload.get("success"))
        windows = payload.get("windows") or []
        _require_lease(lease_check)
        db.record_opencode_quota_snapshot(
            account.id,
            success=success,
            windows=windows,
            error=None if success else _safe_error(payload.get("error")),
            expected_collection_revision=account.collection_revision,
            lease_name=lease_name,
            lease_owner_id=lease_owner_id,
        )
        log_event(
            logger,
            logging.INFO if success else logging.WARNING,
            "quota_job_completed" if success else "quota_job_failed",
            provider="opencode",
            account_id=account.id,
            windows_count=len(windows),
            duration_ms=round((time.monotonic() - started_at) * 1000),
            **({} if success else {"error_code": "upstream_quota_error"}),
            **_run_fields(run_id),
        )
        return success
    except db.CollectionGuardRejected as exc:
        if exc.reason == "lease_lost":
            log_event(
                logger,
                logging.WARNING,
                "quota_job_interrupted",
                provider="opencode",
                account_id=account.id,
                reason="lease_lost",
                **_run_fields(run_id),
            )
            raise QuotaCollectionInterrupted("scheduler lease lost") from exc
        log_event(
            logger,
            logging.WARNING,
            "quota_result_discarded",
            provider="opencode",
            account_id=account.id,
            reason="source_deleted_disabled_or_changed",
            **_run_fields(run_id),
        )
        return False
    except QuotaCollectionInterrupted:
        log_event(
            logger,
            logging.WARNING,
            "quota_job_interrupted",
            provider="opencode",
            account_id=account.id,
            reason="lease_lost",
            **_run_fields(run_id),
        )
        raise
    except Exception as exc:
        _require_lease(lease_check)
        if _current_opencode_account(account) is None:
            log_event(
                logger,
                logging.WARNING,
                "quota_result_discarded",
                provider="opencode",
                account_id=account.id,
                reason="source_deleted_disabled_or_changed",
                **_run_fields(run_id),
            )
            return False
        try:
            db.record_opencode_quota_snapshot(
                account.id,
                success=False,
                error=_safe_error(exc),
                expected_collection_revision=account.collection_revision,
                lease_name=lease_name,
                lease_owner_id=lease_owner_id,
            )
        except db.CollectionGuardRejected as guard_exc:
            if guard_exc.reason == "lease_lost":
                log_event(
                    logger,
                    logging.WARNING,
                    "quota_job_interrupted",
                    provider="opencode",
                    account_id=account.id,
                    reason="lease_lost",
                    **_run_fields(run_id),
                )
                raise QuotaCollectionInterrupted("scheduler lease lost") from guard_exc
            log_event(
                logger,
                logging.WARNING,
                "quota_result_discarded",
                provider="opencode",
                account_id=account.id,
                reason="source_deleted_disabled_or_changed",
                **_run_fields(run_id),
            )
            return False
        log_event(
            logger,
            logging.WARNING,
            "quota_job_failed",
            provider="opencode",
            account_id=account.id,
            duration_ms=round((time.monotonic() - started_at) * 1000),
            **safe_exception_fields(exc, "collection_error"),
            **_run_fields(run_id),
        )
        return False


async def collect_ollama_account(
    account: db.OllamaAccountRow,
    *,
    lease_check: LeaseCheck | None = None,
    lease_name: str | None = None,
    lease_owner_id: str | None = None,
    run_id: str | None = None,
) -> bool:
    started_at = time.monotonic()
    config = OllamaAccountConfig(
        name=account.name,
        session_cookie=account.session_cookie,
        show_session=account.show_session,
        show_weekly=account.show_weekly,
    )
    try:
        _require_lease(lease_check)
        result = await fetch_ollama_quota_for_account(config, 0)
        _require_lease(lease_check)
        if _current_ollama_account(account) is None:
            log_event(
                logger,
                logging.WARNING,
                "quota_result_discarded",
                provider="ollama",
                account_id=account.id,
                reason="source_deleted_disabled_or_changed",
                **_run_fields(run_id),
            )
            return False
        payload = result.to_dict()
        success = bool(payload.get("success"))
        windows = payload.get("windows") or []
        _require_lease(lease_check)
        db.record_ollama_quota_snapshot(
            account.id,
            success=success,
            plan=str(payload.get("plan") or "") or None,
            windows=windows,
            error=None if success else _safe_error(payload.get("error")),
            expected_collection_revision=account.collection_revision,
            lease_name=lease_name,
            lease_owner_id=lease_owner_id,
        )
        log_event(
            logger,
            logging.INFO if success else logging.WARNING,
            "quota_job_completed" if success else "quota_job_failed",
            provider="ollama",
            account_id=account.id,
            windows_count=len(windows),
            duration_ms=round((time.monotonic() - started_at) * 1000),
            **({} if success else {"error_code": "upstream_quota_error"}),
            **_run_fields(run_id),
        )
        return success
    except db.CollectionGuardRejected as exc:
        if exc.reason == "lease_lost":
            log_event(
                logger,
                logging.WARNING,
                "quota_job_interrupted",
                provider="ollama",
                account_id=account.id,
                reason="lease_lost",
                **_run_fields(run_id),
            )
            raise QuotaCollectionInterrupted("scheduler lease lost") from exc
        log_event(
            logger,
            logging.WARNING,
            "quota_result_discarded",
            provider="ollama",
            account_id=account.id,
            reason="source_deleted_disabled_or_changed",
            **_run_fields(run_id),
        )
        return False
    except QuotaCollectionInterrupted:
        log_event(
            logger,
            logging.WARNING,
            "quota_job_interrupted",
            provider="ollama",
            account_id=account.id,
            reason="lease_lost",
            **_run_fields(run_id),
        )
        raise
    except Exception as exc:
        _require_lease(lease_check)
        if _current_ollama_account(account) is None:
            log_event(
                logger,
                logging.WARNING,
                "quota_result_discarded",
                provider="ollama",
                account_id=account.id,
                reason="source_deleted_disabled_or_changed",
                **_run_fields(run_id),
            )
            return False
        try:
            db.record_ollama_quota_snapshot(
                account.id,
                success=False,
                error=_safe_error(exc),
                expected_collection_revision=account.collection_revision,
                lease_name=lease_name,
                lease_owner_id=lease_owner_id,
            )
        except db.CollectionGuardRejected as guard_exc:
            if guard_exc.reason == "lease_lost":
                log_event(
                    logger,
                    logging.WARNING,
                    "quota_job_interrupted",
                    provider="ollama",
                    account_id=account.id,
                    reason="lease_lost",
                    **_run_fields(run_id),
                )
                raise QuotaCollectionInterrupted("scheduler lease lost") from guard_exc
            log_event(
                logger,
                logging.WARNING,
                "quota_result_discarded",
                provider="ollama",
                account_id=account.id,
                reason="source_deleted_disabled_or_changed",
                **_run_fields(run_id),
            )
            return False
        log_event(
            logger,
            logging.WARNING,
            "quota_job_failed",
            provider="ollama",
            account_id=account.id,
            duration_ms=round((time.monotonic() - started_at) * 1000),
            **safe_exception_fields(exc, "collection_error"),
            **_run_fields(run_id),
        )
        return False


async def collect_cpa_channel(
    channel: db.CPAChannelRow,
    *,
    lease_check: LeaseCheck | None = None,
    lease_name: str | None = None,
    lease_owner_id: str | None = None,
    run_id: str | None = None,
) -> bool:
    started_at = time.monotonic()
    try:
        _require_lease(lease_check)
        async with httpx.AsyncClient(timeout=CPA_TIMEOUT, follow_redirects=False) as client:
            accounts = await discover_cpa_accounts(channel, client)
            _require_lease(lease_check)
            if _current_cpa_channel(channel) is None:
                log_event(
                    logger,
                    logging.WARNING,
                    "quota_result_discarded",
                    provider="cpa",
                    quota_source=channel.quota_source,
                    channel_id=channel.id,
                    reason="source_deleted_disabled_or_changed",
                    **_run_fields(run_id),
                )
                return False
            db.prepare_cpa_channel_discovery(
                channel.id,
                [_cpa_discovery_account(account) for account in accounts],
                source_mode="native_queue",
                expected_collection_revision=channel.collection_revision,
                lease_name=lease_name,
                lease_owner_id=lease_owner_id,
            )
            cache_cpa_accounts(channel, accounts)
            log_event(
                logger,
                logging.INFO,
                "cpa_discovery_completed",
                provider="cpa",
                quota_source=channel.quota_source,
                channel_id=channel.id,
                accounts_discovered=len(accounts),
                **_run_fields(run_id),
            )
            _require_lease(lease_check)
            if _current_cpa_channel(channel) is not None:
                _require_lease(lease_check)
                db.record_cpa_channel_attempt(
                    channel.id,
                    success=True,
                    expected_collection_revision=channel.collection_revision,
                    lease_name=lease_name,
                    lease_owner_id=lease_owner_id,
                )
                log_event(
                    logger,
                    logging.INFO,
                    "cpa_channel_collection_completed",
                    provider="cpa",
                    quota_source=channel.quota_source,
                    channel_id=channel.id,
                    account_count=len(accounts),
                    success_count=len(accounts),
                    failure_count=0,
                    duration_ms=round((time.monotonic() - started_at) * 1000),
                    **_run_fields(run_id),
                )
                return True
            return False
    except db.CollectionGuardRejected as exc:
        if exc.reason == "lease_lost":
            log_event(
                logger,
                logging.WARNING,
                "quota_job_interrupted",
                provider="cpa",
                quota_source=channel.quota_source,
                channel_id=channel.id,
                reason="lease_lost",
                **_run_fields(run_id),
            )
            raise QuotaCollectionInterrupted("scheduler lease lost") from exc
        log_event(
            logger,
            logging.WARNING,
            "quota_result_discarded",
            provider="cpa",
            quota_source=channel.quota_source,
            channel_id=channel.id,
            reason="source_deleted_disabled_or_changed",
            **_run_fields(run_id),
        )
        return False
    except QuotaCollectionInterrupted:
        log_event(
            logger,
            logging.WARNING,
            "quota_job_interrupted",
            provider="cpa",
            quota_source=channel.quota_source,
            channel_id=channel.id,
            reason="lease_lost",
            **_run_fields(run_id),
        )
        raise
    except Exception as exc:
        _require_lease(lease_check)
        if _current_cpa_channel(channel) is not None:
            try:
                db.record_cpa_channel_attempt(
                    channel.id,
                    success=False,
                    error=_safe_cpa_error(exc),
                    expected_collection_revision=channel.collection_revision,
                    lease_name=lease_name,
                    lease_owner_id=lease_owner_id,
                )
            except db.CollectionGuardRejected as guard_exc:
                if guard_exc.reason == "lease_lost":
                    raise QuotaCollectionInterrupted(
                        "scheduler lease lost"
                    ) from guard_exc
                log_event(
                    logger,
                    logging.WARNING,
                    "quota_result_discarded",
                    provider="cpa",
                    quota_source=channel.quota_source,
                    channel_id=channel.id,
                    reason="source_deleted_disabled_or_changed",
                    **_run_fields(run_id),
                )
                return False
        error_code = (
            "channel_authentication_failed"
            if isinstance(exc, CPAChannelAuthenticationError)
            else "channel_collection_error"
        )
        log_event(
            logger,
            logging.WARNING,
            "cpa_channel_collection_failed",
            provider="cpa",
            quota_source=channel.quota_source,
            channel_id=channel.id,
            duration_ms=round((time.monotonic() - started_at) * 1000),
            **safe_exception_fields(exc, error_code),
            **_run_fields(run_id),
        )
        return False


async def collect_cpamp_channel(
    channel: db.CPAMPChannelRow,
    *,
    lease_check: LeaseCheck | None = None,
    lease_name: str | None = None,
    lease_owner_id: str | None = None,
    run_id: str | None = None,
) -> bool:
    started_at = time.monotonic()
    success_count = 0
    failure_count = 0
    successful_batches = 0
    fresh_snapshot_count = 0
    latest_observed_at: str | None = None
    snapshot_source: str | None = None
    try:
        _require_lease(lease_check)
        async with httpx.AsyncClient(
            timeout=CPAMP_TIMEOUT, follow_redirects=False
        ) as client:
            accounts = []
            discovery_succeeded = False
            try:
                accounts = await discover_cpamp_accounts(channel, client)
                discovery_succeeded = True
            except CPAMPAuthenticationError:
                raise
            except Exception as exc:
                log_event(
                    logger,
                    logging.WARNING,
                    "cpamp_snapshot_batch_failed",
                    provider="cpa",
                    quota_source="cpamp_snapshot",
                    channel_id=channel.id,
                    batch_index=-1,
                    **safe_exception_fields(exc, "account_discovery_error"),
                    **_run_fields(run_id),
                )
                accounts = _stored_cpamp_accounts(channel.id)
            _require_lease(lease_check)
            if _current_cpamp_channel(channel) is None:
                return False

            if discovery_succeeded:
                db.prepare_cpamp_channel_discovery(
                    channel.id,
                    [_cpamp_discovery_account(account) for account in accounts],
                    expected_collection_revision=channel.collection_revision,
                    lease_name=lease_name,
                    lease_owner_id=lease_owner_id,
                )

            fallback_to_headers = not discovery_succeeded
            if discovery_succeeded and accounts:
                log_event(
                    logger,
                    logging.INFO,
                    "cpamp_snapshot_sync_started",
                    provider="cpa",
                    quota_source="cpamp_snapshot",
                    channel_id=channel.id,
                    account_count=len(accounts),
                    snapshot_source="quota_snapshots",
                    **_run_fields(run_id),
                )
                for batch_index, start in enumerate(
                    range(0, len(accounts), CPAMP_QUERY_BATCH_SIZE)
                ):
                    _require_lease(lease_check)
                    batch = accounts[start : start + CPAMP_QUERY_BATCH_SIZE]
                    try:
                        items = await query_cpamp_snapshots_batch(
                            channel, batch, client
                        )
                    except CPAMPQueryUnsupported:
                        fallback_to_headers = True
                        log_event(
                            logger,
                            logging.INFO,
                            "cpamp_snapshot_fallback",
                            provider="cpa",
                            quota_source="cpamp_snapshot",
                            channel_id=channel.id,
                            snapshot_source="header_snapshots",
                            reason="query_unsupported",
                            **_run_fields(run_id),
                        )
                        break
                    except CPAMPAuthenticationError:
                        raise
                    except Exception as exc:
                        failure_count += len(batch)
                        for account in batch:
                            db.record_cpamp_quota_snapshot(
                                channel.id,
                                account.account_key_hash,
                                account_display=account.account_display,
                                plan=account.plan,
                                success=False,
                                error=_safe_cpamp_error(exc),
                                quota_source="quota_snapshots",
                                expected_collection_revision=channel.collection_revision,
                                lease_name=lease_name,
                                lease_owner_id=lease_owner_id,
                            )
                        log_event(
                            logger,
                            logging.WARNING,
                            "cpamp_snapshot_batch_failed",
                            provider="cpa",
                            quota_source="cpamp_snapshot",
                            channel_id=channel.id,
                            batch_index=batch_index,
                            account_count=len(batch),
                            **safe_exception_fields(exc, "snapshot_batch_error"),
                            **_run_fields(run_id),
                        )
                        continue

                    _require_lease(lease_check)
                    if _current_cpamp_channel(channel) is None:
                        return False
                    snapshots = parse_cpamp_query_items(items, batch)
                    for snapshot in snapshots:
                        _require_lease(lease_check)
                        result = db.record_cpamp_quota_snapshot(
                            channel.id,
                            snapshot.account.account_key_hash,
                            account_display=snapshot.account.account_display,
                            plan=snapshot.plan,
                            success=True,
                            windows=snapshot.windows,
                            quota_source=snapshot.source,
                            observed_at=snapshot.observed_at,
                            stale=snapshot.stale,
                            expected_collection_revision=channel.collection_revision,
                            lease_name=lease_name,
                            lease_owner_id=lease_owner_id,
                        )
                        if not result.applied:
                            failure_count += 1
                            log_event(
                                logger,
                                logging.WARNING,
                                "cpamp_snapshot_discarded",
                                provider="cpa",
                                quota_source="cpamp_snapshot",
                                channel_id=channel.id,
                                public_id=result.public_id,
                                reason=result.reason or "snapshot_not_applied",
                                **_run_fields(run_id),
                            )
                            continue
                        success_count += 1
                        if not snapshot.stale:
                            fresh_snapshot_count += 1
                        if (
                            latest_observed_at is None
                            or snapshot.observed_at > latest_observed_at
                        ):
                            latest_observed_at = snapshot.observed_at
                    successful_batches += 1
                    snapshot_source = "quota_snapshots"
            elif discovery_succeeded:
                successful_batches += 1
                snapshot_source = "quota_snapshots"

            if fallback_to_headers:
                _require_lease(lease_check)
                items = await fetch_cpamp_header_snapshots(channel, client)
                _require_lease(lease_check)
                if _current_cpamp_channel(channel) is None:
                    return False
                snapshots = parse_cpamp_header_items(
                    items,
                    accounts,
                    allow_ephemeral_accounts=not discovery_succeeded,
                )
                discovered = [snapshot.account for snapshot in snapshots]
                if not discovery_succeeded and not discovered:
                    raise CPAMPError(
                        "CPAMP 账号发现失败且没有可用的只读额度快照"
                    )
                if not discovery_succeeded:
                    db.prepare_cpamp_channel_discovery(
                        channel.id,
                        [_cpamp_discovery_account(account) for account in discovered],
                        expected_collection_revision=channel.collection_revision,
                        lease_name=lease_name,
                        lease_owner_id=lease_owner_id,
                    )
                for snapshot in snapshots:
                    _require_lease(lease_check)
                    result = db.record_cpamp_quota_snapshot(
                        channel.id,
                        snapshot.account.account_key_hash,
                        account_display=snapshot.account.account_display,
                        plan=snapshot.plan,
                        success=True,
                        windows=snapshot.windows,
                        quota_source=snapshot.source,
                        observed_at=snapshot.observed_at,
                        stale=snapshot.stale,
                        expected_collection_revision=channel.collection_revision,
                        lease_name=lease_name,
                        lease_owner_id=lease_owner_id,
                    )
                    if not result.applied:
                        failure_count += 1
                        log_event(
                            logger,
                            logging.WARNING,
                            "cpamp_snapshot_discarded",
                            provider="cpa",
                            quota_source="cpamp_snapshot",
                            channel_id=channel.id,
                            public_id=result.public_id,
                            reason=result.reason or "snapshot_not_applied",
                            **_run_fields(run_id),
                        )
                        continue
                    success_count += 1
                    if not snapshot.stale:
                        fresh_snapshot_count += 1
                    if (
                        latest_observed_at is None
                        or snapshot.observed_at > latest_observed_at
                    ):
                        latest_observed_at = snapshot.observed_at
                successful_batches += 1
                snapshot_source = "header_snapshots"

            if successful_batches == 0:
                raise CPAMPError("CPAMP 快照同步没有成功批次")
            _require_lease(lease_check)
            db.record_cpamp_channel_attempt(
                channel.id,
                success=True,
                snapshot_source=snapshot_source,
                source_snapshot_at=latest_observed_at,
                stale=success_count == 0 or fresh_snapshot_count == 0,
                expected_collection_revision=channel.collection_revision,
                lease_name=lease_name,
                lease_owner_id=lease_owner_id,
            )
            log_event(
                logger,
                logging.INFO,
                "cpamp_channel_collection_completed",
                provider="cpa",
                quota_source="cpamp_snapshot",
                channel_id=channel.id,
                success_count=success_count,
                failure_count=failure_count,
                snapshot_source=snapshot_source,
                duration_ms=round((time.monotonic() - started_at) * 1000),
                **_run_fields(run_id),
            )
            return True
    except db.CollectionGuardRejected as exc:
        if exc.reason == "lease_lost":
            raise QuotaCollectionInterrupted("scheduler lease lost") from exc
        log_event(
            logger,
            logging.WARNING,
            "quota_result_discarded",
            provider="cpa",
            quota_source="cpamp_snapshot",
            channel_id=channel.id,
            reason="source_deleted_disabled_or_changed",
            **_run_fields(run_id),
        )
        return False
    except QuotaCollectionInterrupted:
        raise
    except Exception as exc:
        _require_lease(lease_check)
        if _current_cpamp_channel(channel) is not None:
            try:
                db.record_cpamp_channel_attempt(
                    channel.id,
                    success=False,
                    error=_safe_cpamp_error(exc),
                    expected_collection_revision=channel.collection_revision,
                    lease_name=lease_name,
                    lease_owner_id=lease_owner_id,
                )
            except db.CollectionGuardRejected as guard_exc:
                if guard_exc.reason == "lease_lost":
                    raise QuotaCollectionInterrupted(
                        "scheduler lease lost"
                    ) from guard_exc
                return False
        log_event(
            logger,
            logging.WARNING,
            "cpamp_channel_collection_failed",
            provider="cpa",
            quota_source="cpamp_snapshot",
            channel_id=channel.id,
            duration_ms=round((time.monotonic() - started_at) * 1000),
            **safe_exception_fields(
                exc,
                "channel_authentication_failed"
                if isinstance(exc, CPAMPAuthenticationError)
                else "channel_collection_error",
            ),
            **_run_fields(run_id),
        )
        return False


async def collect_due_quotas(*, owner_id: str | None = None) -> None:
    if _collection_lock.locked():
        log_event(
            logger,
            logging.DEBUG,
            "quota_cycle_skipped",
            scheduler=QUOTA_LEASE_NAME,
            reason="in_process_collection_active",
        )
        return
    async with _collection_lock:
        lease = SchedulerLease(
            QUOTA_LEASE_NAME, **({"owner_id": owner_id} if owner_id else {})
        )
        if not await lease.acquire():
            return
        run_id: str | None = None
        cycle_started_at = time.monotonic()
        job_count = 0
        success_count = 0
        failure_count = 0
        skipped_count = 0
        cycle_reason = "completed"
        try:
            service = load_service_config()
            jobs: list[tuple[str, Any]] = []
            if service.quota_sync_opencode_go.auto_sync:
                for account in db.list_opencode_accounts(enabled_only=True):
                    if _is_due(
                        db.get_quota_snapshot_attempt("opencode", account.id),
                        service.quota_sync_opencode_go.interval_sec,
                    ):
                        jobs.append(("opencode", account))
            if service.quota_sync_ollama.auto_sync:
                for account in db.list_ollama_accounts(enabled_only=True):
                    if _is_due(
                        db.get_quota_snapshot_attempt("ollama", account.id),
                        service.quota_sync_ollama.interval_sec,
                    ):
                        jobs.append(("ollama", account))
            for channel in db.list_cpa_channels(enabled_only=True):
                if _is_due(channel.last_attempt_at, channel.interval_sec):
                    if channel.quota_source == "cpamp_snapshot":
                        cpamp = db.get_cpamp_channel(channel.id)
                        if cpamp is not None:
                            jobs.append(("cpamp", cpamp))
                    else:
                        jobs.append(("cpa", channel))

            if not jobs:
                log_event(
                    logger,
                    logging.DEBUG,
                    "quota_cycle_idle",
                    scheduler=QUOTA_LEASE_NAME,
                    owner_id=lease.owner_id,
                    job_count=0,
                )
                return

            run_id = uuid.uuid4().hex[:8]
            job_count = len(jobs)
            log_event(
                logger,
                logging.INFO,
                "quota_cycle_started",
                scheduler=QUOTA_LEASE_NAME,
                owner_id=lease.owner_id,
                run_id=run_id,
                job_count=job_count,
                opencode_jobs=sum(provider == "opencode" for provider, _ in jobs),
                ollama_jobs=sum(provider == "ollama" for provider, _ in jobs),
                cpa_jobs=sum(provider in {"cpa", "cpamp"} for provider, _ in jobs),
            )
            processed = 0
            requests_started = 0
            for provider, account in jobs:
                if not lease.is_valid():
                    cycle_reason = "lease_lost"
                    skipped_count += job_count - processed
                    return
                current = (
                    _current_opencode_account(account)
                    if provider == "opencode"
                    else _current_ollama_account(account)
                    if provider == "ollama"
                    else _current_cpa_channel(account)
                    if provider == "cpa"
                    else _current_cpamp_channel(account)
                )
                if current is None:
                    skipped_count += 1
                    processed += 1
                    continue
                if requests_started > 0 and REQUEST_PACING_SECONDS > 0:
                    await asyncio.sleep(REQUEST_PACING_SECONDS)
                    if not lease.is_valid():
                        cycle_reason = "lease_lost"
                        skipped_count += job_count - processed
                        return
                requests_started += 1
                try:
                    if provider == "opencode":
                        success = await collect_opencode_account(
                            current,
                            lease_check=lease.is_valid,
                            lease_name=QUOTA_LEASE_NAME,
                            lease_owner_id=lease.owner_id,
                            run_id=run_id,
                        )
                    elif provider == "ollama":
                        success = await collect_ollama_account(
                            current,
                            lease_check=lease.is_valid,
                            lease_name=QUOTA_LEASE_NAME,
                            lease_owner_id=lease.owner_id,
                            run_id=run_id,
                        )
                    elif provider == "cpa":
                        success = await collect_cpa_channel(
                            current,
                            lease_check=lease.is_valid,
                            lease_name=QUOTA_LEASE_NAME,
                            lease_owner_id=lease.owner_id,
                            run_id=run_id,
                        )
                    else:
                        success = await collect_cpamp_channel(
                            current,
                            lease_check=lease.is_valid,
                            lease_name=QUOTA_LEASE_NAME,
                            lease_owner_id=lease.owner_id,
                            run_id=run_id,
                        )
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                except QuotaCollectionInterrupted:
                    cycle_reason = "lease_lost"
                    skipped_count += job_count - processed
                    return
                except Exception as exc:
                    failure_count += 1
                    identity_fields = (
                        {
                            "channel_id": account.id,
                            "quota_source": (
                                "cpamp_snapshot" if provider == "cpamp" else account.quota_source
                            ),
                        }
                        if provider in {"cpa", "cpamp"}
                        else {"account_id": account.id}
                    )
                    log_event(
                        logger,
                        logging.ERROR,
                        "quota_job_unexpected_error",
                        provider="cpa" if provider == "cpamp" else provider,
                        run_id=run_id,
                        **identity_fields,
                        **safe_exception_fields(exc, "unexpected_job_error"),
                    )
                processed += 1
        except Exception as exc:
            cycle_reason = "unexpected_error"
            log_event(
                logger,
                logging.ERROR,
                "quota_cycle_failed",
                scheduler=QUOTA_LEASE_NAME,
                owner_id=lease.owner_id,
                **safe_exception_fields(exc, "unexpected_cycle_error"),
                **_run_fields(run_id),
            )
        finally:
            if run_id is not None:
                log_event(
                    logger,
                    logging.INFO if cycle_reason == "completed" else logging.WARNING,
                    "quota_cycle_completed",
                    scheduler=QUOTA_LEASE_NAME,
                    owner_id=lease.owner_id,
                    run_id=run_id,
                    job_count=job_count,
                    success_count=success_count,
                    failure_count=failure_count,
                    skipped_count=skipped_count,
                    duration_ms=round((time.monotonic() - cycle_started_at) * 1000),
                    reason=cycle_reason,
                )
            await lease.release()


def wake_quota_sync() -> None:
    _wakeup.set()


async def quota_sync_loop() -> None:
    log_event(
        logger,
        logging.INFO,
        "scheduler_started",
        scheduler=QUOTA_LEASE_NAME,
        poll_seconds=POLL_SECONDS,
    )
    while True:
        try:
            await collect_due_quotas()
        except asyncio.CancelledError:
            log_event(
                logger,
                logging.INFO,
                "scheduler_stopped",
                scheduler=QUOTA_LEASE_NAME,
                reason="cancelled",
            )
            raise
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "scheduler_loop_recovered",
                scheduler=QUOTA_LEASE_NAME,
                **safe_exception_fields(exc, "unexpected_loop_error"),
            )
        try:
            await asyncio.wait_for(_wakeup.wait(), timeout=POLL_SECONDS)
        except TimeoutError:
            pass
        except asyncio.CancelledError:
            log_event(
                logger,
                logging.INFO,
                "scheduler_stopped",
                scheduler=QUOTA_LEASE_NAME,
                reason="cancelled",
            )
            raise
        finally:
            _wakeup.clear()
