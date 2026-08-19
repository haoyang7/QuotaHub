from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import httpx
import pytest

from app import db
from app.cpa_quota import (
    CPAAuthAccount,
    discover_cpa_accounts,
    map_cpa_plan,
    mask_cpa_account,
    normalize_cpa_url,
    parse_auth_files,
    parse_cpa_usage_payload,
)
from app.quota import LABEL_ROLLING, LABEL_WEEKLY


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("free", "Free"),
        ("plus", "Plus"),
        ("prolite", "Pro 5x"),
        ("pro-lite", "Pro 5x"),
        ("pro_5x", "Pro 5x"),
        ("pro", "Pro 20x"),
        ("pro-20x", "Pro 20x"),
        ("team", "未知套餐"),
    ],
)
def test_cpa_plan_mapping(raw: str, expected: str):
    assert map_cpa_plan(raw) == expected


def test_cpa_url_and_account_masking():
    assert normalize_cpa_url(" HTTPS://proxy.example.com/root/ ") == (
        "https://proxy.example.com/root"
    )
    assert mask_cpa_account("alice@example.com") == "a***@example.com"
    assert mask_cpa_account("acct_123456789") == "ac***89"
    with pytest.raises(ValueError):
        normalize_cpa_url("proxy.example.com")
    with pytest.raises(ValueError):
        normalize_cpa_url("https://user:pass@proxy.example.com")


def test_parse_auth_files_filters_non_codex_and_disabled_without_leaking_identifiers(
    temp_data_dir,
):
    raw_email = "alice@example.com"
    raw_auth_index = "codex-auth-index-sensitive"
    accounts = parse_auth_files(
        {
            "files": [
                {
                    "provider": "codex",
                    "auth_index": raw_auth_index,
                    "name": "codex-account.json",
                    "email": raw_email,
                    "account_type": "prolite",
                },
                {"provider": "codex", "auth_index": "disabled", "disabled": True},
                {"provider": "claude", "auth_index": "other"},
            ]
        }
    )
    assert len(accounts) == 1
    account = accounts[0]
    assert account.account_display == "a***@example.com"
    assert account.plan == "Pro 5x"
    assert account.auth_index == raw_auth_index
    assert account.auth_file_name == "codex-account.json"
    assert account.account_key_hash.startswith("hmac:v1:")
    assert account.legacy_account_key_hash == hashlib.sha256(
        raw_auth_index.encode("utf-8")
    ).hexdigest()
    assert raw_auth_index not in account.account_key_hash
    assert raw_email not in account.account_display


@pytest.mark.parametrize(
    ("plan_type", "expected"),
    [
        ("free", "Free"),
        ("plus", "Plus"),
        ("prolite", "Pro 5x"),
        ("pro", "Pro 20x"),
    ],
)
def test_parse_auth_files_prefers_cli_proxy_id_token_plan_over_oauth_kind(
    temp_data_dir, plan_type: str, expected: str
):
    account = parse_auth_files(
        {
            "files": [
                {
                    "provider": "codex",
                    "auth_index": f"auth-{plan_type}",
                    "account_type": "oauth",
                    "id_token": {
                        "chatgpt_account_id": "acct-sanitized",
                        "plan_type": plan_type,
                    },
                }
            ]
        }
    )[0]
    assert account.plan == expected


def test_legacy_cpa_sha_fingerprint_migrates_without_losing_snapshot(temp_data_dir):
    auth_index = "legacy-auth-index"
    old_hash = hashlib.sha256(auth_index.encode("utf-8")).hexdigest()
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="management-secret",
    )
    db.record_cpa_quota_snapshot(
        channel.id,
        old_hash,
        account_display="l***@example.com",
        plan="Plus",
        success=True,
        windows=[{"label": "5h Rolling", "remaining": 75}],
    )
    before = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"][0]
    account = parse_auth_files(
        {
            "files": [
                {
                    "provider": "codex",
                    "auth_index": auth_index,
                    "email": "legacy@example.com",
                    "account_type": "plus",
                }
            ]
        }
    )[0]
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            (
                account.account_key_hash,
                account.legacy_account_key_hash,
                account.account_display,
                account.plan,
            )
        ],
    )
    after = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"][0]
    assert after["public_id"] == before["public_id"]
    assert after["windows"] == before["windows"]


def test_same_auth_index_with_changed_account_subject_gets_new_public_identity(
    temp_data_dir,
):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="management-secret",
    )

    def parse(subject: str) -> CPAAuthAccount:
        return parse_auth_files(
            {
                "files": [
                    {
                        "provider": "codex",
                        "auth_index": "same-path-auth-index",
                        "name": "same-file.json",
                        "email": "same@example.com",
                        "id_token": {
                            "chatgpt_account_id": subject,
                            "plan_type": "plus",
                        },
                    }
                ]
            }
        )[0]

    first = parse("subject-a")
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            (
                first.account_key_hash,
                (first.previous_account_key_hash, first.legacy_account_key_hash),
                first.account_display,
                first.plan,
            )
        ],
    )
    first_public_id = db.list_cached_cpa_channels(enabled_only=False)[0]["accounts"][0][
        "public_id"
    ]

    replacement = parse("subject-b")
    db.prepare_cpa_channel_discovery(
        channel.id,
        [
            (
                replacement.account_key_hash,
                (
                    replacement.previous_account_key_hash,
                    replacement.legacy_account_key_hash,
                ),
                replacement.account_display,
                replacement.plan,
            )
        ],
    )
    replacement_public_id = db.list_cached_cpa_channels(enabled_only=False)[0][
        "accounts"
    ][0]["public_id"]
    assert replacement_public_id != first_public_id
    raw_db = db.db_path().read_bytes()
    assert b"subject-a" not in raw_db
    assert b"subject-b" not in raw_db


def test_parse_usage_items_response_metadata_quota_windows():
    now = datetime(2026, 8, 11, 8, 0, tzinfo=UTC)
    windows = parse_cpa_usage_payload(
        {
            "items": [
                {
                    "response_metadata": {
                        "quota": {
                            "primary": {
                                "used_percent": 12.5,
                                "reset_after_seconds": 1800,
                                "limit_window_seconds": 18000,
                            },
                            "secondary": {
                                "used_percent": 40,
                                "reset_at": "2026-08-16T08:00:00Z",
                                "limit_window_seconds": 604800,
                            },
                        }
                    }
                }
            ]
        },
        now=now,
    )
    assert [window["label"] for window in windows] == [
        LABEL_ROLLING,
        LABEL_WEEKLY,
    ]
    assert windows[0]["remaining"] == 87.5
    assert windows[0]["reset_in_sec"] == 1800


@pytest.mark.asyncio
async def test_cpa_protocol_only_discovers_accounts(temp_data_dir):
    channel = db.create_cpa_channel(
        name="CPA",
        base_url="https://proxy.example.com",
        management_key="management-secret",
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.method == "GET"
        assert request.url.path == "/v0/management/auth-files"
        assert request.headers["authorization"] == "Bearer management-secret"
        return httpx.Response(
            200,
            json={
                "files": [
                    {
                        "provider": "codex",
                        "auth_index": "auth-1",
                        "name": "codex-auth.json",
                        "email": "person@example.com",
                        "account_type": "plus",
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        accounts = await discover_cpa_accounts(channel, client)

    assert len(seen) == 1
    assert accounts[0].account_display == "p***@example.com"
