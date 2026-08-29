from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app import db
from app.cpamp_quota import (
    CPAMPAccount,
    CPAMPAuthenticationError,
    CPAMPError,
    CPAMPQueryUnsupported,
    discover_cpamp_accounts,
    fetch_cpamp_header_snapshots,
    parse_cpamp_auth_files,
    parse_cpamp_header_items,
    parse_cpamp_query_items,
    parse_cpamp_signal_snapshot,
    query_cpamp_snapshots_batch,
)
from app.cpa_quota import auth_tag_from_locator, mask_auth_file_name
from app.quota_sync import collect_cpamp_channel


def _account(index: int = 1) -> CPAMPAccount:
    return CPAMPAccount(
        row_key=f"account-{index}",
        auth_index=f"auth-{index}",
        auth_file_name=f"account-{index}.json",
        account_snapshot="",
        account_key_hash=f"hmac:v1:cpamp-{index}",
        account_display=f"u{index}***@example.test",
        plan="Plus",
    )


def _query_item(account: CPAMPAccount, *, used: float = 25) -> dict[str, object]:
    observed_ms = int(datetime(2026, 8, 15, 1, 0, tzinfo=UTC).timestamp() * 1000)
    return {
        "row_key": account.row_key,
        "account_key": "cpamp-internal-must-not-persist",
        "provider": "codex",
        "windows": [
            {
                "provider_window_id": "primary",
                "window_kind": "primary",
                "window_mode": "fixed",
                "used_percent": used,
                "remaining_percent": 100 - used,
                "cycle_end_ms": observed_ms + 1800 * 1000,
                "duration_seconds": 18000,
                "plan_type": "pro",
                "stale": False,
                "observed_at_ms": observed_ms,
            }
        ],
    }


def _subject_payload(subject: str, *, email: str) -> dict[str, object]:
    return {
        "files": [
            {
                "provider": "codex",
                "auth_index": "shared-auth-index",
                "name": "shared-account.json",
                "email": email,
                "id_token": {
                    "chatgpt_account_id": subject,
                    "plan_type": "plus",
                },
            }
        ]
    }


def test_cpamp_query_metadata_follows_selected_latest_window():
    account = _account()
    items = [
        {
            "row_key": account.row_key,
            "windows": [
                {
                    "provider_window_id": "primary",
                    "used_percent": 10,
                    "plan_type": "plus",
                    "stale": False,
                    "observed_at_ms": 2_000,
                },
                {
                    "provider_window_id": "primary",
                    "used_percent": 90,
                    "plan_type": "free",
                    "stale": True,
                    "observed_at_ms": 1_000,
                },
            ],
        }
    ]

    snapshot = parse_cpamp_query_items(items, [account])[0]

    assert snapshot.plan == "Plus"
    assert snapshot.stale is False
    assert snapshot.windows[0]["remaining"] == 90.0


def test_cpamp_header_fallback_uses_latest_snapshot_with_quota(temp_data_dir):
    account = _account()
    snapshots = parse_cpamp_header_items(
        [
            {
                "timestamp_ms": 1_000,
                "auth_file_snapshot": account.auth_file_name,
                "auth_index": account.auth_index,
                "response_metadata": {
                    "quota": {"primary": {"used_percent": 20}}
                },
            },
            {
                "timestamp_ms": 2_000,
                "auth_file_snapshot": account.auth_file_name,
                "auth_index": account.auth_index,
                "response_metadata": {"error": "upstream failed"},
            },
        ],
        [account],
    )

    assert len(snapshots) == 1
    assert snapshots[0].windows[0]["remaining"] == 80.0


def test_cpamp_subject_identity_migrates_legacy_and_separates_replacement(
    temp_data_dir,
):
    def payload(account_id: str) -> dict[str, object]:
        return {
            "files": [
                {
                    "provider": "codex",
                    "auth_index": "shared-auth-index",
                    "name": "shared-account.json",
                    "email": "same@example.test",
                    "id_token": {
                        "chatgpt_account_id": account_id,
                        "plan_type": "plus",
                    },
                }
            ]
        }

    first = parse_cpamp_auth_files(payload("account-subject-a"))[0]
    replacement = parse_cpamp_auth_files(payload("account-subject-b"))[0]
    assert first.account_key_hash != replacement.account_key_hash
    assert first.subject_hash != replacement.subject_hash
    assert first.header_subject_hash == replacement.header_subject_hash
    assert first.legacy_account_key_hashes[-1] == replacement.legacy_account_key_hashes[-1]

    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    legacy_hash = first.legacy_account_key_hashes[-1]
    db.record_cpamp_quota_snapshot(
        channel.id,
        legacy_hash,
        account_display=first.account_display,
        plan="Pro 20x",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 75}],
        observed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    legacy_public_id = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"][0][
        "public_id"
    ]

    db.prepare_cpamp_channel_discovery(
        channel.id,
        [
            db.CPAMPDiscoveryAccount(
                account_key_hash=first.account_key_hash,
                legacy_account_key_hashes=first.legacy_account_key_hashes,
                locator_hash=first.locator_hash,
                subject_hash=first.subject_hash,
                account_display=first.account_display,
                plan=first.plan,
            )
        ],
    )
    migrated = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"][0]
    assert migrated["public_id"] == legacy_public_id
    assert migrated["plan"] == "Pro 20x"
    assert migrated["windows"][0]["remaining"] == 75

    db.prepare_cpamp_channel_discovery(
        channel.id,
        [
            db.CPAMPDiscoveryAccount(
                account_key_hash=replacement.account_key_hash,
                legacy_account_key_hashes=replacement.legacy_account_key_hashes,
                locator_hash=replacement.locator_hash,
                subject_hash=replacement.subject_hash,
                account_display=replacement.account_display,
                plan=replacement.plan,
            )
        ],
    )
    visible = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"]
    assert len(visible) == 1
    assert visible[0]["public_id"] != legacy_public_id
    assert visible[0]["windows"] == []


def test_cpamp_header_snapshot_rejects_mismatched_subject(temp_data_dir):
    current = parse_cpamp_auth_files(
        _subject_payload("account-subject-b", email="current@example.test")
    )[0]
    observed_ms = int(datetime.now(UTC).timestamp() * 1000)

    snapshots = parse_cpamp_header_items(
        [
            {
                "timestamp_ms": observed_ms,
                "auth_file_snapshot": current.auth_file_name,
                "auth_index": current.auth_index,
                "account_snapshot": "previous@example.test",
                "response_metadata": {
                    "quota": {"primary": {"used_percent": 20}}
                },
            }
        ],
        [current],
    )

    assert snapshots == []


def test_cpamp_same_observation_refreshes_stale_state(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = _account()
    observed_at = "2026-08-15T01:00:00Z"
    db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=observed_at,
        stale=False,
    )
    db.prepare_cpamp_channel_discovery(
        channel.id,
        [(account.account_key_hash, None, account.account_display, account.plan)],
    )

    db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=observed_at,
        stale=False,
    )

    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["accounts"][0]["stale"] is False
    assert cached["accounts"][0]["success"] is True


def test_cpamp_older_observation_does_not_refresh_success_state(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = _account()
    db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        attempted_at="2026-08-17T10:00:00Z",
        observed_at="2026-08-17T09:00:00Z",
    )
    db.prepare_cpamp_channel_discovery(
        channel.id,
        [(account.account_key_hash, None, account.account_display, account.plan)],
    )

    db.record_cpamp_quota_snapshot(
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
                WHERE channel_id = ? AND source_mode = 'cpamp_snapshot'
                """,
                (channel.id,),
        ).fetchone()
    assert row is not None
    assert row["last_success_at"] == "2026-08-17T10:00:00Z"
    assert bool(row["stale"]) is True
    assert row["plan"] == account.plan
    assert '"remaining": 80' in row["windows_json"]


@pytest.mark.asyncio
async def test_cpamp_replacement_rejects_historical_query_snapshot(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    first = parse_cpamp_auth_files(
        _subject_payload("account-subject-a", email="first@example.test")
    )[0]
    replacement = parse_cpamp_auth_files(
        _subject_payload("account-subject-b", email="replacement@example.test")
    )[0]

    with (
        patch("app.quota_sync.discover_cpamp_accounts", AsyncMock(return_value=[first])),
        patch(
            "app.quota_sync.query_cpamp_snapshots_batch",
            AsyncMock(return_value=[_query_item(first)]),
        ),
    ):
        assert await collect_cpamp_channel(channel) is True
    first_cached = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"][0]

    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[replacement]),
        ),
        patch(
            "app.quota_sync.query_cpamp_snapshots_batch",
            AsyncMock(return_value=[_query_item(replacement)]),
        ),
    ):
        assert await collect_cpamp_channel(channel) is True

    visible = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"]
    assert len(visible) == 1
    assert visible[0]["public_id"] != first_cached["public_id"]
    assert visible[0]["windows"] == []
    assert visible[0]["success"] is False


@pytest.mark.asyncio
async def test_cpamp_discovery_failure_header_fallback_keeps_subject_public_id(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = parse_cpamp_auth_files(
        _subject_payload("account-subject-a", email="person@example.test")
    )[0]
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[account]),
        ),
        patch(
            "app.quota_sync.query_cpamp_snapshots_batch",
            AsyncMock(return_value=[_query_item(account)]),
        ),
    ):
        assert await collect_cpamp_channel(channel) is True
    original = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"][0]

    observed_ms = int(datetime.now(UTC).timestamp() * 1000)
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(side_effect=RuntimeError("private-discovery-error")),
        ),
        patch(
            "app.quota_sync.fetch_cpamp_header_snapshots",
            AsyncMock(
                return_value=[
                    {
                        "timestamp_ms": observed_ms,
                        "auth_file_snapshot": account.auth_file_name,
                        "auth_index": account.auth_index,
                        "account_snapshot": "person@example.test",
                        "response_metadata": {
                            "quota": {"primary": {"used_percent": 30}}
                        },
                    }
                ]
            ),
        ),
    ):
        assert await collect_cpamp_channel(channel) is True

    refreshed = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"]
    assert len(refreshed) == 1
    assert refreshed[0]["public_id"] == original["public_id"]
    assert refreshed[0]["windows"][0]["remaining"] == 70.0


@pytest.mark.asyncio
async def test_cpamp_protocol_discovers_and_queries_read_only_snapshots(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="management-secret",
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers["authorization"] == "Bearer management-secret"
        if request.method == "GET":
            assert request.url.path == "/v0/management/auth-files"
            return httpx.Response(
                200,
                json={
                    "files": [
                        {
                            "provider": "codex",
                            "auth_index": "auth-1",
                            "name": "account-1.json",
                            "email": "person@example.test",
                            "id_token": {"plan_type": "plus"},
                        }
                    ]
                },
            )
        assert request.method == "POST"
        assert request.url.path == "/v0/management/quota-snapshots/query"
        body = request.read().decode("utf-8")
        assert "auth-1" in body
        assert "account-1.json" in body
        return httpx.Response(
            200,
                json={
                    "generated_at_ms": 1,
                    "items": [_query_item(_account(0))],
                },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        accounts = await discover_cpamp_accounts(channel, client)
        items = await query_cpamp_snapshots_batch(channel, accounts, client)

    assert len(seen) == 2
    assert accounts[0].account_display == "p***@example.test"
    assert accounts[0].account_key_hash.startswith("hmac:v1:")
    snapshots = parse_cpamp_query_items(items, accounts)
    assert snapshots[0].plan == "Pro 20x"
    assert snapshots[0].windows[0]["remaining"] == 75.0


@pytest.mark.asyncio
async def test_cpamp_auth_files_protocol_flows_through_collector_and_storage(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="management-secret",
    )
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = _auth_files_payload(
        observed_at=now_iso,
        signals=_signals_dict(primary_used="37"),
    )
    seen: list[tuple[str, str]] = []
    real_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        assert request.headers["authorization"] == "Bearer management-secret"
        if request.method == "GET" and request.url.path.endswith(
            "/v0/management/auth-files"
        ):
            return httpx.Response(200, json=payload)
        raise AssertionError(f"unexpected CPAMP request: {request.method} {request.url}")

    class MockUpstreamClient:
        def __init__(self, **kwargs):
            options = dict(kwargs)
            options["transport"] = httpx.MockTransport(handler)
            self._client = real_async_client(**options)

        async def __aenter__(self):
            return await self._client.__aenter__()

        async def __aexit__(self, *args):
            return await self._client.__aexit__(*args)

    with patch("app.quota_sync.httpx.AsyncClient", MockUpstreamClient):
        assert await collect_cpamp_channel(channel) is True

    assert seen == [("GET", "/v0/management/auth-files")]
    cached = db.list_cached_cpa_channels(
        enabled_only=False, include_credential_details=True
    )[0]
    account = cached["accounts"][0]
    assert cached["snapshot_source"] == "auth_files"
    assert account["quota_source"] == "auth_files"
    assert account["account"] == "p***@example.test"
    assert account["auth_file_masked"]
    assert account["windows"][0]["used"] == 37.0
    assert "auth-1" not in str(account)


@pytest.mark.asyncio
async def test_cpamp_query_404_falls_back_to_header_endpoint(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="management-secret",
    )
    account = _account()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("quota-snapshots/query"):
            return httpx.Response(404, json={"error": "not found"})
        assert request.method == "GET"
        assert request.url.path == "/v0/management/monitoring/header-snapshots"
        assert dict(request.url.params) == {"days": "30", "limit": "5000"}
        return httpx.Response(200, json={"items": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CPAMPQueryUnsupported):
            await query_cpamp_snapshots_batch(channel, [account], client)
        assert await fetch_cpamp_header_snapshots(channel, client) == []


def test_cpamp_header_fallback_builds_ephemeral_identity_and_windows(temp_data_dir):
    observed_ms = int(datetime(2026, 8, 15, 1, 0, tzinfo=UTC).timestamp() * 1000)
    raw_auth_index = "auth-index-must-not-persist"
    snapshots = parse_cpamp_header_items(
        [
            {
                "timestamp_ms": observed_ms,
                "auth_file_snapshot": "account.json",
                "auth_index": raw_auth_index,
                "account_snapshot": "person@example.test",
                "header_quota_plan_type": "prolite",
                "response_metadata": {
                    "quota": {
                        "primary": {
                            "used_percent": 20,
                            "reset_after_seconds": 1800,
                            "window_minutes": 300,
                        }
                    }
                },
            }
        ]
    )
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.account.account_display == "p***@example.test"
    assert snapshot.account.account_key_hash.startswith("hmac:v1:")
    assert raw_auth_index not in snapshot.account.account_key_hash
    assert snapshot.plan == "Pro 5x"
    assert snapshot.windows[0]["remaining"] == 80.0


def test_cpamp_header_fallback_marks_fully_expired_quota_stale(temp_data_dir):
    now = datetime.now(UTC)
    observed_ms = int((now - timedelta(hours=1)).timestamp() * 1000)
    expired_reset_ms = int((now - timedelta(minutes=1)).timestamp() * 1000)
    active_reset_ms = int((now + timedelta(minutes=30)).timestamp() * 1000)

    def parse(reset_at_ms: int):
        return parse_cpamp_header_items(
            [
                {
                    "timestamp_ms": observed_ms,
                    "auth_file_snapshot": "account.json",
                    "auth_index": "auth-1",
                    "account_snapshot": "person@example.test",
                    "response_metadata": {
                        "quota": {
                            "primary": {
                                "used_percent": 20,
                                "reset_at_ms": reset_at_ms,
                                "window_minutes": 300,
                            }
                        }
                    },
                }
            ]
        )[0]

    assert parse(expired_reset_ms).stale is True
    assert parse(active_reset_ms).stale is False


def test_cpamp_header_fallback_marks_old_snapshot_without_reset_stale(temp_data_dir):
    now = datetime.now(UTC)

    def parse(observed: datetime):
        return parse_cpamp_header_items(
            [
                {
                    "timestamp_ms": int(observed.timestamp() * 1000),
                    "auth_file_snapshot": "account.json",
                    "auth_index": "auth-1",
                    "account_snapshot": "person@example.test",
                    "response_metadata": {
                        "quota": {"primary": {"used_percent": 20}}
                    },
                }
            ]
        )[0]

    assert parse(now - timedelta(hours=7)).stale is True
    assert parse(now - timedelta(hours=1)).stale is False


@pytest.mark.asyncio
async def test_cpamp_collector_isolates_failed_batches(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    accounts = [_account(index) for index in range(201)]
    query = AsyncMock(
        side_effect=[
            RuntimeError("first-batch-secret"),
            [_query_item(accounts[-1], used=10)],
        ]
    )
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=accounts),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", query),
    ):
        assert await collect_cpamp_channel(channel) is True

    assert query.await_count == 2
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["success"] is True
    by_account = {item["account"]: item for item in cached["accounts"]}
    assert by_account[accounts[-1].account_display]["success"] is True
    assert by_account[accounts[0].account_display]["success"] is False
    assert b"first-batch-secret" not in db.db_path().read_bytes()


@pytest.mark.asyncio
async def test_cpamp_channel_is_stale_when_all_source_windows_are_stale(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = _account()
    item = _query_item(account)
    item["windows"][0]["stale"] = True
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[account]),
        ),
        patch(
            "app.quota_sync.query_cpamp_snapshots_batch",
            AsyncMock(return_value=[item]),
        ),
    ):
        assert await collect_cpamp_channel(channel) is True

    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["success"] is True
    assert cached["stale"] is True
    assert cached["accounts"][0]["stale"] is True


@pytest.mark.asyncio
async def test_cpamp_empty_query_keeps_discovered_old_snapshot_visible_and_stale(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = _account()
    db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at="2026-08-15T01:00:00Z",
    )
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[account]),
        ),
        patch(
            "app.quota_sync.query_cpamp_snapshots_batch",
            AsyncMock(return_value=[]),
        ),
    ):
        assert await collect_cpamp_channel(channel) is True

    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["stale"] is True
    assert len(cached["accounts"]) == 1
    assert cached["accounts"][0]["stale"] is True
    assert cached["accounts"][0]["windows"][0]["remaining"] == 80


@pytest.mark.asyncio
async def test_cpamp_successful_empty_discovery_does_not_restore_historical_headers(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = _account()
    db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at="2026-08-15T01:00:00Z",
    )
    header = AsyncMock(return_value=[])
    query = AsyncMock()
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[]),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", query),
        patch("app.quota_sync.fetch_cpamp_header_snapshots", header),
    ):
        assert await collect_cpamp_channel(channel) is True

    query.assert_not_awaited()
    header.assert_not_awaited()
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["accounts"] == []


@pytest.mark.asyncio
async def test_cpamp_discovery_failure_and_empty_headers_preserve_stale_snapshot(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = _account()
    db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at="2026-08-15T01:00:00Z",
    )
    db.record_cpamp_channel_attempt(channel.id, success=True)
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(side_effect=RuntimeError("private-discovery-error")),
        ),
        patch(
            "app.quota_sync.fetch_cpamp_header_snapshots",
            AsyncMock(return_value=[]),
        ),
    ):
        assert await collect_cpamp_channel(channel) is False

    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["success"] is False
    assert cached["stale"] is True
    assert len(cached["accounts"]) == 1
    assert cached["accounts"][0]["stale"] is True
    assert cached["accounts"][0]["windows"][0]["remaining"] == 80
    assert b"private-discovery-error" not in db.db_path().read_bytes()


@pytest.mark.asyncio
async def test_cpamp_header_fallback_keeps_successful_query_batch_visible(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    accounts = [_account(index) for index in range(201)]
    header_observed_ms = int(datetime.now(UTC).timestamp() * 1000)
    query = AsyncMock(
        side_effect=[
            [_query_item(accounts[0], used=10)],
            CPAMPQueryUnsupported("query unavailable"),
        ]
    )
    header = AsyncMock(
        return_value=[
            {
                "timestamp_ms": header_observed_ms,
                "auth_file_snapshot": accounts[-1].auth_file_name,
                "auth_index": accounts[-1].auth_index,
                "response_metadata": {
                    "quota": {
                        "primary": {
                            "used_percent": 30,
                            "reset_after_seconds": 1800,
                            "window_minutes": 300,
                        }
                    }
                },
            },
            {
                "timestamp_ms": header_observed_ms,
                "auth_file_snapshot": "retired-account.json",
                "auth_index": "retired-auth-index",
                "account_snapshot": "retired@example.test",
                "response_metadata": {
                    "quota": {
                        "primary": {
                            "used_percent": 5,
                            "reset_after_seconds": 1800,
                            "window_minutes": 300,
                        }
                    }
                },
            },
        ]
    )
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=accounts),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", query),
        patch("app.quota_sync.fetch_cpamp_header_snapshots", header),
    ):
        assert await collect_cpamp_channel(channel) is True

    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    visible = {item["account"]: item for item in cached["accounts"]}
    assert len(cached["accounts"]) == len(accounts)
    assert visible[accounts[0].account_display]["success"] is True
    assert visible[accounts[-1].account_display]["success"] is True
    assert "r***@example.test" not in visible


@pytest.mark.asyncio
async def test_cpamp_authentication_failure_stops_channel_and_marks_stale(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = _account()
    db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[],
        observed_at="2026-08-15T01:00:00Z",
    )
    db.record_cpamp_channel_attempt(channel.id, success=True)
    with patch(
        "app.quota_sync.discover_cpamp_accounts",
        AsyncMock(side_effect=CPAMPAuthenticationError("bad key")),
    ):
        assert await collect_cpamp_channel(channel) is False

    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["success"] is False
    assert cached["stale"] is True
    assert cached["accounts"][0]["stale"] is True
    assert "bad key" not in db.db_path().read_text("utf-8", errors="ignore")


@pytest.mark.asyncio
async def test_cpamp_collection_logs_unified_cpa_source(temp_data_dir, caplog):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    caplog.set_level(logging.INFO, logger="quotahub.quota_sync")
    with patch(
        "app.quota_sync.discover_cpamp_accounts", AsyncMock(return_value=[])
    ):
        assert await collect_cpamp_channel(channel) is True

    completed = next(
        record
        for record in caplog.records
        if getattr(record, "event", "") == "cpamp_channel_collection_completed"
    )
    assert completed.event_fields["provider"] == "cpa"
    assert completed.event_fields["quota_source"] == "cpamp_snapshot"


def _signals_dict(
    *,
    plan_type: str | None = "pro",
    primary_used: str = "25",
    primary_minutes: str = "300",
    primary_reset_after: str = "1800",
) -> dict[str, str]:
    signals: dict[str, str] = {
        "X-Codex-Primary-Used-Percent": primary_used,
        "X-Codex-Primary-Window-Minutes": primary_minutes,
        "X-Codex-Primary-Reset-After-Seconds": primary_reset_after,
    }
    if plan_type is not None:
        signals["X-Codex-Plan-Type"] = plan_type
    return signals


def _auth_files_payload(
    *,
    auth_index: str = "auth-1",
    name: str = "account-1.json",
    email: str = "person@example.test",
    observed_at: str = "2026-08-15T01:00:00Z",
    signals: dict[str, str] | None = None,
    id_token_plan: str = "plus",
) -> dict[str, object]:
    entry: dict[str, object] = {
        "provider": "codex",
        "auth_index": auth_index,
        "name": name,
        "email": email,
        "id_token": {"plan_type": id_token_plan},
    }
    if signals is not None:
        entry["quota"] = {"observed_at": observed_at, "signals": signals}
    return {"files": [entry]}


def test_cpamp_parse_auth_files_marks_plan_from_signals_and_observed_at(
    temp_data_dir,
):
    account = parse_cpamp_auth_files(
        _auth_files_payload(
            observed_at="2026-08-15T01:00:00Z",
            signals=_signals_dict(plan_type="pro"),
        )
    )[0]
    assert account.plan_from_signals is True
    assert account.plan_observed_at == "2026-08-15T01:00:00Z"
    assert account.plan == "Pro 20x"


def test_cpamp_parse_auth_files_without_signal_plan_keeps_weak_plan(temp_data_dir):
    account = parse_cpamp_auth_files(
        _auth_files_payload(
            observed_at="2026-08-15T01:00:00Z",
            signals=_signals_dict(plan_type=None),
        )
    )[0]
    assert account.plan_from_signals is False
    assert account.plan_observed_at is None
    assert account.plan == "Plus"


def test_cpamp_signal_snapshot_marks_old_observation_stale(temp_data_dir):
    old = (
        datetime.now(UTC) - timedelta(hours=7)
    ).isoformat().replace("+00:00", "Z")
    account = parse_cpamp_auth_files(
        _auth_files_payload(observed_at=old, signals=_signals_dict())
    )[0]
    snapshot = parse_cpamp_signal_snapshot(account)
    assert snapshot.source == "auth_files"
    assert snapshot.stale is True
    assert snapshot.windows[0]["used"] == 25.0


def test_cpamp_signal_snapshot_fresh_observation_not_stale(temp_data_dir):
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    account = parse_cpamp_auth_files(
        _auth_files_payload(observed_at=now_iso, signals=_signals_dict())
    )[0]
    snapshot = parse_cpamp_signal_snapshot(account)
    assert snapshot.stale is False


def test_cpamp_signal_snapshot_rejects_incomplete_or_invalid_observation(
    temp_data_dir,
):
    account = parse_cpamp_auth_files(
        _auth_files_payload(
            observed_at="not-a-timestamp",
            signals={"X-Codex-Plan-Type": "pro"},
        )
    )[0]
    with pytest.raises(CPAMPError):
        parse_cpamp_signal_snapshot(account)


@pytest.mark.asyncio
async def test_cpamp_incomplete_auth_files_signals_fall_back_to_query(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    account = parse_cpamp_auth_files(
        _auth_files_payload(
            observed_at=now_iso,
            signals={"X-Codex-Plan-Type": "pro"},
        )
    )[0]
    query = AsyncMock(return_value=[_query_item(account, used=55)])
    header = AsyncMock(return_value=[])
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[account]),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", query),
        patch("app.quota_sync.fetch_cpamp_header_snapshots", header),
    ):
        assert await collect_cpamp_channel(channel) is True

    query.assert_awaited_once()
    header.assert_not_awaited()
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["accounts"][0]["quota_source"] == "quota_snapshots"
    assert cached["accounts"][0]["windows"][0]["used"] == 55.0


@pytest.mark.asyncio
async def test_cpamp_signal_main_path_writes_auth_files_without_query(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    account = parse_cpamp_auth_files(
        _auth_files_payload(observed_at=now_iso, signals=_signals_dict())
    )[0]
    query = AsyncMock(return_value=[])
    header = AsyncMock(return_value=[])
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[account]),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", query),
        patch("app.quota_sync.fetch_cpamp_header_snapshots", header),
    ):
        assert await collect_cpamp_channel(channel) is True

    query.assert_not_awaited()
    header.assert_not_awaited()
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["success"] is True
    assert cached["snapshot_source"] == "auth_files"
    assert cached["accounts"][0]["success"] is True
    assert cached["accounts"][0]["quota_source"] == "auth_files"
    assert cached["accounts"][0]["plan"] == "Pro 20x"
    assert cached["accounts"][0]["windows"][0]["used"] == 25.0
    assert b"auth-1" not in db.db_path().read_bytes()


@pytest.mark.asyncio
async def test_cpamp_mixed_accounts_split_between_auth_files_and_query(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    signal_account = parse_cpamp_auth_files(
        _auth_files_payload(
            auth_index="auth-sig",
            name="sig.json",
            email="sig@example.test",
            observed_at=now_iso,
            signals=_signals_dict(),
        )
    )[0]
    fallback_account = parse_cpamp_auth_files(
        _auth_files_payload(
            auth_index="auth-fb",
            name="fb.json",
            email="fb@example.test",
            signals=None,
        )
    )[0]
    query = AsyncMock(return_value=[_query_item(fallback_account, used=40)])
    header = AsyncMock(return_value=[])
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[signal_account, fallback_account]),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", query),
        patch("app.quota_sync.fetch_cpamp_header_snapshots", header),
    ):
        assert await collect_cpamp_channel(channel) is True

    query.assert_awaited_once()
    header.assert_not_awaited()
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    by_account = {item["account"]: item for item in cached["accounts"]}
    assert by_account[signal_account.account_display]["quota_source"] == "auth_files"
    assert by_account[signal_account.account_display]["windows"][0]["used"] == 25.0
    assert (
        by_account[fallback_account.account_display]["quota_source"]
        == "quota_snapshots"
    )
    assert by_account[fallback_account.account_display]["windows"][0]["used"] == 40.0
    assert cached["snapshot_source"] == "auth_files"


@pytest.mark.asyncio
async def test_cpamp_all_fallback_query_404_falls_back_to_headers(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account = parse_cpamp_auth_files(
        _auth_files_payload(
            auth_index="auth-1",
            name="account-1.json",
            email="person@example.test",
            signals=None,
        )
    )[0]
    query = AsyncMock(side_effect=CPAMPQueryUnsupported("query unavailable"))
    header = AsyncMock(
        return_value=[
            {
                "timestamp_ms": int(datetime.now(UTC).timestamp() * 1000),
                "auth_file_snapshot": account.auth_file_name,
                "auth_index": account.auth_index,
                "account_snapshot": "person@example.test",
                "response_metadata": {
                    "quota": {
                        "primary": {
                            "used_percent": 30,
                            "reset_after_seconds": 1800,
                            "window_minutes": 300,
                        }
                    }
                },
            }
        ]
    )
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[account]),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", query),
        patch("app.quota_sync.fetch_cpamp_header_snapshots", header),
    ):
        assert await collect_cpamp_channel(channel) is True

    query.assert_awaited_once()
    header.assert_awaited_once()
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["success"] is True
    assert cached["snapshot_source"] == "header_snapshots"
    assert cached["accounts"][0]["quota_source"] == "header_snapshots"
    assert cached["accounts"][0]["windows"][0]["used"] == 30.0


@pytest.mark.asyncio
async def test_cpamp_signal_old_observation_marks_snapshot_stale(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    old = (
        datetime.now(UTC) - timedelta(hours=7)
    ).isoformat().replace("+00:00", "Z")
    account = parse_cpamp_auth_files(
        _auth_files_payload(observed_at=old, signals=_signals_dict())
    )[0]
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[account]),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", AsyncMock(return_value=[])),
        patch(
            "app.quota_sync.fetch_cpamp_header_snapshots", AsyncMock(return_value=[])
        ),
    ):
        assert await collect_cpamp_channel(channel) is True
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["accounts"][0]["stale"] is True
    assert cached["accounts"][0]["quota_source"] == "auth_files"
    assert cached["accounts"][0]["windows"][0]["used"] == 25.0


@pytest.mark.asyncio
async def test_cpamp_signal_parse_failure_isolates_account(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    good = parse_cpamp_auth_files(
        _auth_files_payload(
            auth_index="auth-good",
            name="good.json",
            email="good@example.test",
            observed_at=now_iso,
            signals=_signals_dict(),
        )
    )[0]
    bad = parse_cpamp_auth_files(
        _auth_files_payload(
            auth_index="auth-bad",
            name="bad.json",
            email="bad@example.test",
            observed_at=now_iso,
            signals=_signals_dict(),
        )
    )[0]
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[good, bad]),
        ),
        patch(
            "app.quota_sync.parse_cpamp_signal_snapshot",
            side_effect=[parse_cpamp_signal_snapshot(good), RuntimeError("parse-bang")],
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", AsyncMock(return_value=[])),
        patch(
            "app.quota_sync.fetch_cpamp_header_snapshots", AsyncMock(return_value=[])
        ),
    ):
        assert await collect_cpamp_channel(channel) is True
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    by_account = {item["account"]: item for item in cached["accounts"]}
    assert by_account[good.account_display]["success"] is True
    assert by_account[good.account_display]["quota_source"] == "auth_files"
    assert by_account[bad.account_display]["success"] is False
    assert b"parse-bang" not in db.db_path().read_bytes()


@pytest.mark.asyncio
async def test_cpamp_discovery_failure_rediscovery_preserves_strong_plan(
    temp_data_dir,
):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    now = datetime.now(UTC)
    t1 = (now - timedelta(seconds=10)).isoformat(timespec="microseconds").replace("+00:00", "Z")
    signal_account = parse_cpamp_auth_files(
        _auth_files_payload(
            auth_index="auth-1",
            name="account-1.json",
            email="person@example.test",
            observed_at=t1,
            signals=_signals_dict(plan_type="pro"),
        )
    )[0]
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(return_value=[signal_account]),
        ),
        patch("app.quota_sync.query_cpamp_snapshots_batch", AsyncMock(return_value=[])),
        patch(
            "app.quota_sync.fetch_cpamp_header_snapshots", AsyncMock(return_value=[])
        ),
    ):
        assert await collect_cpamp_channel(channel) is True
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["accounts"][0]["plan"] == "Pro 20x"
    assert cached["accounts"][0]["quota_source"] == "auth_files"

    # Discovery fails; the stored-account fallback drives rediscovery. The
    # header carries no plan_type, so the stored strong plan is what surfaces.
    header_observed_ms = int(now.timestamp() * 1000)
    with (
        patch(
            "app.quota_sync.discover_cpamp_accounts",
            AsyncMock(side_effect=RuntimeError("private-discovery-error")),
        ),
        patch(
            "app.quota_sync.fetch_cpamp_header_snapshots",
            AsyncMock(
                return_value=[
                    {
                        "timestamp_ms": header_observed_ms,
                        "auth_file_snapshot": signal_account.auth_file_name,
                        "auth_index": signal_account.auth_index,
                        "account_snapshot": "person@example.test",
                        "response_metadata": {
                            "quota": {
                                "primary": {
                                    "used_percent": 30,
                                    "reset_after_seconds": 1800,
                                    "window_minutes": 300,
                                }
                            }
                        },
                    }
                ]
            ),
        ),
    ):
        assert await collect_cpamp_channel(channel) is True

    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]
    assert cached["accounts"][0]["plan"] == "Pro 20x"
    assert cached["accounts"][0]["quota_source"] == "header_snapshots"
    assert b"private-discovery-error" not in db.db_path().read_bytes()


def test_cpamp_parse_passes_through_masked_credential_fields(temp_data_dir):
    raw_name = "codex-account-sensitive.json"
    raw_project_id = "proj-secret-1234567890"
    accounts = parse_cpamp_auth_files(
        {
            "files": [
                {
                    "provider": "codex",
                    "auth_index": "auth-index-sensitive",
                    "name": raw_name,
                    "email": "alice@example.com",
                    "project_id": raw_project_id,
                    "account_type": "pro",
                }
            ]
        }
    )
    assert len(accounts) == 1
    account = accounts[0]
    assert account.auth_file_masked == mask_auth_file_name(raw_name)
    assert account.auth_tag.startswith("#")
    assert len(account.auth_tag) == 7
    assert account.provider == "codex"
    assert account.project_id_masked == "pr***90"
    # Raw identity values must not appear in the masked fields.
    assert raw_name not in account.auth_file_masked
    assert raw_project_id not in account.project_id_masked


def test_cpamp_header_fallback_derives_auth_file_masked_and_tag(temp_data_dir):
    observed_ms = int(datetime(2026, 8, 15, 1, 0, tzinfo=UTC).timestamp() * 1000)
    raw_auth_file = "ephemeral-account.json"
    raw_auth_index = "header-auth-index-sensitive"
    snapshots = parse_cpamp_header_items(
        [
            {
                "timestamp_ms": observed_ms,
                "auth_file_snapshot": raw_auth_file,
                "auth_index": raw_auth_index,
                "account_snapshot": "person@example.test",
                "response_metadata": {
                    "quota": {"primary": {"used_percent": 20}}
                },
            }
        ]
    )
    assert len(snapshots) == 1
    account = snapshots[0].account
    # Header fallback can derive the masked file name and an auth tag from the
    # header identity; provider and project_id_masked stay at their defaults.
    assert account.auth_file_masked == mask_auth_file_name(raw_auth_file)
    assert account.auth_tag.startswith("#")
    assert len(account.auth_tag) == 7
    assert account.provider == "unknown"
    assert account.project_id_masked == ""
    # Raw identity values must not leak into the masked fields.
    assert raw_auth_file not in account.auth_file_masked
    assert raw_auth_index not in account.auth_tag
