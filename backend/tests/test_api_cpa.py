from __future__ import annotations

from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.secrets import ENCRYPTED_PREFIX


ADMIN_TOKEN = "test-admin-token-with-at-least-32-characters"


def _admin_client() -> TestClient:
    client = TestClient(app)
    login = client.post("/api/admin/auth/login", json={"token": ADMIN_TOKEN})
    assert login.status_code == 200
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    return client


def test_cpa_channel_crud_encrypts_key_and_never_returns_it(temp_data_dir):
    client = _admin_client()
    created = client.post(
        "/api/admin/cpa/channels",
        json={
            "name": "Primary CPA",
            "cpa_endpoint": {
                "url": "https://proxy.example.com/",
                "management_key": "management-key-should-stay-server-side",
            },
            "cpamp_endpoint": {
                "url": "https://cpamp.example.com/",
                "admin_key": "cpamp-key-should-stay-server-side",
            },
            "interval_sec": 600,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    channel_id = payload["id"]
    assert payload["cpa_url"] == "https://proxy.example.com"
    assert payload["cpamp_url"] == "https://cpamp.example.com"
    assert payload["quota_source"] == "none"
    assert payload["enabled"] is True
    assert payload["interval_sec"] == 600
    assert "management_key" not in payload
    assert "configured" not in payload

    with db.get_conn() as conn:
        stored = conn.execute(
            "SELECT management_key, cpamp_management_key FROM cpa_channels WHERE id = ?",
            (channel_id,),
        ).fetchone()
    assert stored["management_key"].startswith(ENCRYPTED_PREFIX)
    assert stored["cpamp_management_key"].startswith(ENCRYPTED_PREFIX)
    assert "management-key-should-stay-server-side" not in stored["management_key"]
    assert "cpamp-key-should-stay-server-side" not in stored["cpamp_management_key"]

    updated = client.put(
        f"/api/admin/cpa/channels/{channel_id}",
        json={
            "cpa_endpoint": {"management_key": ""},
            "cpamp_endpoint": {"admin_key": ""},
            "enabled": False,
            "interval_sec": 900,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert db.get_cpa_channel(channel_id).management_key == "management-key-should-stay-server-side"

    anonymous = TestClient(app)
    assert anonymous.get("/api/admin/cpa/channels").status_code == 401
    assert anonymous.post(
        "/api/admin/cpa/channels",
        json={
            "name": "x",
            "cpa_endpoint": {"url": "https://x.example", "management_key": "x"},
        },
    ).status_code == 401

    deleted = client.delete(f"/api/admin/cpa/channels/{channel_id}")
    assert deleted.status_code == 200
    assert db.get_cpa_channel(channel_id) is None


def test_cpa_endpoint_removal_after_source_switch_clears_non_nullable_key(
    temp_data_dir,
):
    client = _admin_client()
    created = client.post(
        "/api/admin/cpa/channels",
        json={
            "name": "Migrated CPA",
            "cpa_endpoint": {
                "url": "https://proxy.example.com/",
                "management_key": "legacy-native-key",
            },
            "cpamp_endpoint": {
                "url": "https://cpamp.example.com/",
                "admin_key": "snapshot-key",
            },
        },
    )
    assert created.status_code == 200
    channel_id = created.json()["id"]

    switched = client.post(
        f"/api/admin/cpa/channels/{channel_id}/quota-source",
        json={"source": "cpamp_snapshot"},
    )
    assert switched.status_code == 200

    removed = client.put(
        f"/api/admin/cpa/channels/{channel_id}",
        json={"cpa_endpoint": None},
    )
    assert removed.status_code == 200
    assert removed.json()["cpa_url"] is None
    assert db.get_cpa_channel(channel_id).management_key == ""

    with db.get_conn() as conn:
        stored = conn.execute(
            "SELECT management_key FROM cpa_channels WHERE id = ?", (channel_id,)
        ).fetchone()
    assert stored["management_key"] == ""


def test_cpa_disabled_channel_hidden_publicly_and_delete_cascades_snapshots(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    db.record_cpa_quota_snapshot(
        channel.id,
        "account-hash",
        account_display="a***@example.com",
        plan="Plus",
        success=True,
        windows=[
            {
                "label": "5h Rolling",
                "used": 10,
                "remaining": 90,
                "total": 100,
                "unit": "%",
                "reset_at": "",
                "reset_in_sec": 0,
            }
        ],
    )
    db.record_cpa_channel_attempt(channel.id, success=True)

    public = TestClient(app).get("/api/public/quota")
    assert public.status_code == 200
    public_channel = public.json()["cpa_channels"][0]
    assert "id" not in public_channel
    assert "url" not in public_channel
    assert public_channel["accounts"][0]["account"] == "a***@example.com"
    assert "account_key_hash" not in public_channel["accounts"][0]

    db.update_cpa_channel(channel.id, enabled=False)
    assert TestClient(app).get("/api/public/quota").json()["cpa_channels"] == []
    assert len(db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]) == 1

    assert db.delete_cpa_channel(channel.id) is True
    with db.get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM cpa_quota_snapshots WHERE channel_id = ?",
            (channel.id,),
        ).fetchone()[0]
    assert count == 0


def test_cpa_write_requires_csrf(temp_data_dir):
    client = TestClient(app)
    login = client.post("/api/admin/auth/login", json={"token": ADMIN_TOKEN})
    assert login.status_code == 200
    response = client.post(
        "/api/admin/cpa/channels",
        json={
            "name": "CPA",
            "cpa_endpoint": {
                "url": "https://proxy.example.com",
                "management_key": "secret",
            },
        },
    )
    assert response.status_code == 403


def test_cpa_usage_queue_requires_explicit_confirmation_and_reconfirmation(
    temp_data_dir,
):
    client = _admin_client()
    created = client.post(
        "/api/admin/cpa/channels",
        json={
            "name": "CPA",
            "cpa_endpoint": {
                "url": "https://proxy.example.com",
                "management_key": "secret",
            },
        },
    ).json()
    channel_id = created["id"]
    assert created["queue_enabled"] is False
    assert created["quota_source"] == "none"
    assert created["queue_status"] == "disabled"

    missing_confirmation = client.post(
        f"/api/admin/cpa/channels/{channel_id}/quota-source",
        json={"source": "native_queue"},
    )
    assert missing_confirmation.status_code == 400

    enabled = client.post(
        f"/api/admin/cpa/channels/{channel_id}/quota-source",
        json={"source": "native_queue", "confirm_exclusive": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["queue_enabled"] is True
    assert enabled.json()["exclusive_confirmed_at"]

    disabled_channel = client.put(
        f"/api/admin/cpa/channels/{channel_id}", json={"enabled": False}
    )
    assert disabled_channel.status_code == 200
    assert disabled_channel.json()["queue_enabled"] is False
    assert disabled_channel.json()["queue_status"] == "disabled"

    enabled_channel = client.put(
        f"/api/admin/cpa/channels/{channel_id}", json={"enabled": True}
    )
    assert enabled_channel.status_code == 200
    assert enabled_channel.json()["queue_enabled"] is False
    assert enabled_channel.json()["queue_status"] == "awaiting_confirmation"


def test_cpamp_snapshot_is_a_unified_cpa_source_and_never_returns_key(temp_data_dir):
    client = _admin_client()
    created = client.post(
        "/api/admin/cpa/channels",
        json={
            "name": "Read-only CPAMP",
            "cpamp_endpoint": {
                "url": "https://cpamp.example.com/",
                "admin_key": "cpamp-management-secret",
            },
            "quota_source": "cpamp_snapshot",
            "interval_sec": 600,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    channel_id = payload["id"]
    assert payload["cpamp_url"] == "https://cpamp.example.com"
    assert payload["cpa_url"] is None
    assert payload["quota_source"] == "cpamp_snapshot"
    assert payload["interval_sec"] == 600
    assert "management_key" not in payload
    assert "configured" not in payload

    with db.get_conn() as conn:
        stored = conn.execute(
            "SELECT cpamp_management_key FROM cpa_channels WHERE id = ?", (channel_id,)
        ).fetchone()[0]
    assert stored.startswith(ENCRYPTED_PREFIX)
    assert "cpamp-management-secret" not in stored

    public = TestClient(app).get("/api/public/quota")
    assert public.status_code == 200
    assert "cpamp_channels" not in public.json()
    public_channel = public.json()["cpa_channels"][0]
    assert "id" not in public_channel
    assert "url" not in public_channel

    updated = client.put(
        f"/api/admin/cpa/channels/{channel_id}",
        json={"cpamp_endpoint": {"admin_key": ""}, "enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert db.get_cpamp_channel(channel_id).management_key == "cpamp-management-secret"

    assert client.get("/api/admin/cpamp/channels").status_code == 404
    deleted = client.delete(f"/api/admin/cpa/channels/{channel_id}")
    assert deleted.status_code == 200
    assert db.get_cpamp_channel(channel_id) is None


def test_channel_update_reports_only_actual_sync_scheduling(temp_data_dir):
    client = _admin_client()
    created = client.post(
        "/api/admin/cpa/channels",
        json={
            "name": "CPA",
            "cpa_endpoint": {
                "url": "https://cpa.example.test",
                "management_key": "same-key",
            },
            "cpamp_endpoint": {
                "url": "https://cpamp.example.test",
                "admin_key": "same-cpamp-key",
            },
        },
    ).json()
    channel_id = created["id"]

    same_key = client.put(
        f"/api/admin/cpa/channels/{channel_id}",
        json={"cpa_endpoint": {"management_key": "same-key"}},
    )
    assert same_key.status_code == 200
    assert same_key.json()["sync_scheduled"] is False

    unselected_changed = client.put(
        f"/api/admin/cpa/channels/{channel_id}",
        json={"cpamp_endpoint": {"admin_key": "changed-cpamp-key"}},
    )
    assert unselected_changed.status_code == 200
    assert unselected_changed.json()["sync_scheduled"] is False

    selected_changed = client.put(
        f"/api/admin/cpa/channels/{channel_id}",
        json={"cpa_endpoint": {"management_key": "changed-key"}},
    )
    assert selected_changed.status_code == 200
    assert selected_changed.json()["sync_scheduled"] is True

    fetched = client.get(f"/api/admin/cpa/channels/{channel_id}")
    assert fetched.status_code == 200
    assert "sync_scheduled" not in fetched.json()
