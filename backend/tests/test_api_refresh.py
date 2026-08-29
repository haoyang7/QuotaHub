from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app import db
from app.cpa_queue import CPA_QUEUE_LEASE_NAME
from app.main import app
from app.quota_sync import QUOTA_LEASE_NAME

ADMIN_TOKEN = "test-admin-token-with-at-least-32-characters"


def _admin_client() -> TestClient:
    client = TestClient(app)
    login = client.post("/api/admin/auth/login", json={"token": ADMIN_TOKEN})
    assert login.status_code == 200
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    return client


def _hold_lease(name: str) -> None:
    """Pre-acquire a scheduler lease so endpoint SchedulerLease.acquire() fails."""
    assert db.acquire_scheduler_lease(name, "background-fake-owner", ttl_sec=120)


def _window() -> dict[str, object]:
    return {
        "label": "5h Rolling",
        "used": 1.0,
        "remaining": 9.0,
        "total": 10.0,
        "unit": "%",
        "reset_at": "",
        "reset_in_sec": 0,
    }


# ---------------------------------------------------------------------------
# OpenCode refresh
# ---------------------------------------------------------------------------


def test_opencode_refresh_returns_409_when_quota_lease_held(temp_data_dir):
    client = _admin_client()
    account = db.create_opencode_account(
        name="OC", workspace_id="Default", auth_cookie="auth=t"
    )
    _hold_lease(QUOTA_LEASE_NAME)
    collect = AsyncMock()
    with patch("app.main.collect_opencode_account", collect):
        response = client.post(
            f"/api/admin/accounts/opencode/{account.id}/refresh"
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "额度采集正在进行，请稍后"
    collect.assert_not_called()


def test_opencode_refresh_writes_snapshot_and_returns_it(temp_data_dir):
    client = _admin_client()
    account = db.create_opencode_account(
        name="OC", workspace_id="Default", auth_cookie="auth=t"
    )

    async def fake_collect(row, **_kwargs):
        db.record_opencode_quota_snapshot(row.id, success=True, windows=[_window()])
        return True

    with patch(
        "app.main.collect_opencode_account", AsyncMock(side_effect=fake_collect)
    ):
        response = client.post(
            f"/api/admin/accounts/opencode/{account.id}/refresh"
        )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["windows"] == [_window()]
    # The response must be the freshly written cached snapshot.
    cached = db.get_cached_opencode_quota(account.id)
    assert cached is not None
    assert body["windows"] == cached["windows"]
    assert body["updated_at"] == cached["updated_at"]


def test_opencode_refresh_returns_502_when_collection_fails_with_cached_snapshot(
    temp_data_dir,
):
    client = _admin_client()
    account = db.create_opencode_account(
        name="OC", workspace_id="Default", auth_cookie="auth=t"
    )
    db.record_opencode_quota_snapshot(account.id, success=True, windows=[_window()])

    with patch(
        "app.main.collect_opencode_account", AsyncMock(return_value=False)
    ) as collect:
        response = client.post(
            f"/api/admin/accounts/opencode/{account.id}/refresh"
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "额度采集失败"
    collect.assert_awaited_once()
    assert db.get_cached_opencode_quota(account.id)["success"] is True


def test_opencode_refresh_404_when_account_missing(temp_data_dir):
    client = _admin_client()
    response = client.post(
        "/api/admin/accounts/opencode/does-not-exist/refresh"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "账号不存在"


def test_opencode_refresh_requires_csrf(temp_data_dir):
    client = _admin_client()
    account = db.create_opencode_account(
        name="OC", workspace_id="Default", auth_cookie="auth=t"
    )
    # Strip the CSRF header to confirm the route is CSRF-guarded.
    csrf = client.headers.pop("X-CSRF-Token")
    response = client.post(
        f"/api/admin/accounts/opencode/{account.id}/refresh"
    )
    assert response.status_code == 403
    client.headers["X-CSRF-Token"] = csrf


# ---------------------------------------------------------------------------
# Ollama refresh
# ---------------------------------------------------------------------------


def test_ollama_refresh_returns_409_when_quota_lease_held(temp_data_dir):
    client = _admin_client()
    account = db.create_ollama_account(name="Ollama", session_cookie="sess=t")
    _hold_lease(QUOTA_LEASE_NAME)
    collect = AsyncMock()
    with patch("app.main.collect_ollama_account", collect):
        response = client.post(
            f"/api/admin/accounts/ollama/{account.id}/refresh"
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "额度采集正在进行，请稍后"
    collect.assert_not_called()


def test_ollama_refresh_writes_snapshot_and_returns_it(temp_data_dir):
    client = _admin_client()
    account = db.create_ollama_account(name="Ollama", session_cookie="sess=t")

    async def fake_collect(row, **_kwargs):
        db.record_ollama_quota_snapshot(
            row.id, success=True, plan="Plus", windows=[_window()]
        )
        return True

    with patch(
        "app.main.collect_ollama_account", AsyncMock(side_effect=fake_collect)
    ):
        response = client.post(
            f"/api/admin/accounts/ollama/{account.id}/refresh"
        )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["plan"] == "Plus"
    cached = db.get_cached_ollama_quota(account.id)
    assert cached is not None
    assert body["windows"] == cached["windows"]


def test_ollama_refresh_returns_502_when_collection_fails_with_cached_snapshot(
    temp_data_dir,
):
    client = _admin_client()
    account = db.create_ollama_account(name="Ollama", session_cookie="sess=t")
    db.record_ollama_quota_snapshot(
        account.id, success=True, plan="Plus", windows=[_window()]
    )

    with patch(
        "app.main.collect_ollama_account", AsyncMock(return_value=False)
    ) as collect:
        response = client.post(
            f"/api/admin/accounts/ollama/{account.id}/refresh"
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "额度采集失败"
    collect.assert_awaited_once()
    assert db.get_cached_ollama_quota(account.id)["success"] is True


def test_ollama_refresh_404_when_account_missing(temp_data_dir):
    client = _admin_client()
    response = client.post(
        "/api/admin/accounts/ollama/does-not-exist/refresh"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "账号不存在"


# ---------------------------------------------------------------------------
# CPA channel refresh
# ---------------------------------------------------------------------------


def _write_cpa_snapshot(
    channel_id: str, account_hash: str, display: str, plan: str, observed_at: str
) -> None:
    db.record_cpa_quota_snapshot(
        channel_id,
        account_hash,
        account_display=display,
        plan=plan,
        success=True,
        windows=[_window()],
        quota_source="usage_queue",
        observed_at=observed_at,
    )


def test_cpa_refresh_404_when_channel_missing(temp_data_dir):
    client = _admin_client()
    response = client.post("/api/admin/cpa/channels/does-not-exist/refresh")
    assert response.status_code == 404
    assert response.json()["detail"] == "CPA 渠道不存在"


def test_cpa_native_queue_refresh_rejected_without_exclusive_confirmation(
    temp_data_dir,
):
    client = _admin_client()
    # Create a disabled native_queue channel so exclusive confirmation is absent.
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=False,
        enabled=False,
    )
    assert channel.exclusive_confirmed_at is None
    collect = AsyncMock()
    with patch("app.main.collect_cpa_channel", collect):
        response = client.post(
            f"/api/admin/cpa/channels/{channel.id}/refresh"
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "未确认独占消费，无法刷新"
    # No queue pop / collection may happen.
    collect.assert_not_called()


def test_cpa_native_queue_refresh_409_when_queue_lease_held(temp_data_dir):
    client = _admin_client()
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    assert channel.exclusive_confirmed_at is not None
    _hold_lease(CPA_QUEUE_LEASE_NAME)
    collect = AsyncMock()
    with patch("app.main.collect_cpa_channel", collect):
        response = client.post(
            f"/api/admin/cpa/channels/{channel.id}/refresh"
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "额度采集正在进行，请稍后"
    collect.assert_not_called()


def test_cpa_native_queue_refresh_runs_collect_and_returns_channel(temp_data_dir):
    client = _admin_client()
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    observed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    async def fake_collect(channel_row, **_kwargs):
        _write_cpa_snapshot(
            channel_row.id,
            "hmac:v1:acct-native",
            "a***@example.com",
            "Plus",
            observed_at,
        )
        return True

    with patch("app.main.collect_cpa_channel", AsyncMock(side_effect=fake_collect)):
        response = client.post(
            f"/api/admin/cpa/channels/{channel.id}/refresh"
        )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == channel.id
    assert body["quota_source"] == "native_queue"
    assert body["accounts"][0]["plan"] == "Plus"
    assert body["accounts"][0]["observed_at"] == observed_at


def test_cpa_cpamp_snapshot_refresh_uses_quota_lease_and_collect_cpamp(
    temp_data_dir,
):
    client = _admin_client()
    channel = db.create_cpa_channel(
        name="CPAMP",
        cpamp_base_url="https://cpamp.example.com",
        cpamp_management_key="cpamp-secret",
        quota_source="cpamp_snapshot",
    )
    observed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    async def fake_collect(channel_row, **_kwargs):
        _write_cpa_snapshot(
            channel_row.id,
            "hmac:v1:acct-cpamp",
            "b***@example.com",
            "Pro",
            observed_at,
        )
        return True

    with patch(
        "app.main.collect_cpamp_channel", AsyncMock(side_effect=fake_collect)
    ):
        response = client.post(
            f"/api/admin/cpa/channels/{channel.id}/refresh"
        )
    assert response.status_code == 200
    body = response.json()
    assert body["quota_source"] == "cpamp_snapshot"
    assert body["accounts"][0]["plan"] == "Pro"


def test_cpa_cpamp_snapshot_refresh_409_when_quota_lease_held(temp_data_dir):
    client = _admin_client()
    channel = db.create_cpa_channel(
        name="CPAMP",
        cpamp_base_url="https://cpamp.example.com",
        cpamp_management_key="cpamp-secret",
        quota_source="cpamp_snapshot",
    )
    _hold_lease(QUOTA_LEASE_NAME)
    collect = AsyncMock()
    with patch("app.main.collect_cpamp_channel", collect):
        response = client.post(
            f"/api/admin/cpa/channels/{channel.id}/refresh"
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "额度采集正在进行，请稍后"
    collect.assert_not_called()


def test_cpa_cpamp_snapshot_refresh_returns_error_when_collection_fails(
    temp_data_dir,
):
    client = _admin_client()
    channel = db.create_cpa_channel(
        name="CPAMP",
        cpamp_base_url="https://cpamp.example.com",
        cpamp_management_key="cpamp-secret",
        quota_source="cpamp_snapshot",
    )
    with patch(
        "app.main.collect_cpamp_channel", AsyncMock(return_value=False)
    ):
        response = client.post(
            f"/api/admin/cpa/channels/{channel.id}/refresh"
        )
    assert response.status_code == 502
    assert response.json()["detail"] == "额度采集失败"


def test_cpa_none_source_refresh_runs_collect_cpa_channel(temp_data_dir):
    client = _admin_client()
    channel = db.create_cpa_channel(
        name="DiscoveryOnly",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="none",
    )
    # For the "none" source no quota is collected; the mock just reports success
    # and the channel is returned with an empty account list.
    async def fake_collect(channel_row, **_kwargs):
        return True

    with patch("app.main.collect_cpa_channel", AsyncMock(side_effect=fake_collect)):
        response = client.post(
            f"/api/admin/cpa/channels/{channel.id}/refresh"
        )
    assert response.status_code == 200
    body = response.json()
    assert body["quota_source"] == "none"
    assert body["accounts"] == []


def test_cpa_refresh_requires_csrf(temp_data_dir):
    client = _admin_client()
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
    )
    csrf = client.headers.pop("X-CSRF-Token")
    response = client.post(f"/api/admin/cpa/channels/{channel.id}/refresh")
    assert response.status_code == 403
    client.headers["X-CSRF-Token"] = csrf


# ---------------------------------------------------------------------------
# Zero-upstream-on-read invariant
# ---------------------------------------------------------------------------


def test_public_read_endpoints_make_no_upstream_requests_after_refresh(
    temp_data_dir,
):
    client = _admin_client()
    account = db.create_opencode_account(
        name="OC", workspace_id="Default", auth_cookie="auth=t"
    )

    async def fake_collect(row, **_kwargs):
        db.record_opencode_quota_snapshot(row.id, success=True, windows=[_window()])
        return True

    with patch(
        "app.main.collect_opencode_account", AsyncMock(side_effect=fake_collect)
    ):
        refresh = client.post(
            f"/api/admin/accounts/opencode/{account.id}/refresh"
        )
    assert refresh.status_code == 200

    # The refresh POST may issue upstream requests, but public reads must stay
    # snapshot-only: any async upstream client instantiation on a read fails loud.
    with patch(
        "httpx.AsyncClient",
        side_effect=AssertionError("upstream request on read"),
    ):
        read = TestClient(app).get("/api/public/quota")
    assert read.status_code == 200
    assert read.json()["opencode"][0]["success"] is True


# ---------------------------------------------------------------------------
# record_cpa_quota_batch plan arbitration (M4 legacy fix)
# ---------------------------------------------------------------------------


def test_record_cpa_quota_batch_arbitrates_plan_by_observed_at(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account_hash = "hmac:v1:arbitration-account"
    display = "n***@example.test"
    base = datetime.now(UTC)
    t1 = base.isoformat().replace("+00:00", "Z")
    t2 = (base + timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
    t3 = (base + timedelta(seconds=20)).isoformat().replace("+00:00", "Z")

    endpoint_revision = channel.cpa_endpoint_revision

    # 1. Strong source writes "Pro 20x" at T1.
    db.record_cpa_quota_batch(
        channel.id,
        [
            {
                "account_key_hash": account_hash,
                "account_display": display,
                "plan": "Pro 20x",
                "windows": [],
                "plan_observed_at": t1,
                "observed_at": t1,
            }
        ],
        endpoint_revision=endpoint_revision,
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Pro 20x"

    # 2. Newer strong source writes "Plus" at T2 > T1 -> overrides plan.
    db.record_cpa_quota_batch(
        channel.id,
        [
            {
                "account_key_hash": account_hash,
                "account_display": display,
                "plan": "Plus",
                "windows": [],
                "plan_observed_at": t2,
                "observed_at": t2,
            }
        ],
        endpoint_revision=endpoint_revision,
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Plus"

    # 3. Even newer "未知套餐" at T3 > T2 must NOT downgrade the known plan.
    db.record_cpa_quota_batch(
        channel.id,
        [
            {
                "account_key_hash": account_hash,
                "account_display": display,
                "plan": "未知套餐",
                "windows": [],
                "observed_at": t3,
            }
        ],
        endpoint_revision=endpoint_revision,
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Plus"

    # plan_observed_at should reflect the Plus observation (T2), not T3.
    with db.get_conn() as conn:
        row = conn.execute(
            """
            SELECT plan, plan_observed_at FROM cpa_quota_snapshots
            WHERE channel_id = ? AND source_mode = 'native_queue'
            """,
            (channel.id,),
        ).fetchone()
    assert row["plan"] == "Plus"
    assert row["plan_observed_at"] == t2
    with db.get_conn() as conn:
        account_row = conn.execute(
            """
            SELECT plan, plan_observed_at FROM cpa_accounts
            WHERE channel_id = ? AND canonical_account_hash = ?
            """,
            (channel.id, account_hash),
        ).fetchone()
    assert account_row["plan"] == "Plus"
    assert account_row["plan_observed_at"] == t2

    # A later discovery-only weak plan must not replace the strong queue plan.
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=account_hash,
                legacy_account_key_hashes=(),
                locator_hash=account_hash,
                subject_hash="",
                account_display=display,
                plan="Free",
            )
        ],
        source_mode="native_queue",
    )
    with db.get_conn() as conn:
        account_row = conn.execute(
            """
            SELECT plan, plan_observed_at FROM cpa_accounts
            WHERE channel_id = ? AND canonical_account_hash = ?
            """,
            (channel.id, account_hash),
        ).fetchone()
    assert account_row["plan"] == "Plus"
    assert account_row["plan_observed_at"] == t2
