from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app import db
from app.cpa_queue import (
    CPA_QUEUE_BATCH_SIZE,
    CPA_QUEUE_LEASE_NAME,
    CPAQueueCollectionInterrupted,
    CPAQueueUnsupported,
    _load_accounts,
    _pop_usage_queue,
    _usage_statistics_enabled,
    cache_cpa_accounts,
    collect_cpa_usage_queue_channel,
    collect_cpa_usage_queues,
    parse_cpa_usage_queue_event,
)
from app.cpa_quota import CPAAuthAccount, CPAChannelAuthenticationError


def _event(
    *,
    auth_index: str = "auth-1",
    used: str = "25",
    provider: str = "codex",
) -> dict[str, object]:
    return {
        "provider": provider,
        "auth_index": auth_index,
        "timestamp": "2026-08-15T01:00:00Z",
        "api_key": "must-not-persist",
        "client_ip": "192.0.2.1",
        "user_agent": "must-not-log",
        "fail": {"body": "must-not-persist"},
        "response_headers": {
            "X-Codex-Plan-Type": ["prolite"],
            "X-Codex-Primary-Used-Percent": [used],
            "X-Codex-Primary-Reset-After-Seconds": ["1800"],
            "X-Codex-Primary-Window-Minutes": ["300"],
            "X-Codex-Secondary-Used-Percent": ["40"],
            "X-Codex-Secondary-Window-Minutes": ["10080"],
        },
    }


def _account() -> CPAAuthAccount:
    return CPAAuthAccount(
        auth_index="auth-1",
        auth_file_name="account.json",
        account_key_hash="hmac:v1:account",
        account_display="a***@example.test",
        plan="Plus",
        locator_hash="hmac:v1:locator",
        subject_hash="hmac:v1:subject",
    )


@pytest.mark.asyncio
async def test_account_discovery_cache_uses_channel_interval(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.test",
        management_key="management-secret",
        interval_sec=3600,
    )
    account = _account()
    with patch("app.cpa_queue.time.monotonic", return_value=100.0):
        cache_cpa_accounts(channel, [account])

    discover = AsyncMock(return_value=[account])
    client = AsyncMock(spec=httpx.AsyncClient)
    with (
        patch("app.cpa_queue.time.monotonic", return_value=1901.0),
        patch("app.cpa_queue.discover_cpa_accounts", discover),
    ):
        cached = await _load_accounts(channel, client)

    assert cached == {account.auth_index: account}
    discover.assert_not_awaited()

    with (
        patch("app.cpa_queue.time.monotonic", return_value=3701.0),
        patch("app.cpa_queue.discover_cpa_accounts", discover),
    ):
        refreshed = await _load_accounts(channel, client)

    assert refreshed == {account.auth_index: account}
    discover.assert_awaited_once_with(channel, client)


def test_queue_event_parser_whitelists_headers_and_maps_plan():
    parsed = parse_cpa_usage_queue_event(_event())
    assert parsed is not None
    assert parsed.provider == "codex"
    assert parsed.auth_index == "auth-1"
    assert parsed.plan == "Pro 5x"
    assert [window["label"] for window in parsed.windows] == [
        "5h Rolling",
        "Weekly",
    ]
    assert parsed.windows[0]["remaining"] == 75.0
    assert parsed.windows[0]["reset_at"] == "2026-08-15T01:30:00Z"
    assert parse_cpa_usage_queue_event(_event(provider="openai")) is None


def test_queue_event_parser_accepts_json_encoded_object_items():
    parsed = parse_cpa_usage_queue_event(json.dumps(_event()))

    assert parsed is not None
    assert parsed.auth_index == "auth-1"
    assert parsed.plan == "Pro 5x"
    assert parse_cpa_usage_queue_event("not-json") is None
    assert parse_cpa_usage_queue_event(json.dumps([_event()])) is None
    assert parse_cpa_usage_queue_event(json.dumps(json.dumps(_event()))) is None


@pytest.mark.asyncio
async def test_queue_protocol_uses_only_fixed_get_endpoints(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.test",
        management_key="management-secret",
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.method == "GET"
        assert request.headers["authorization"] == "Bearer management-secret"
        if request.url.path.endswith("usage-statistics-enabled"):
            return httpx.Response(200, json={"usage-statistics-enabled": True})
        assert request.url.path == "/v0/management/usage-queue"
        assert dict(request.url.params) == {"count": str(CPA_QUEUE_BATCH_SIZE)}
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await _usage_statistics_enabled(channel, client) is True
        assert await _pop_usage_queue(channel, client) == []

    assert [request.url.path for request in seen] == [
        "/v0/management/usage-statistics-enabled",
        "/v0/management/usage-queue",
    ]
    app_source = Path(__file__).parents[1] / "app"
    tracked_source = b"".join(path.read_bytes() for path in app_source.glob("*.py"))
    assert b"/v0/management/api-call" not in tracked_source
    assert b"chatgpt.com/backend-api/wham/usage" not in tracked_source


@pytest.mark.asyncio
async def test_queue_authentication_failure_is_classified(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.test",
        management_key="wrong",
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CPAChannelAuthenticationError):
            await _usage_statistics_enabled(channel, client)


@pytest.mark.asyncio
async def test_unconfirmed_channel_never_starts_queue_collection(temp_data_dir):
    db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.test",
        management_key="secret",
    )
    collector = AsyncMock()
    with patch("app.cpa_queue.collect_cpa_usage_queue_channel", collector):
        await collect_cpa_usage_queues(owner_id="unconfirmed-owner")

    collector.assert_not_awaited()


@pytest.mark.asyncio
async def test_queue_lease_single_flight_then_collects_multiple_channels(temp_data_dir):
    channels = []
    for index in range(2):
        channel = db.create_cpa_channel(
            name=f"CPA {index}",
            base_url=f"https://proxy-{index}.example.test",
            management_key="secret",
        )
        confirmed = db.configure_cpa_usage_queue(
            channel.id, enabled=True, confirm_exclusive=True
        )
        assert confirmed is not None
        channels.append(confirmed)

    assert db.acquire_scheduler_lease(
        CPA_QUEUE_LEASE_NAME, "current-owner"
    ) is True
    collector = AsyncMock(return_value=(0, 0))
    with patch("app.cpa_queue.collect_cpa_usage_queue_channel", collector):
        await collect_cpa_usage_queues(owner_id="other-owner")
    collector.assert_not_awaited()

    assert db.release_scheduler_lease(CPA_QUEUE_LEASE_NAME, "current-owner") is True
    with patch("app.cpa_queue.collect_cpa_usage_queue_channel", collector):
        await collect_cpa_usage_queues(owner_id="other-owner")

    assert [call.args[0].id for call in collector.await_args_list] == [
        channel.id for channel in channels
    ]


@pytest.mark.asyncio
async def test_usage_statistics_disabled_does_not_pop_queue(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    pop = AsyncMock()
    with (
        patch("app.cpa_queue._load_accounts", AsyncMock(return_value={})),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=False)),
        patch("app.cpa_queue._pop_usage_queue", pop),
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="config-disabled"
        ) == (0, 0)

    pop.assert_not_awaited()
    current = db.get_cpa_channel(channel.id)
    assert current is not None
    assert current.queue_status == "config_disabled"
    assert current.queue_last_error_code == "usage_statistics_disabled"
    assert current.queue_last_poll_at is None


@pytest.mark.asyncio
async def test_discovery_failure_does_not_claim_a_queue_poll(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    with (
        patch(
            "app.cpa_queue._load_accounts",
            AsyncMock(side_effect=RuntimeError("discovery-private-detail")),
        ),
        patch("app.cpa_queue._pop_usage_queue", AsyncMock()) as pop,
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="discovery-failure"
        ) == (0, 0)

    pop.assert_not_awaited()
    current = db.get_cpa_channel(channel.id)
    assert current is not None
    assert current.queue_status == "degraded"
    assert current.queue_last_poll_at is None
    assert current.queue_last_error_code == "queue_collection_error"


@pytest.mark.asyncio
async def test_queue_unsupported_is_persisted_without_retrying_batches(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    pop = AsyncMock(side_effect=CPAQueueUnsupported("unsupported"))
    with (
        patch(
            "app.cpa_queue._load_accounts",
            AsyncMock(return_value={_account().auth_index: _account()}),
        ),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", pop),
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="unsupported"
        ) == (0, 0)

    pop.assert_awaited_once()
    current = db.get_cpa_channel(channel.id)
    assert current is not None
    assert current.queue_status == "unsupported"
    assert current.queue_last_error_code == "queue_unsupported"
    assert current.queue_last_poll_at is not None


@pytest.mark.asyncio
async def test_empty_account_mapping_never_pops_destructive_queue(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    pop = AsyncMock()
    with (
        patch("app.cpa_queue._load_accounts", AsyncMock(return_value={})),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", pop),
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="empty-mapping"
        ) == (0, 0)

    pop.assert_not_awaited()
    current = db.get_cpa_channel(channel.id)
    assert current is not None
    assert current.queue_status == "degraded"
    assert current.queue_last_error_code == "account_mapping_empty"


@pytest.mark.asyncio
async def test_queue_cycle_refreshes_replaced_account_before_pop(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    previous = _account()
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=previous.account_key_hash,
                legacy_account_key_hashes=(),
                locator_hash=previous.locator_hash,
                subject_hash=previous.subject_hash,
                account_display=previous.account_display,
                plan=previous.plan,
            )
        ],
    )
    previous_public_id = db.list_cached_cpa_channels(enabled_only=False)[0][
        "accounts"
    ][0]["public_id"]
    replacement = CPAAuthAccount(
        auth_index=previous.auth_index,
        auth_file_name=previous.auth_file_name,
        account_key_hash="hmac:v1:replacement",
        account_display="r***@example.test",
        plan="Plus",
        locator_hash=previous.locator_hash,
        subject_hash="hmac:v1:replacement-subject",
    )
    cache_cpa_accounts(channel, [previous])

    with (
        patch(
            "app.cpa_queue.discover_cpa_accounts",
            AsyncMock(return_value=[replacement]),
        ) as discover,
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", AsyncMock(return_value=[_event()])),
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="replacement"
        ) == (0, 1)

    discover.assert_awaited_once()
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert len(cached) == 1
    assert cached[0]["account"] == replacement.account_display
    assert cached[0]["public_id"] != previous_public_id
    assert cached[0]["success"] is False
    assert cached[0]["windows"] == []
    replacement_public_id = cached[0]["public_id"]

    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=replacement.account_key_hash,
                legacy_account_key_hashes=(),
                locator_hash=replacement.locator_hash,
                subject_hash=replacement.subject_hash,
                account_display=replacement.account_display,
                plan=replacement.plan,
            )
        ],
    )
    rediscovered = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert rediscovered[0]["public_id"] == replacement_public_id


class _Lease:
    def __init__(self) -> None:
        self.valid = True

    def is_valid(self) -> bool:
        return self.valid


@pytest.mark.asyncio
async def test_popped_batch_is_written_after_lease_loss_but_no_next_request(
    temp_data_dir,
):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    cache_cpa_accounts(channel, [account])
    lease = _Lease()
    pop = AsyncMock()
    load_accounts = AsyncMock(return_value={account.auth_index: account})

    async def lose_after_pop(*_args, **_kwargs):
        lease.valid = False
        return [_event() for _ in range(CPA_QUEUE_BATCH_SIZE)]

    pop.side_effect = lose_after_pop
    with (
        patch("app.cpa_queue._load_accounts", load_accounts),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", pop),
    ):
        with pytest.raises(CPAQueueCollectionInterrupted):
            await collect_cpa_usage_queue_channel(
                channel, lease=lease, run_id="lease-test"
            )

    pop.assert_awaited_once()
    assert load_accounts.await_count == 2
    assert load_accounts.await_args_list[1].kwargs == {"force": True}
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert len(cached) == 1
    assert cached[0]["quota_source"] == "usage_queue"
    assert cached[0]["plan"] == "Pro 5x"
    raw = db.db_path().read_bytes()
    for secret in (
        b"auth-1",
        b"must-not-persist",
        b"192.0.2.1",
    ):
        assert secret not in raw


@pytest.mark.asyncio
async def test_popped_batch_is_persisted_after_channel_disable(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    lease = _Lease()

    async def disable_after_pop(*_args, **_kwargs):
        db.update_cpa_channel(channel.id, enabled=False)
        return [_event()]

    with (
        patch(
            "app.cpa_queue._load_accounts",
            AsyncMock(return_value={account.auth_index: account}),
        ),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch(
            "app.cpa_queue._pop_usage_queue", AsyncMock(side_effect=disable_after_pop)
        ),
    ):
        processed, discarded = await collect_cpa_usage_queue_channel(
            channel, lease=lease, run_id="disable-test"
        )

    assert processed == 1
    assert discarded == 0
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert len(cached) == 1
    assert cached[0]["success"] is True
    assert cached[0]["windows"]
    assert db.list_cached_cpa_channels(enabled_only=True) == []


@pytest.mark.asyncio
async def test_popped_native_batch_stays_historical_after_switch_to_cpamp(
    temp_data_dir,
):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.test",
        management_key="native-secret",
        cpamp_base_url="https://cpamp.example.test",
        cpamp_management_key="snapshot-secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    native_account = _account()
    cache_cpa_accounts(channel, [native_account])
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=native_account.account_key_hash,
                legacy_account_key_hashes=(),
                locator_hash=native_account.locator_hash,
                subject_hash=native_account.subject_hash,
                account_display=native_account.account_display,
                plan=native_account.plan,
            )
        ],
        source_mode="native_queue",
    )
    cpamp_hash = "hmac:v1:cpamp-current"

    async def switch_source_after_pop(*_args, **_kwargs):
        switched = db.set_cpa_quota_source(
            channel.id, source="cpamp_snapshot"
        )
        assert switched is not None
        db.prepare_cpa_channel_discovery(
            channel.id,
            [
                db.CPADiscoveryAccount(
                    account_key_hash=cpamp_hash,
                    legacy_account_key_hashes=(),
                    locator_hash="hmac:v1:cpamp-locator",
                    subject_hash="hmac:v1:cpamp-subject",
                    account_display="c***@example.test",
                    plan="Plus",
                )
            ],
            source_mode="cpamp_snapshot",
        )
        db.record_cpa_quota_snapshot(
            channel.id,
            cpamp_hash,
            account_display="c***@example.test",
            plan="Plus",
            success=True,
            windows=[{"kind": "primary", "used_percent": 10}],
            quota_source="quota_snapshots",
            observed_at="2026-08-15T00:59:00Z",
            source_mode="cpamp_snapshot",
        )
        return [_event()]

    load_accounts = AsyncMock(
        return_value={native_account.auth_index: native_account}
    )
    pop = AsyncMock(side_effect=switch_source_after_pop)
    with (
        patch("app.cpa_queue._load_accounts", load_accounts),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", pop),
    ):
        processed, discarded = await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="source-switch-test"
        )

    assert (processed, discarded) == (1, 0)
    pop.assert_awaited_once()
    load_accounts.assert_awaited_once()
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]
    assert cached["quota_source"] == "cpamp_snapshot"
    assert [account["account"] for account in cached["accounts"]] == [
        "c***@example.test"
    ]
    with db.get_conn() as conn:
        native_snapshot = conn.execute(
            """
            SELECT windows_json, source_mode, endpoint_revision
            FROM cpa_quota_snapshots
            WHERE channel_id = ? AND canonical_account_hash = ?
            """,
            (channel.id, native_account.account_key_hash),
        ).fetchone()
        native_visibility = conn.execute(
            """
            SELECT visible FROM cpa_accounts
            WHERE channel_id = ? AND canonical_account_hash = ?
            """,
            (channel.id, native_account.account_key_hash),
        ).fetchone()
    assert native_snapshot is not None
    assert native_snapshot["source_mode"] == "native_queue"
    assert json.loads(native_snapshot["windows_json"])
    assert native_visibility is not None
    assert native_visibility["visible"] == 0


@pytest.mark.asyncio
async def test_nonempty_batch_refresh_failure_discards_all_popped_events(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    cache_cpa_accounts(channel, [account])
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=account.account_key_hash,
                legacy_account_key_hashes=(),
                locator_hash=account.locator_hash,
                subject_hash=account.subject_hash,
                account_display=account.account_display,
                plan=account.plan,
            )
        ],
    )
    load_accounts = AsyncMock(
        side_effect=[
            {account.auth_index: account},
            RuntimeError("refresh-private-detail"),
        ]
    )
    with (
        patch("app.cpa_queue._load_accounts", load_accounts),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch(
            "app.cpa_queue._pop_usage_queue",
            AsyncMock(
                return_value=[
                    _event(auth_index=account.auth_index),
                    _event(auth_index="unknown-account"),
                ]
            ),
        ),
    ):
        processed, discarded = await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="refresh-failure"
        )

    assert load_accounts.await_count == 2
    assert (processed, discarded) == (0, 2)
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert len(cached) == 1
    assert cached[0]["success"] is False
    assert cached[0]["windows"] == []
    assert b"refresh-private-detail" not in db.db_path().read_bytes()


@pytest.mark.asyncio
async def test_queue_channel_processes_at_most_ten_full_batches(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    pop = AsyncMock(return_value=[_event() for _ in range(CPA_QUEUE_BATCH_SIZE)])
    with (
        patch(
            "app.cpa_queue._load_accounts",
            AsyncMock(return_value={account.auth_index: account}),
        ),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", pop),
    ):
        processed, discarded = await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="ten-batches"
        )

    assert pop.await_count == 10
    assert processed == CPA_QUEUE_BATCH_SIZE * 10
    assert discarded == 0


@pytest.mark.asyncio
async def test_popped_batch_retries_transient_sqlite_lock(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    real_record_batch = db.record_cpa_quota_batch
    attempts = 0

    def flaky_record_batch(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise sqlite3.OperationalError("database is locked")
        return real_record_batch(*args, **kwargs)

    sleep = AsyncMock()
    with (
        patch(
            "app.cpa_queue._load_accounts",
            AsyncMock(return_value={account.auth_index: account}),
        ),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", AsyncMock(return_value=[_event()])),
        patch(
            "app.cpa_queue.db.record_cpa_quota_batch",
            side_effect=flaky_record_batch,
        ),
        patch("app.cpa_queue.asyncio.sleep", sleep),
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="sqlite-retry"
        ) == (1, 0)

    assert attempts == 3
    assert [item.args[0] for item in sleep.await_args_list] == [0.05, 0.1]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["auth", "config_disabled", "unsupported"])
async def test_queue_failures_mark_existing_quota_stale(temp_data_dir, failure):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at="2026-08-17T09:00:00Z",
    )
    db.record_cpa_channel_attempt(channel.id, success=True)

    load_accounts = AsyncMock(return_value={account.auth_index: account})
    usage_enabled = AsyncMock(return_value=True)
    pop = AsyncMock(return_value=[])
    if failure == "auth":
        load_accounts.side_effect = CPAChannelAuthenticationError("private-auth")
    elif failure == "config_disabled":
        usage_enabled.return_value = False
    else:
        pop.side_effect = CPAQueueUnsupported("private-unsupported")

    with (
        patch("app.cpa_queue._load_accounts", load_accounts),
        patch("app.cpa_queue._usage_statistics_enabled", usage_enabled),
        patch("app.cpa_queue._pop_usage_queue", pop),
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id=f"stale-{failure}"
        ) == (0, 0)

    cached = db.list_cached_cpa_channels(enabled_only=True)[0]
    assert cached["stale"] is True
    assert cached["accounts"][0]["stale"] is True
    assert cached["accounts"][0]["windows"][0]["remaining"] == 80


@pytest.mark.asyncio
async def test_successful_queue_event_clears_channel_stale_after_failure(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at="2026-08-14T09:00:00Z",
    )
    db.record_cpa_channel_attempt(channel.id, success=True)
    db.record_cpa_queue_state(
        channel.id,
        status="auth_error",
        error_code="channel_authentication_failed",
        expected_collection_revision=channel.collection_revision,
    )
    db.record_cpa_queue_state(
        channel.id,
        status="empty",
        expected_collection_revision=channel.collection_revision,
    )
    assert db.list_cached_cpa_channels(enabled_only=True)[0]["stale"] is True

    with (
        patch(
            "app.cpa_queue._load_accounts",
            AsyncMock(return_value={account.auth_index: account}),
        ),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", AsyncMock(return_value=[_event()])),
    ):
        assert await collect_cpa_usage_queue_channel(
            channel, lease=_Lease(), run_id="stale-recovery"
        ) == (1, 0)

    cached = db.list_cached_cpa_channels(enabled_only=True)[0]
    assert cached["stale"] is False
    assert cached["accounts"][0]["stale"] is False
    assert cached["accounts"][0]["windows"][0]["remaining"] == 75.0


@pytest.mark.asyncio
async def test_empty_queue_uses_cached_mapping_without_info_cycle_logs(
    temp_data_dir, caplog
):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    channel = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert channel is not None
    account = _account()
    cache_cpa_accounts(channel, [account])
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=account.account_key_hash,
                legacy_account_key_hashes=(),
                locator_hash=account.locator_hash,
                subject_hash=account.subject_hash,
                account_display=account.account_display,
                plan=account.plan,
            )
        ],
    )
    discover = AsyncMock(return_value=[account])
    caplog.set_level(logging.INFO, logger="quotahub.cpa_queue")

    with (
        patch("app.cpa_queue.discover_cpa_accounts", discover),
        patch("app.cpa_queue._usage_statistics_enabled", AsyncMock(return_value=True)),
        patch("app.cpa_queue._pop_usage_queue", AsyncMock(return_value=[])),
    ):
        await collect_cpa_usage_queues(owner_id="empty-queue-owner")

    discover.assert_not_awaited()
    emitted = {
        record.getMessage()
        for record in caplog.records
        if record.name == "quotahub.cpa_queue"
    }
    assert "cpa_queue_batch_empty" not in emitted
    assert "cpa_queue_channel_completed" not in emitted
    assert "cpa_queue_cycle_completed" not in emitted


def test_queue_observation_updates_monotonically(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account = _account()
    newer = datetime(2026, 8, 15, 2, 0, tzinfo=UTC).isoformat().replace(
        "+00:00", "Z"
    )
    older = datetime(2026, 8, 15, 1, 0, tzinfo=UTC).isoformat().replace(
        "+00:00", "Z"
    )
    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan="Pro 20x",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        quota_source="usage_queue",
        observed_at=newer,
    )
    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan="Free",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 10}],
        quota_source="usage_queue",
        observed_at=older,
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"][0]
    assert cached["plan"] == "Pro 20x"
    assert cached["windows"][0]["remaining"] == 80
    assert cached["observed_at"] == newer


def test_older_queue_observation_does_not_refresh_success_state(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.test", management_key="secret"
    )
    account = _account()
    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan="Pro 20x",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        attempted_at="2026-08-17T10:00:00Z",
        observed_at="2026-08-17T09:00:00Z",
    )
    db.prepare_cpa_channel_discovery(
        channel.id,
        [(account.account_key_hash, None, account.account_display, account.plan)],
    )

    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan="Free",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 10}],
        attempted_at="2026-08-17T11:00:00Z",
        observed_at="2026-08-17T08:00:00Z",
    )

    with db.get_conn() as conn:
        row = conn.execute(
            """
            SELECT last_success_at, stale, plan, windows_json
            FROM cpa_quota_snapshots
            WHERE channel_id = ? AND account_key_hash = ?
            """,
            (channel.id, account.account_key_hash),
        ).fetchone()
    assert row is not None
    assert row["last_success_at"] == "2026-08-17T10:00:00Z"
    assert bool(row["stale"]) is False
    assert row["plan"] == "Pro 20x"
    assert '"remaining": 80' in row["windows_json"]
