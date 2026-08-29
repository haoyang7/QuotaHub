import sqlite3
import threading
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet

from app import db
from app.bootstrap import ensure_bootstrapped
from app.secrets import encrypt_secret


def test_create_and_list_opencode_account(temp_data_dir):
    row = db.create_opencode_account(
        name="test",
        workspace_id="Default",
        auth_cookie="auth=token",
    )
    accounts = db.list_opencode_accounts()
    assert len(accounts) == 1
    assert accounts[0].id == row.id
    assert accounts[0].name == "test"


def test_insert_usage_records_ignore(temp_data_dir):
    account = db.create_opencode_account(
        name="test",
        workspace_id="Default",
        auth_cookie="auth=token",
    )
    records = [
        {
            "usg_id": "usg_001",
            "created_at": "2026-07-09T08:16:06.000Z",
            "model": "glm-5.2",
            "provider": "deepinfra-glm-5.2",
            "input_tokens": 100,
            "output_tokens": 10,
            "cost_raw": 1000,
            "cost_usd": 0.000001,
            "key_id": "key_abc",
            "plan": "lite",
        }
    ]
    inserted = db.insert_usage_records_ignore(account.id, "wrk_test", records)
    assert inserted == 1
    inserted_again = db.insert_usage_records_ignore(account.id, "wrk_test", records)
    assert inserted_again == 0

    listed, total = db.list_usage_records(account.id)
    assert total == 1
    assert listed[0].usg_id == "usg_001"


def test_list_all_usage_records_and_daily_stats(temp_data_dir):
    today = datetime.now(UTC).date().isoformat()
    account_a = db.create_opencode_account(
        name="Alpha",
        workspace_id="Default",
        auth_cookie="auth=a",
    )
    account_b = db.create_opencode_account(
        name="Beta",
        workspace_id="Default",
        auth_cookie="auth=b",
    )
    db.insert_usage_records_ignore(
        account_a.id,
        "wrk_a",
        [
            {
                "usg_id": "usg_a1",
                "created_at": f"{today}T10:00:00.000Z",
                "model": "glm-5.2",
                "provider": "p",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost_raw": 1000,
                "cost_usd": 0.01,
                "key_id": "k1",
                "plan": "lite",
            }
        ],
    )
    db.insert_usage_records_ignore(
        account_b.id,
        "wrk_b",
        [
            {
                "usg_id": "usg_b1",
                "created_at": f"{today}T12:00:00.000Z",
                "model": "gpt",
                "provider": "p",
                "input_tokens": 2,
                "output_tokens": 2,
                "cost_raw": 2000,
                "cost_usd": 0.02,
                "key_id": "k2",
                "plan": "lite",
            }
        ],
    )

    records, total = db.list_all_usage_records(limit=10)
    assert total == 2
    assert {r.account_name for r in records} == {"Alpha", "Beta"}

    filtered, filtered_total = db.list_all_usage_records(account_id=account_a.id)
    assert filtered_total == 1
    assert filtered[0].account_name == "Alpha"

    stats = db.opencode_daily_stats(days=30)
    assert len(stats) >= 1
    assert stats[0]["request_count"] >= 1

    model_stats = db.opencode_daily_model_stats(days=30)
    assert len(model_stats) >= 1
    assert model_stats[0]["model"]


def test_import_from_config_once(temp_data_dir, monkeypatch: pytest.MonkeyPatch):
    config = temp_data_dir / "config.json"
    monkeypatch.setenv("QUOTAHUB_CONFIG", str(config))
    config.write_text(
        """
        {
          "listen_host": "127.0.0.1",
          "listen_port": 8788,
          "opencode_accounts": [
            {
              "name": "Imported",
              "workspace_id": "Default",
              "auth_cookie": "auth=imported"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    ensure_bootstrapped()
    assert db.count_opencode_accounts() == 1
    assert db.imported_flag_path().exists()

    config.write_text(
        '{"listen_host":"127.0.0.1","listen_port":8788,"opencode_accounts":[]}',
        encoding="utf-8",
    )
    ensure_bootstrapped()
    assert db.count_opencode_accounts() == 1


def test_init_db_backfills_stable_public_ids_for_legacy_accounts(temp_data_dir):
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO opencode_accounts (
                id, name, workspace_id, auth_cookie, created_at, updated_at
            ) VALUES ('legacy-open', 'Legacy Open', 'Default', 'ciphertext-placeholder', ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            """
            INSERT INTO ollama_accounts (
                id, name, session_cookie, created_at, updated_at
            ) VALUES ('legacy-ollama', 'Legacy Ollama', 'ciphertext-placeholder', ?, ?)
            """,
            (now, now),
        )

    db.init_db()
    with db.get_conn() as conn:
        first = (
            conn.execute(
                "SELECT public_id FROM opencode_quota_snapshots WHERE account_id = 'legacy-open'"
            ).fetchone()[0],
            conn.execute(
                "SELECT public_id FROM ollama_quota_snapshots WHERE account_id = 'legacy-ollama'"
            ).fetchone()[0],
        )

    db.init_db()
    with db.get_conn() as conn:
        second = (
            conn.execute(
                "SELECT public_id FROM opencode_quota_snapshots WHERE account_id = 'legacy-open'"
            ).fetchone()[0],
            conn.execute(
                "SELECT public_id FROM ollama_quota_snapshots WHERE account_id = 'legacy-ollama'"
            ).fetchone()[0],
        )
    assert first == second


def test_init_db_migrates_cpa_passive_snapshot_columns_idempotently(temp_data_dir):
    expected = {
        "quota_source",
        "observed_at",
        "last_active_attempt_at",
        "locator_hash",
        "subject_hash",
        "accept_observed_after",
    }
    channel = db.create_cpa_channel(
        name="Legacy CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
    )
    with db.get_conn() as conn:
        conn.execute("DROP TABLE cpa_quota_snapshots")
        conn.execute(
            """
            CREATE TABLE cpa_quota_snapshots (
                channel_id TEXT NOT NULL REFERENCES cpa_channels(id) ON DELETE CASCADE,
                account_key_hash TEXT NOT NULL,
                public_id TEXT NOT NULL UNIQUE,
                account_display TEXT NOT NULL,
                plan TEXT NOT NULL,
                windows_json TEXT NOT NULL DEFAULT '[]',
                visible INTEGER NOT NULL DEFAULT 1,
                last_attempt_at TEXT,
                last_success_at TEXT,
                last_attempt_status TEXT,
                stale INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                quota_source TEXT,
                observed_at TEXT,
                last_active_attempt_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (channel_id, account_key_hash)
            )
            """
        )
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            INSERT INTO cpa_quota_snapshots (
                channel_id, account_key_hash, public_id, account_display, plan,
                created_at, updated_at
            ) VALUES (?, 'hmac:v1:legacy', 'legacy-cpa-public-id',
                'l***@example.test', 'Plus', ?, ?)
            """,
            (channel.id, now, now),
        )

    db.init_db()
    with db.get_conn() as conn:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(cpa_quota_snapshots)").fetchall()
        }
        migrated = conn.execute(
            """
            SELECT public_id, locator_hash, subject_hash, accept_observed_after
            FROM cpa_quota_snapshots WHERE channel_id = ?
            """,
            (channel.id,),
        ).fetchone()
    assert expected <= columns
    assert migrated is not None
    assert migrated["public_id"] == "legacy-cpa-public-id"
    assert migrated["locator_hash"] is None
    assert migrated["subject_hash"] is None
    assert migrated["accept_observed_after"] is None

    db.init_db()
    with db.get_conn() as conn:
        columns_after = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(cpa_quota_snapshots)").fetchall()
        }
    assert columns_after == columns


def test_init_db_migrates_cpamp_identity_columns_idempotently(temp_data_dir):
    db.db_path().unlink()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(db.db_path()) as conn:
        conn.executescript(
            """
            CREATE TABLE cpamp_channels (
                id TEXT PRIMARY KEY, public_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL, base_url TEXT NOT NULL,
                management_key TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                interval_sec INTEGER NOT NULL DEFAULT 1800,
                last_attempt_at TEXT, last_success_at TEXT,
                last_attempt_status TEXT, stale INTEGER NOT NULL DEFAULT 0,
                error TEXT, snapshot_source TEXT, last_source_snapshot_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE cpamp_quota_snapshots (
                channel_id TEXT NOT NULL REFERENCES cpamp_channels(id) ON DELETE CASCADE,
                account_key_hash TEXT NOT NULL, public_id TEXT NOT NULL UNIQUE,
                account_display TEXT NOT NULL, plan TEXT NOT NULL,
                windows_json TEXT NOT NULL DEFAULT '[]', visible INTEGER NOT NULL DEFAULT 1,
                last_attempt_at TEXT, last_success_at TEXT, last_attempt_status TEXT,
                stale INTEGER NOT NULL DEFAULT 0, error TEXT, quota_source TEXT,
                observed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY (channel_id, account_key_hash)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO cpamp_channels (
                id, public_id, name, base_url, management_key, interval_sec,
                created_at, updated_at
            ) VALUES ('legacy-cpamp', 'legacy-channel-public', 'Legacy CPAMP',
                'https://cpamp.example.test', ?, 600, ?, ?)
            """,
            (encrypt_secret("secret"), now, now),
        )
        conn.execute(
            """
            INSERT INTO cpamp_quota_snapshots (
                channel_id, account_key_hash, public_id, account_display, plan,
                windows_json, last_success_at, last_attempt_status, quota_source,
                observed_at, created_at, updated_at
            ) VALUES ('legacy-cpamp', 'hmac:v1:legacy', 'legacy-account-public',
                'l***@example.test', 'Plus', '[]', ?, 'success',
                'quota_snapshots', ?, ?, ?)
            """,
            (now, now, now, now),
        )

    db.init_db()
    db.init_db()
    with db.get_conn() as conn:
        channel = conn.execute(
            "SELECT * FROM cpa_channels WHERE name = 'Legacy CPAMP'"
        ).fetchone()
        account = conn.execute(
            "SELECT * FROM cpa_accounts WHERE channel_id = ?", (channel["id"],)
        ).fetchone()
        snapshot = conn.execute(
            "SELECT * FROM cpa_quota_snapshots WHERE channel_id = ?", (channel["id"],)
        ).fetchone()
        legacy_tables = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name IN ('cpamp_channels', 'cpamp_quota_snapshots')
            """
        ).fetchall()
    assert channel["quota_source"] == "cpamp_snapshot"
    assert channel["cpamp_base_url"] == "https://cpamp.example.test"
    assert account["public_id"] == "legacy-account-public"
    assert snapshot["source_mode"] == "cpamp_snapshot"
    assert legacy_tables == []


def test_init_db_rolls_back_candidate_cpamp_migration_on_failure(temp_data_dir):
    db.db_path().unlink()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(db.db_path()) as conn:
        conn.executescript(
            """
            CREATE TABLE cpamp_channels (
                id TEXT PRIMARY KEY, public_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL, base_url TEXT NOT NULL,
                management_key TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                interval_sec INTEGER NOT NULL DEFAULT 1800,
                last_attempt_at TEXT, last_success_at TEXT,
                last_attempt_status TEXT, stale INTEGER NOT NULL DEFAULT 0,
                error TEXT, snapshot_source TEXT, last_source_snapshot_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE cpamp_quota_snapshots (
                channel_id TEXT NOT NULL, account_key_hash TEXT NOT NULL,
                public_id TEXT NOT NULL UNIQUE
            );
            """
        )
        conn.execute(
            """
            INSERT INTO cpamp_channels (
                id, public_id, name, base_url, management_key, created_at, updated_at
            ) VALUES ('legacy-cpamp', 'legacy-channel-public', 'Legacy CPAMP',
                'https://cpamp.example.test', ?, ?, ?)
            """,
            (encrypt_secret("secret"), now, now),
        )
        conn.execute(
            """
            INSERT INTO cpamp_quota_snapshots (
                channel_id, account_key_hash, public_id
            ) VALUES ('legacy-cpamp', 'hmac:v1:legacy', 'legacy-account-public')
            """
        )

    with pytest.raises(IndexError):
        db.init_db()

    with sqlite3.connect(db.db_path()) as conn:
        cpamp_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(cpamp_channels)").fetchall()
        }
        migrated_count = conn.execute("SELECT COUNT(*) FROM cpa_channels").fetchone()[0]
        legacy_count = conn.execute("SELECT COUNT(*) FROM cpamp_channels").fetchone()[0]
    assert "collection_revision" not in cpamp_columns
    assert migrated_count == 0
    assert legacy_count == 1


def test_import_from_config_preserves_disabled_accounts(temp_data_dir, monkeypatch):
    config = temp_data_dir / "legacy-disabled.json"
    monkeypatch.setenv("QUOTAHUB_CONFIG", str(config))
    config.write_text(
        '''{
          "opencode_accounts": [{
            "name": "Disabled Open", "workspace_id": "Default",
            "auth_cookie": "auth=disabled", "enabled": false
          }],
          "ollama_accounts": [{
            "name": "Disabled Ollama", "session_cookie": "aid=x", "enabled": false
          }]
        }''',
        encoding="utf-8",
    )

    ensure_bootstrapped()

    assert db.list_opencode_accounts()[0].enabled is False
    assert db.list_ollama_accounts()[0].enabled is False


def test_collection_revision_changes_only_for_collection_inputs(temp_data_dir):
    opencode = db.create_opencode_account(
        name="Open", workspace_id="Default", auth_cookie="auth=old"
    )
    db.record_opencode_resolved_workspace(
        opencode.id,
        "wrk_old",
        expected_collection_revision=opencode.collection_revision,
    )
    renamed = db.update_opencode_account(
        opencode.id, name="Renamed", show_weekly=False
    )
    assert renamed.collection_revision == opencode.collection_revision
    assert renamed.resolved_workspace_id == "wrk_old"

    credential_changed = db.update_opencode_account(
        opencode.id, auth_cookie="auth=new"
    )
    assert credential_changed.collection_revision == opencode.collection_revision + 1
    assert credential_changed.resolved_workspace_id is None
    workspace_changed = db.update_opencode_account(
        opencode.id, workspace_id="Another"
    )
    assert workspace_changed.collection_revision == credential_changed.collection_revision + 1
    disabled = db.update_opencode_account(opencode.id, enabled=False)
    assert disabled.collection_revision == workspace_changed.collection_revision + 1

    ollama = db.create_ollama_account(name="Ollama", session_cookie="session=old")
    displayed = db.update_ollama_account(ollama.id, name="Shown", show_weekly=False)
    assert displayed.collection_revision == ollama.collection_revision
    cookie_changed = db.update_ollama_account(ollama.id, session_cookie="session=new")
    assert cookie_changed.collection_revision == ollama.collection_revision + 1

    channel = db.create_cpa_channel(
        name="CPA", base_url="https://cpa.example.test", management_key="old-key"
    )
    display_changed = db.update_cpa_channel(
        channel.id, name="Renamed CPA", interval_sec=3600
    )
    assert display_changed.collection_revision == channel.collection_revision
    key_changed = db.update_cpa_channel(channel.id, management_key="new-key")
    assert key_changed.collection_revision == channel.collection_revision + 1


def test_init_db_adds_collection_revision_to_legacy_tables(temp_data_dir):
    db.db_path().unlink()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(db.db_path()) as conn:
        conn.executescript(
            """
            CREATE TABLE opencode_accounts (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, workspace_id TEXT NOT NULL,
                resolved_workspace_id TEXT, auth_cookie TEXT NOT NULL,
                show_rolling INTEGER NOT NULL DEFAULT 1,
                show_weekly INTEGER NOT NULL DEFAULT 1,
                show_monthly INTEGER NOT NULL DEFAULT 1,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE ollama_accounts (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, session_cookie TEXT NOT NULL,
                show_session INTEGER NOT NULL DEFAULT 1,
                show_weekly INTEGER NOT NULL DEFAULT 1,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE cpa_channels (
                id TEXT PRIMARY KEY, public_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL, base_url TEXT NOT NULL,
                management_key TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                interval_sec INTEGER NOT NULL DEFAULT 1800,
                last_attempt_at TEXT, last_success_at TEXT,
                last_attempt_status TEXT, stale INTEGER NOT NULL DEFAULT 0,
                error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT INTO opencode_accounts (
                id, name, workspace_id, auth_cookie, created_at, updated_at
            ) VALUES ('legacy-open', 'Legacy', 'Default', ?, ?, ?)
            """,
            (encrypt_secret("auth=legacy"), now, now),
        )
    db.init_db()
    db.init_db()

    with db.get_conn() as conn:
        for table in ("opencode_accounts", "ollama_accounts", "cpa_channels"):
            columns = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            assert "collection_revision" in columns
        cpa_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(cpa_channels)").fetchall()
        }
        assert {
            "queue_status",
            "queue_enabled",
            "exclusive_confirmed_at",
            "queue_last_poll_at",
            "queue_last_event_at",
            "queue_last_error_code",
        } <= cpa_columns
        revision = conn.execute(
            "SELECT collection_revision FROM opencode_accounts WHERE id = 'legacy-open'"
        ).fetchone()[0]
    assert revision == 1


def test_cpa_usage_queue_requires_confirmation_and_resets_on_changes(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA", base_url="https://cpa.example.test", management_key="old-key"
    )
    assert channel.queue_enabled is False
    assert channel.quota_source == "none"
    assert channel.queue_status == "disabled"
    assert channel.exclusive_confirmed_at is None

    with pytest.raises(ValueError, match="确认独占条件"):
        db.configure_cpa_usage_queue(channel.id, enabled=True)

    confirmed = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert confirmed is not None
    assert confirmed.queue_enabled is True
    assert confirmed.queue_status == "active"
    assert confirmed.exclusive_confirmed_at

    renamed = db.update_cpa_channel(channel.id, name="Renamed")
    assert renamed is not None
    assert renamed.queue_enabled is True

    key_changed = db.update_cpa_channel(channel.id, management_key="new-key")
    assert key_changed is not None
    assert key_changed.queue_enabled is False
    assert key_changed.queue_status == "awaiting_confirmation"
    assert key_changed.exclusive_confirmed_at is None

    confirmed_again = db.configure_cpa_usage_queue(
        channel.id, enabled=True, confirm_exclusive=True
    )
    assert confirmed_again is not None and confirmed_again.queue_enabled is True
    disabled = db.update_cpa_channel(channel.id, enabled=False)
    assert disabled is not None
    assert disabled.queue_enabled is False
    assert disabled.queue_status == "disabled"
    assert disabled.exclusive_confirmed_at is None

    enabled_again = db.update_cpa_channel(channel.id, enabled=True)
    assert enabled_again is not None
    assert enabled_again.queue_enabled is False
    assert enabled_again.queue_status == "awaiting_confirmation"
    assert enabled_again.exclusive_confirmed_at is None


def test_cpamp_channel_crud_encrypts_secret_and_cascades_snapshots(temp_data_dir):
    channel = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="cpamp-secret",
    )
    with db.get_conn() as conn:
        stored = conn.execute(
            "SELECT cpamp_management_key FROM cpa_channels WHERE id = ?", (channel.id,)
        ).fetchone()[0]
    assert stored.startswith("fernet:v1:")
    assert "cpamp-secret" not in stored

    db.record_cpamp_quota_snapshot(
        channel.id,
        "hmac:v1:account",
        account_display="a***@example.test",
        plan="Plus",
        success=True,
        windows=[],
        observed_at="2026-08-15T01:00:00Z",
    )
    updated = db.update_cpamp_channel(channel.id, interval_sec=3600)
    assert updated is not None
    assert updated.interval_sec == 3600
    assert updated.collection_revision == channel.collection_revision

    assert db.delete_cpamp_channel(channel.id) is True
    with db.get_conn() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM cpa_quota_snapshots WHERE channel_id = ?",
            (channel.id,),
        ).fetchone()[0] == 0


def test_discovery_does_not_overwrite_successful_quota_plan(temp_data_dir):
    cpa = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    db.record_cpa_quota_snapshot(
        cpa.id,
        "hmac:v1:cpa-account",
        account_display="a***@example.test",
        plan="Pro 20x",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    db.prepare_cpa_channel_discovery(
        cpa.id,
        [("hmac:v1:cpa-account", None, "a***@example.test", "Plus")],
    )
    assert db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"][0][
        "plan"
    ] == "Pro 20x"

    cpamp = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    db.record_cpamp_quota_snapshot(
        cpamp.id,
        "hmac:v1:cpamp-account",
        account_display="b***@example.test",
        plan="Pro 5x",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 70}],
        observed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    db.prepare_cpamp_channel_discovery(
        cpamp.id,
        [("hmac:v1:cpamp-account", None, "b***@example.test", "Free")],
    )
    assert db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"][0][
        "plan"
    ] == "Pro 5x"


def test_native_failures_do_not_mark_cpamp_history_stale(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="cpa-secret",
        cpamp_base_url="https://cpamp.example.test",
        cpamp_management_key="cpamp-secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    for source_mode in ("native_queue", "cpamp_snapshot"):
        db.record_cpa_quota_snapshot(
            channel.id,
            "shared-account",
            account_display="s***@example.test",
            plan="Plus",
            success=True,
            windows=[],
            source_mode=source_mode,
            observed_at="2026-08-18T00:00:00Z",
        )

    assert db.record_cpa_queue_state(channel.id, status="degraded") is True
    db.record_cpa_channel_attempt(channel.id, success=False, error="discovery_error")

    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT source_mode, stale FROM cpa_quota_snapshots
            WHERE channel_id = ? ORDER BY source_mode
            """,
            (channel.id,),
        ).fetchall()
    assert {row["source_mode"]: row["stale"] for row in rows} == {
        "cpamp_snapshot": 0,
        "native_queue": 1,
    }


def test_cpamp_endpoint_generation_does_not_reuse_future_old_snapshot(
    temp_data_dir,
):
    channel = db.create_cpa_channel(
        name="CPAMP",
        cpamp_base_url="https://old.example.test",
        cpamp_management_key="old-secret",
        quota_source="cpamp_snapshot",
    )
    account = db.CPADiscoveryAccount(
        account_key_hash="hmac:v1:shared-account",
        legacy_account_key_hashes=(),
        locator_hash="hmac:v1:shared-locator",
        subject_hash="hmac:v1:shared-subject",
        account_display="s***@example.test",
        plan="Plus",
    )
    db.prepare_cpa_channel_discovery(
        channel.id, [account], source_mode="cpamp_snapshot"
    )
    first = db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "old-endpoint"}],
        observed_at="2030-01-01T00:00:00Z",
    )
    original_public_id = db.list_cached_cpa_channels(enabled_only=False)[0][
        "accounts"
    ][0]["public_id"]
    assert first.applied is True

    changed = db.update_cpa_channel(
        channel.id,
        cpamp_base_url="https://new.example.test",
        cpamp_management_key="new-secret",
    )
    assert changed is not None
    assert changed.cpamp_endpoint_revision == 2
    assert db.list_cpamp_snapshot_identities(channel.id) == []

    db.prepare_cpa_channel_discovery(
        channel.id,
        [account],
        source_mode="cpamp_snapshot",
        expected_collection_revision=changed.collection_revision,
    )
    second = db.record_cpamp_quota_snapshot(
        channel.id,
        account.account_key_hash,
        account_display=account.account_display,
        plan=account.plan,
        success=True,
        windows=[{"label": "new-endpoint"}],
        observed_at="2026-08-19T00:00:00Z",
        expected_collection_revision=changed.collection_revision,
    )

    assert second.applied is True
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert len(cached) == 1
    assert cached[0]["public_id"] == original_public_id
    assert cached[0]["windows"] == [{"label": "new-endpoint"}]
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT endpoint_revision, windows_json, visible
            FROM cpa_quota_snapshots
            WHERE channel_id = ? AND source_mode = 'cpamp_snapshot'
            ORDER BY endpoint_revision
            """,
            (channel.id,),
        ).fetchall()
    assert [(row["endpoint_revision"], row["visible"]) for row in rows] == [
        (1, 0),
        (2, 1),
    ]
    assert '"old-endpoint"' in rows[0]["windows_json"]
    assert '"new-endpoint"' in rows[1]["windows_json"]


def test_native_queue_batches_stay_isolated_by_endpoint_generation(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://old.example.test",
        management_key="old-secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account = db.CPADiscoveryAccount(
        account_key_hash="hmac:v1:shared-native-account",
        legacy_account_key_hashes=(),
        locator_hash="hmac:v1:shared-native-locator",
        subject_hash="hmac:v1:shared-native-subject",
        account_display="n***@example.test",
        plan="Plus",
    )
    db.prepare_cpa_channel_discovery(channel.id, [account])
    first = db.record_cpa_quota_batch(
        channel.id,
        [
            {
                "account_key_hash": account.account_key_hash,
                "account_display": account.account_display,
                "plan": account.plan,
                "windows": [{"label": "old-endpoint"}],
                "observed_at": "2030-01-01T00:00:00Z",
            }
        ],
        endpoint_revision=channel.cpa_endpoint_revision,
    )
    assert first[0].applied is True

    changed = db.update_cpa_channel(
        channel.id,
        base_url="https://new.example.test",
        management_key="new-secret",
    )
    assert changed is not None
    assert changed.cpa_endpoint_revision == 2
    db.prepare_cpa_channel_discovery(
        channel.id,
        [account],
        expected_collection_revision=changed.collection_revision,
    )
    current = db.record_cpa_quota_batch(
        channel.id,
        [
            {
                "account_key_hash": account.account_key_hash,
                "account_display": account.account_display,
                "plan": account.plan,
                "windows": [{"label": "new-endpoint"}],
                "observed_at": "2026-08-19T00:00:00Z",
            }
        ],
        endpoint_revision=changed.cpa_endpoint_revision,
    )
    late_old = db.record_cpa_quota_batch(
        channel.id,
        [
            {
                "account_key_hash": account.account_key_hash,
                "account_display": account.account_display,
                "plan": account.plan,
                "windows": [{"label": "late-old-endpoint"}],
                "observed_at": "2031-01-01T00:00:00Z",
            }
        ],
        endpoint_revision=channel.cpa_endpoint_revision,
    )

    assert current[0].applied is True
    assert late_old[0].applied is True
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["windows"] == [{"label": "new-endpoint"}]
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT endpoint_revision, windows_json
            FROM cpa_quota_snapshots
            WHERE channel_id = ? AND source_mode = 'native_queue'
            ORDER BY endpoint_revision
            """,
            (channel.id,),
        ).fetchall()
    assert [row["endpoint_revision"] for row in rows] == [1, 2]
    assert '"late-old-endpoint"' in rows[0]["windows_json"]
    assert '"new-endpoint"' in rows[1]["windows_json"]


def test_init_db_migrates_candidate_generation_storage_hash_idempotently(
    temp_data_dir,
):
    channel = db.create_cpa_channel(
        name="CPAMP",
        cpamp_base_url="https://cpamp.example.test",
        cpamp_management_key="secret",
        quota_source="cpamp_snapshot",
    )
    account_hash = "hmac:v1:candidate-generation-account"
    db.record_cpamp_quota_snapshot(
        channel.id,
        account_hash,
        account_display="c***@example.test",
        plan="Plus",
        success=True,
        windows=[{"label": "candidate"}],
        observed_at="2026-08-19T00:00:00Z",
    )
    with db.get_conn() as conn:
        old_hash = conn.execute(
            "SELECT account_key_hash FROM cpa_quota_snapshots WHERE channel_id = ?",
            (channel.id,),
        ).fetchone()["account_key_hash"]
        conn.execute(
            "UPDATE cpa_channels SET cpamp_endpoint_revision = 2 WHERE id = ?",
            (channel.id,),
        )
        conn.execute(
            "UPDATE cpa_quota_snapshots SET endpoint_revision = 2 WHERE channel_id = ?",
            (channel.id,),
        )

    db.init_db()
    db.init_db()

    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT account_key_hash, endpoint_revision
            FROM cpa_quota_snapshots WHERE channel_id = ?
            """,
            (channel.id,),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["endpoint_revision"] == 2
    assert rows[0]["account_key_hash"] != old_hash


def test_guarded_usage_write_rejects_revision_changed_by_other_connection(
    temp_data_dir,
):
    account = db.create_opencode_account(
        name="Race", workspace_id="Default", auth_cookie="auth=old"
    )
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    record = {
        "usg_id": "usg-race",
        "created_at": "2026-08-14T00:00:00Z",
        "model": "model",
        "provider": "provider",
        "input_tokens": 1,
        "output_tokens": 1,
        "cost_raw": 1,
        "cost_usd": 0.0,
    }

    def write_stale_page() -> None:
        barrier.wait()
        try:
            db.insert_usage_records_ignore(
                account.id,
                "wrk_old",
                [record],
                expected_collection_revision=account.collection_revision,
            )
        except BaseException as exc:  # noqa: BLE001 - captured from worker thread
            errors.append(exc)

    conn = sqlite3.connect(db.db_path(), timeout=5)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE opencode_accounts
            SET auth_cookie = ?, collection_revision = collection_revision + 1
            WHERE id = ?
            """,
            (encrypt_secret("auth=new"), account.id),
        )
        worker = threading.Thread(target=write_stale_page)
        worker.start()
        barrier.wait()
        conn.commit()
        worker.join(timeout=5)
    finally:
        conn.close()

    assert not worker.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], db.CollectionGuardRejected)
    assert errors[0].reason == "source_changed"
    assert db.list_usage_records(account.id)[1] == 0


def test_guarded_quota_write_rejects_expired_owner_lease(temp_data_dir):
    account = db.create_opencode_account(
        name="Lease", workspace_id="Default", auth_cookie="auth=lease"
    )
    assert db.acquire_scheduler_lease("quota-test", "owner-a") is True
    with db.get_conn() as conn:
        conn.execute(
            "DELETE FROM scheduler_leases WHERE name = ?", ("quota-test",)
        )

    with pytest.raises(db.CollectionGuardRejected) as exc_info:
        db.record_opencode_quota_snapshot(
            account.id,
            success=True,
            windows=[],
            expected_collection_revision=account.collection_revision,
            lease_name="quota-test",
            lease_owner_id="owner-a",
        )
    assert exc_info.value.reason == "lease_lost"
    assert db.get_quota_snapshot_attempt("opencode", account.id) is None


def _plan_ts(base: datetime, offset_seconds: int) -> str:
    return (
        (base + timedelta(seconds=offset_seconds))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def test_init_db_migrates_cpa_plan_observed_at_idempotently(temp_data_dir):
    channel = db.create_cpa_channel(
        name="Legacy CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
    )
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with db.get_conn() as conn:
        conn.execute("DROP TABLE cpa_accounts")
        conn.execute("DROP TABLE cpa_quota_snapshots")
        conn.execute(
            """
            CREATE TABLE cpa_accounts (
                channel_id TEXT NOT NULL REFERENCES cpa_channels(id) ON DELETE CASCADE,
                canonical_account_hash TEXT NOT NULL,
                public_id TEXT NOT NULL UNIQUE,
                account_display TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT '未知套餐',
                locator_hash TEXT,
                subject_hash TEXT,
                visible INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (channel_id, canonical_account_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE cpa_quota_snapshots (
                channel_id TEXT NOT NULL REFERENCES cpa_channels(id) ON DELETE CASCADE,
                account_key_hash TEXT NOT NULL,
                canonical_account_hash TEXT,
                source_mode TEXT NOT NULL DEFAULT 'native_queue',
                endpoint_revision INTEGER NOT NULL DEFAULT 1,
                locator_hash TEXT,
                subject_hash TEXT,
                public_id TEXT NOT NULL UNIQUE,
                account_display TEXT NOT NULL,
                plan TEXT NOT NULL,
                windows_json TEXT NOT NULL DEFAULT '[]',
                visible INTEGER NOT NULL DEFAULT 1,
                last_attempt_at TEXT,
                last_success_at TEXT,
                last_attempt_status TEXT,
                stale INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                quota_source TEXT,
                observed_at TEXT,
                accept_observed_after TEXT,
                last_active_attempt_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (channel_id, account_key_hash)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO cpa_accounts (
                channel_id, canonical_account_hash, public_id, account_display,
                plan, visible, created_at, updated_at
            ) VALUES (?, 'hmac:v1:legacy-acct', 'legacy-acct-public',
                'l***@example.test', 'Pro 20x', 1, ?, ?)
            """,
            (channel.id, now, now),
        )
        conn.execute(
            """
            INSERT INTO cpa_quota_snapshots (
                channel_id, account_key_hash, canonical_account_hash, public_id,
                account_display, plan, source_mode, last_success_at,
                last_attempt_status, created_at, updated_at
            ) VALUES (?, 'hmac:v1:legacy-acct', 'hmac:v1:legacy-acct',
                'legacy-snap-public', 'l***@example.test', 'Pro 20x', 'native_queue',
                ?, 'success', ?, ?)
            """,
            (channel.id, now, now, now),
        )

    db.init_db()
    with db.get_conn() as conn:
        acct_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(cpa_accounts)").fetchall()
        }
        snap_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(cpa_quota_snapshots)").fetchall()
        }
        assert "plan_observed_at" in acct_columns
        assert "plan_observed_at" in snap_columns
        acct = conn.execute(
            "SELECT plan, plan_observed_at FROM cpa_accounts WHERE channel_id = ?",
            (channel.id,),
        ).fetchone()
        snap = conn.execute(
            """
            SELECT plan, plan_observed_at FROM cpa_quota_snapshots
            WHERE channel_id = ? AND source_mode = 'native_queue'
            """,
            (channel.id,),
        ).fetchone()
    assert acct["plan"] == "Pro 20x"
    assert acct["plan_observed_at"] is None
    assert snap["plan"] == "Pro 20x"
    assert snap["plan_observed_at"] is None

    # Idempotent: re-running init_db keeps the column set and the row data.
    db.init_db()
    with db.get_conn() as conn:
        acct_columns_after = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(cpa_accounts)").fetchall()
        }
        snap_columns_after = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(cpa_quota_snapshots)").fetchall()
        }
        acct_after = conn.execute(
            "SELECT plan, plan_observed_at FROM cpa_accounts WHERE channel_id = ?",
            (channel.id,),
        ).fetchone()
    assert acct_columns_after == acct_columns
    assert snap_columns_after == snap_columns
    assert acct_after["plan"] == "Pro 20x"
    assert acct_after["plan_observed_at"] is None


def test_plan_arbitration_upgrade_from_weak_to_strong(temp_data_dir):
    """Regression: account upgraded Plus -> Pro 20x must surface Pro 20x."""
    cpa = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account_hash = "hmac:v1:cpa-account"
    display = "a***@example.test"
    base = datetime.now(UTC)
    t0 = _plan_ts(base, -200)
    t1 = _plan_ts(base, 0)

    db.prepare_cpa_channel_discovery(
        cpa.id,
        [(account_hash, None, display, "Plus")],
    )
    db.record_cpa_quota_snapshot(
        cpa.id,
        account_hash,
        account_display=display,
        plan="Plus",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=t0,
    )
    db.prepare_cpa_channel_discovery(
        cpa.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=account_hash,
                legacy_account_key_hashes=(),
                locator_hash=account_hash,
                subject_hash="",
                account_display=display,
                plan="Pro 20x",
                plan_observed_at=t1,
            )
        ],
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Pro 20x"


def test_quota_observed_at_does_not_become_plan_observed_at(temp_data_dir):
    cpamp = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    observed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    db.record_cpamp_quota_snapshot(
        cpamp.id,
        "hmac:v1:cpamp-account",
        account_display="a***@example.test",
        plan="Plus",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=observed_at,
    )
    with db.get_conn() as conn:
        account = conn.execute(
            "SELECT plan, plan_observed_at FROM cpa_accounts WHERE channel_id = ?",
            (cpamp.id,),
        ).fetchone()
        snapshot = conn.execute(
            "SELECT plan, plan_observed_at FROM cpa_quota_snapshots WHERE channel_id = ?",
            (cpamp.id,),
        ).fetchone()
    assert account["plan"] == "Plus"
    assert account["plan_observed_at"] is None
    assert snapshot["plan"] == "Plus"
    assert snapshot["plan_observed_at"] is None


def test_plan_arbitration_cpamp_upgrade_from_weak_to_strong(temp_data_dir):
    """CPAMP path must also thread plan_observed_at through to the snapshot."""
    cpamp = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account_hash = "hmac:v1:cpamp-account"
    display = "b***@example.test"
    base = datetime.now(UTC)
    t0 = _plan_ts(base, -200)
    t1 = _plan_ts(base, 0)

    db.prepare_cpamp_channel_discovery(
        cpamp.id,
        [(account_hash, None, display, "Plus")],
    )
    db.record_cpamp_quota_snapshot(
        cpamp.id,
        account_hash,
        account_display=display,
        plan="Plus",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=t0,
    )
    db.prepare_cpamp_channel_discovery(
        cpamp.id,
        [
            db.CPAMPDiscoveryAccount(
                account_key_hash=account_hash,
                legacy_account_key_hashes=(),
                locator_hash=account_hash,
                subject_hash="",
                account_display=display,
                plan="Pro 20x",
                plan_observed_at=t1,
            )
        ],
    )
    cached = db.list_cached_cpamp_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Pro 20x"


def test_plan_arbitration_weak_snapshot_keeps_strong_plan(temp_data_dir):
    """A weak-source snapshot (no observed time) must not overwrite a known plan."""
    cpa = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account_hash = "hmac:v1:cpa-account"
    display = "a***@example.test"
    t1 = _plan_ts(datetime.now(UTC), 0)

    db.record_cpa_quota_snapshot(
        cpa.id,
        account_hash,
        account_display=display,
        plan="Pro 20x",
        success=True,
        windows=[],
        observed_at=t1,
        plan_observed_at=t1,
    )
    # Weak source: neither observed_at nor plan_observed_at provided.
    db.record_cpa_quota_snapshot(
        cpa.id,
        account_hash,
        account_display=display,
        plan="Plus",
        success=True,
        windows=[],
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Pro 20x"
    with db.get_conn() as conn:
        snap = conn.execute(
            "SELECT plan, plan_observed_at FROM cpa_quota_snapshots WHERE channel_id = ?",
            (cpa.id,),
        ).fetchone()
    assert snap["plan"] == "Pro 20x"
    assert snap["plan_observed_at"] == t1


def test_plan_arbitration_older_strong_source_keeps_newer_plan(temp_data_dir):
    """An older strong observation must not overwrite a newer known plan."""
    cpa = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account_hash = "hmac:v1:cpa-account"
    display = "a***@example.test"
    base = datetime.now(UTC)
    t0 = _plan_ts(base, -100)
    t1 = _plan_ts(base, 0)

    db.record_cpa_quota_snapshot(
        cpa.id,
        account_hash,
        account_display=display,
        plan="Pro 20x",
        success=True,
        windows=[],
        observed_at=t1,
        plan_observed_at=t1,
    )
    db.prepare_cpa_channel_discovery(
        cpa.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=account_hash,
                legacy_account_key_hashes=(),
                locator_hash=account_hash,
                subject_hash="",
                account_display=display,
                plan="Pro 5x",
                plan_observed_at=t0,
            )
        ],
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Pro 20x"


def test_plan_arbitration_weak_discovery_fills_plan_before_snapshot(temp_data_dir):
    """Weak discovery alone is enough to surface a plan before any quota success."""
    cpa = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account_hash = "hmac:v1:cpa-account"
    display = "a***@example.test"
    db.prepare_cpa_channel_discovery(
        cpa.id,
        [(account_hash, None, display, "Plus")],
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Plus"


def test_plan_arbitration_strong_source_overwrites_null_observed_at(temp_data_dir):
    """Legacy rows (plan_observed_at NULL) accept a strong-source upgrade."""
    cpa = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account_hash = "hmac:v1:cpa-account"
    display = "a***@example.test"
    t1 = _plan_ts(datetime.now(UTC), 0)

    # Legacy row: plan set but plan_observed_at NULL (no observed_at passed).
    db.record_cpa_quota_snapshot(
        cpa.id,
        account_hash,
        account_display=display,
        plan="Pro 5x",
        success=True,
        windows=[],
    )
    db.prepare_cpa_channel_discovery(
        cpa.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=account_hash,
                legacy_account_key_hashes=(),
                locator_hash=account_hash,
                subject_hash="",
                account_display=display,
                plan="Pro 20x",
                plan_observed_at=t1,
            )
        ],
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Pro 20x"


def test_plan_arbitration_unknown_strong_source_does_not_downgrade(temp_data_dir):
    """A strong source carrying 未知套餐 must never downgrade a known plan."""
    cpa = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    account_hash = "hmac:v1:cpa-account"
    display = "a***@example.test"
    base = datetime.now(UTC)
    t1 = _plan_ts(base, 0)
    t2 = _plan_ts(base, 100)

    db.record_cpa_quota_snapshot(
        cpa.id,
        account_hash,
        account_display=display,
        plan="Pro 20x",
        success=True,
        windows=[],
        observed_at=t1,
        plan_observed_at=t1,
    )
    db.prepare_cpa_channel_discovery(
        cpa.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash=account_hash,
                legacy_account_key_hashes=(),
                locator_hash=account_hash,
                subject_hash="",
                account_display=display,
                plan="未知套餐",
                plan_observed_at=t2,
            )
        ],
    )
    cached = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"]
    assert cached[0]["plan"] == "Pro 20x"
    with db.get_conn() as conn:
        snap = conn.execute(
            "SELECT plan, plan_observed_at FROM cpa_quota_snapshots WHERE channel_id = ?",
            (cpa.id,),
        ).fetchone()
        acct = conn.execute(
            "SELECT plan, plan_observed_at FROM cpa_accounts WHERE channel_id = ?",
            (cpa.id,),
        ).fetchone()
    assert snap["plan"] == "Pro 20x"
    assert snap["plan_observed_at"] == t1
    assert acct["plan"] == "Pro 20x"
    assert acct["plan_observed_at"] == t1


def test_list_cpamp_snapshot_identities_backfills_strong_plan_observed_at(
    temp_data_dir,
):
    """list_cpamp_snapshot_identities must thread plan_observed_at so the
    discovery-failure fallback rediscovery keeps treating a strong-source plan
    as strong instead of collapsing it to a weak id_token plan."""
    cpamp = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account_hash = "hmac:v1:cpamp-account"
    display = "b***@example.test"
    t1 = _plan_ts(datetime.now(UTC), 0)
    db.prepare_cpamp_channel_discovery(
        cpamp.id, [(account_hash, None, display, "Plus")]
    )
    db.record_cpamp_quota_snapshot(
        cpamp.id,
        account_hash,
        account_display=display,
        plan="Pro 20x",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=t1,
        plan_observed_at=t1,
    )
    identities = db.list_cpamp_snapshot_identities(cpamp.id)
    assert len(identities) == 1
    assert identities[0].plan == "Pro 20x"
    assert identities[0].plan_observed_at == t1


def test_stored_cpamp_account_rediscovery_threads_strong_plan_observed_at(
    temp_data_dir,
):
    """The stored-account fallback + discovery conversion must carry
    plan_observed_at end-to-end so rediscovery preserves the strong plan."""
    from app.quota_sync import _cpamp_discovery_account, _stored_cpamp_accounts

    cpamp = db.create_cpamp_channel(
        name="CPAMP",
        base_url="https://cpamp.example.test",
        management_key="secret",
    )
    account_hash = "hmac:v1:cpamp-account"
    display = "b***@example.test"
    t1 = _plan_ts(datetime.now(UTC), 0)
    db.prepare_cpamp_channel_discovery(
        cpamp.id, [(account_hash, None, display, "Plus")]
    )
    db.record_cpamp_quota_snapshot(
        cpamp.id,
        account_hash,
        account_display=display,
        plan="Pro 20x",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 80}],
        observed_at=t1,
        plan_observed_at=t1,
    )
    stored = _stored_cpamp_accounts(cpamp.id)
    assert len(stored) == 1
    assert stored[0].plan == "Pro 20x"
    assert stored[0].plan_observed_at == t1
    rediscovery = _cpamp_discovery_account(stored[0])
    assert rediscovery.plan == "Pro 20x"
    assert rediscovery.plan_observed_at == t1


def test_cpa_account_persists_masked_credentials_only(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    raw_name = "codex-account-sensitive.json"
    raw_project_id = "proj-secret-1234567890"
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash="hmac:v1:cpa-account-1",
                legacy_account_key_hashes=(),
                locator_hash="hmac:v1:locator-1",
                subject_hash="hmac:v1:subject-1",
                account_display="a***@example.test",
                plan="Plus",
                auth_file_masked="co***e.json",
                auth_tag="#a3f9c1",
                provider="codex",
                project_id_masked="pr***90",
            )
        ],
        source_mode="native_queue",
    )
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT auth_file_masked, auth_tag, provider, project_id_masked "
            "FROM cpa_accounts WHERE channel_id = ?",
            (channel.id,),
        ).fetchone()
        assert row["auth_file_masked"] == "co***e.json"
        assert row["auth_tag"] == "#a3f9c1"
        assert row["provider"] == "codex"
        assert row["project_id_masked"] == "pr***90"
        # Sentinel: cpa_accounts has no raw-identity columns.
        cols = {col[1] for col in conn.execute("PRAGMA table_info(cpa_accounts)")}
        assert "auth_index" not in cols
        assert "note" not in cols
        assert "label" not in cols
        assert "file_name" not in cols
        assert "status_message" not in cols
        # Sentinel: raw values are not present in any stored text.
        blob = conn.execute(
            "SELECT auth_file_masked || '|' || auth_tag || '|' || provider || '|' || "
            "project_id_masked || '|' || account_display || '|' || plan "
            "FROM cpa_accounts WHERE channel_id = ?",
            (channel.id,),
        ).fetchone()[0]
        assert raw_name not in blob
        assert raw_project_id not in blob


def test_list_cached_cpa_channels_credential_details_isolation(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://cpa.example.test",
        management_key="secret",
        quota_source="native_queue",
        confirm_exclusive=True,
    )
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            db.CPADiscoveryAccount(
                account_key_hash="hmac:v1:cpa-account-1",
                legacy_account_key_hashes=(),
                locator_hash="hmac:v1:locator-1",
                subject_hash="hmac:v1:subject-1",
                account_display="a***@example.test",
                plan="Plus",
                auth_file_masked="co***e.json",
                auth_tag="#a3f9c1",
                provider="codex",
                project_id_masked="pr***90",
            )
        ],
        source_mode="native_queue",
    )
    # Default (public) view: the four credential keys are entirely absent.
    default_item = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"][0]
    for key in ("auth_file_masked", "auth_tag", "provider", "project_id_masked"):
        assert key not in default_item
    # Admin view: the four keys are always present, with no raw identity.
    admin_item = db.list_cached_cpa_channels(
        enabled_only=False, include_credential_details=True
    )[0]["accounts"][0]
    assert admin_item["auth_file_masked"] == "co***e.json"
    assert admin_item["auth_tag"] == "#a3f9c1"
    assert admin_item["provider"] == "codex"
    assert admin_item["project_id_masked"] == "pr***90"
    for key in ("auth_file_name", "auth_index", "note", "label", "fileName"):
        assert key not in admin_item


def test_init_db_adds_credential_columns_to_legacy_cpa_accounts(
    monkeypatch, tmp_path
):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("QUOTAHUB_DATA", str(data))
    monkeypatch.setenv(
        "QUOTAHUB_ADMIN_TOKEN", "test-admin-token-with-at-least-32-characters"
    )
    monkeypatch.setenv(
        "QUOTAHUB_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii")
    )
    # Build a legacy schema without the M6 credential columns.
    with sqlite3.connect(data / "quotahub.db") as conn:
        conn.execute(
            """
            CREATE TABLE cpa_channels (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, base_url TEXT NOT NULL,
                management_key TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                collection_revision INTEGER NOT NULL DEFAULT 1,
                interval_sec INTEGER NOT NULL DEFAULT 300, last_attempt_at TEXT,
                last_success_at TEXT, last_attempt_status TEXT,
                stale INTEGER NOT NULL DEFAULT 0, error TEXT,
                public_id TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE cpa_accounts (
                channel_id TEXT NOT NULL REFERENCES cpa_channels(id) ON DELETE CASCADE,
                canonical_account_hash TEXT NOT NULL, public_id TEXT NOT NULL UNIQUE,
                account_display TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT '未知套餐',
                plan_observed_at TEXT, locator_hash TEXT, subject_hash TEXT,
                visible INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (channel_id, canonical_account_hash)
            )
            """
        )
        conn.execute(
            "INSERT INTO cpa_channels (id, name, base_url, management_key, public_id, "
            "created_at, updated_at) VALUES ('ch-1', 'CPA', 'https://x', 'k', 'pub-ch', "
            "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO cpa_accounts (channel_id, canonical_account_hash, public_id, "
            "account_display, plan, visible, created_at, updated_at) VALUES "
            "('ch-1', 'hash-1', 'pub-1', 'legacy-display', 'Plus', 1, "
            "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )
    # init_db must idempotently add the four credential columns and keep the row.
    db.init_db()
    with sqlite3.connect(data / "quotahub.db") as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(cpa_accounts)")}
        assert {
            "auth_file_masked",
            "auth_tag",
            "provider",
            "project_id_masked",
        } <= cols
        row = conn.execute(
            "SELECT account_display, plan, auth_file_masked, auth_tag, provider, "
            "project_id_masked FROM cpa_accounts WHERE public_id = 'pub-1'"
        ).fetchone()
        assert row[0] == "legacy-display"  # legacy data preserved
        assert row[1] == "Plus"  # legacy data preserved
        assert row[2] is None  # new columns NULL for legacy rows
        assert row[3] is None
        assert row[4] is None
        assert row[5] is None
    # Re-running init_db is a no-op (idempotent migration).
    db.init_db()
