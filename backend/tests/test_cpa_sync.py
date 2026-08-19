from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app import db
from app.cpa_quota import CPAAuthAccount, CPAChannelAuthenticationError, CPAError
from app.quota_sync import QuotaCollectionInterrupted, collect_cpa_channel


def _account(index: int) -> CPAAuthAccount:
    return CPAAuthAccount(
        auth_index=f"raw-auth-{index}",
        auth_file_name=f"account-{index}.json",
        account_key_hash=f"hmac:v1:hash-{index}",
        account_display=f"u{index}***@example.com",
        plan="Plus",
    )


@pytest.mark.asyncio
async def test_cpa_discovery_creates_waiting_accounts_without_quota_requests(
    temp_data_dir,
):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
    )
    discover = AsyncMock(return_value=[_account(1), _account(2)])
    with patch("app.quota_sync.discover_cpa_accounts", discover):
        assert await collect_cpa_channel(channel) is True

    discover.assert_awaited_once()
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]
    assert cached["success"] is True
    assert len(cached["accounts"]) == 2
    assert all(account["success"] is False for account in cached["accounts"])
    assert all(account["windows"] == [] for account in cached["accounts"])


@pytest.mark.asyncio
async def test_cpa_discovery_auth_failure_marks_existing_snapshots_stale(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account = _account(1)
    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[],
        quota_source="usage_queue",
        observed_at="2026-08-15T01:00:00Z",
    )
    db.record_cpa_channel_attempt(channel.id, success=True)
    with patch(
        "app.quota_sync.discover_cpa_accounts",
        AsyncMock(side_effect=CPAChannelAuthenticationError("bad key")),
    ):
        assert await collect_cpa_channel(channel) is False

    cached = db.list_cached_cpa_channels(enabled_only=False)[0]
    assert cached["success"] is False
    assert cached["stale"] is True
    assert cached["accounts"][0]["stale"] is True


def test_cpa_same_observation_refreshes_stale_state(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account = _account(1)
    observed_at = "2026-08-15T01:00:00Z"
    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[],
        quota_source="usage_queue",
        observed_at=observed_at,
    )
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            (
                account.account_key_hash,
                None,
                account.account_display,
                account.plan,
            )
        ],
    )

    db.record_cpa_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[],
        quota_source="usage_queue",
        observed_at=observed_at,
    )

    cached = db.list_cached_cpa_channels(enabled_only=False)[0]
    assert cached["accounts"][0]["stale"] is False
    assert cached["accounts"][0]["success"] is True


@pytest.mark.asyncio
async def test_cpa_discovery_discards_result_after_credential_change(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret-old",
    )

    async def change_key(*_args, **_kwargs):
        db.update_cpa_channel(channel.id, management_key="secret-new")
        return [_account(1)]

    with patch(
        "app.quota_sync.discover_cpa_accounts", AsyncMock(side_effect=change_key)
    ):
        assert await collect_cpa_channel(channel) is False

    current = db.get_cpa_channel(channel.id)
    assert current is not None
    assert current.last_attempt_at is None
    assert current.queue_enabled is False
    assert db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"] == []


@pytest.mark.asyncio
async def test_cpa_discovery_stops_when_lease_is_lost_after_request(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.com", management_key="secret"
    )
    lease_valid = True

    async def lose_lease(*_args, **_kwargs):
        nonlocal lease_valid
        lease_valid = False
        return [_account(1)]

    with patch(
        "app.quota_sync.discover_cpa_accounts",
        AsyncMock(side_effect=lose_lease),
    ):
        with pytest.raises(QuotaCollectionInterrupted):
            await collect_cpa_channel(channel, lease_check=lambda: lease_valid)

    assert db.get_cpa_channel(channel.id).last_attempt_at is None
    assert db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"] == []


@pytest.mark.asyncio
async def test_cpa_unexpected_discovery_error_is_sanitized_in_sqlite(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://proxy.example.com", management_key="secret"
    )
    sentinel = "cpa-error-secret-sentinel"
    with patch(
        "app.quota_sync.discover_cpa_accounts",
        AsyncMock(side_effect=CPAError(sentinel)),
    ):
        assert await collect_cpa_channel(channel) is False

    cached = db.list_cached_cpa_channels(enabled_only=False)[0]
    assert cached["error"] == "CPA 账号发现失败"
    assert sentinel.encode("utf-8") not in db.db_path().read_bytes()
