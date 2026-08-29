from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.cpa_quota import parse_auth_files
from app.cpa_queue import parse_codex_quota_signals
from app.cpamp_quota import parse_cpamp_auth_files
from app.quota import LABEL_MONTHLY, LABEL_ROLLING, LABEL_WEEKLY

OBSERVED_AT = "2026-08-15T01:00:00Z"


def _base_signals(
    *,
    primary_used: str = "25",
    primary_minutes: str = "300",
    primary_reset_after: str = "1800",
    secondary_used: str = "40",
    secondary_minutes: str = "10080",
    secondary_reset_after: str = "3600",
    plan_type: str | None = "prolite",
) -> dict[str, str]:
    signals: dict[str, str] = {
        "x-codex-primary-used-percent": primary_used,
        "x-codex-primary-window-minutes": primary_minutes,
        "x-codex-primary-reset-after-seconds": primary_reset_after,
        "x-codex-secondary-used-percent": secondary_used,
        "x-codex-secondary-window-minutes": secondary_minutes,
        "x-codex-secondary-reset-after-seconds": secondary_reset_after,
    }
    if plan_type is not None:
        signals["x-codex-plan-type"] = plan_type
    return signals


@pytest.mark.parametrize(
    ("window_minutes", "expected_label"),
    [
        ("300", LABEL_ROLLING),
        ("10080", LABEL_WEEKLY),
        ("43200", LABEL_MONTHLY),
    ],
)
def test_base_primary_window_label_follows_window_minutes(
    window_minutes: str, expected_label: str
):
    signals = {
        "x-codex-primary-used-percent": "25",
        "x-codex-primary-window-minutes": window_minutes,
        "x-codex-primary-reset-after-seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert len(windows) == 1
    assert windows[0]["label"] == expected_label
    assert windows[0]["used"] == 25.0
    assert windows[0]["remaining"] == 75.0
    assert windows[0]["unit"] == "%"
    assert windows[0]["reset_at"] == "2026-08-15T01:30:00Z"
    assert windows[0]["reset_in_sec"] == 1800
    assert windows[0]["duration_sec"] == int(window_minutes) * 60


def test_base_primary_and_secondary_produce_two_windows():
    windows = parse_codex_quota_signals(_base_signals(), OBSERVED_AT)
    assert [w["label"] for w in windows] == [LABEL_ROLLING, LABEL_WEEKLY]
    assert windows[0]["used"] == 25.0
    assert windows[1]["used"] == 40.0
    # Labels are ordered rolling -> weekly -> monthly.
    assert windows[0]["reset_in_sec"] == 1800
    assert windows[1]["reset_in_sec"] == 3600


def test_reset_at_timestamp_is_derived_from_reset_after_when_reset_at_absent():
    signals = {
        "x-codex-primary-used-percent": "25",
        "x-codex-primary-window-minutes": "300",
        "x-codex-primary-reset-after-seconds": "1800",
    }
    window = parse_codex_quota_signals(signals, OBSERVED_AT)[0]
    assert window["reset_at"] == "2026-08-15T01:30:00Z"


def test_reset_at_header_takes_precedence_and_recomputes_reset_in_sec():
    signals = {
        "x-codex-primary-used-percent": "25",
        "x-codex-primary-window-minutes": "300",
        "x-codex-primary-reset-at": "2026-08-15T02:00:00Z",
    }
    window = parse_codex_quota_signals(signals, OBSERVED_AT)[0]
    assert window["reset_at"] == "2026-08-15T02:00:00Z"
    assert window["reset_in_sec"] == 3600


def test_http_spelling_additional_namespace_produces_monthly_window():
    signals = {
        "x-codex-bengalfox-primary-used-percent": "50",
        "x-codex-bengalfox-primary-window-minutes": "43200",
        "x-codex-bengalfox-primary-reset-after-seconds": "3600",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert [w["label"] for w in windows] == [LABEL_MONTHLY]
    assert windows[0]["used"] == 50.0


def test_websocket_spelling_additional_namespace_produces_monthly_window():
    signals = {
        "x-codex-additional-my-limit-primary-used-percent": "30",
        "x-codex-additional-my-limit-primary-window-minutes": "43200",
        "x-codex-additional-my-limit-primary-reset-after-seconds": "3600",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert [w["label"] for w in windows] == [LABEL_MONTHLY]
    assert windows[0]["used"] == 30.0


def test_base_namespace_wins_label_conflict_against_additional():
    signals = {
        "x-codex-primary-used-percent": "10",
        "x-codex-primary-window-minutes": "300",
        "x-codex-primary-reset-after-seconds": "1800",
        "x-codex-bengalfox-primary-used-percent": "20",
        "x-codex-bengalfox-primary-window-minutes": "300",
        "x-codex-bengalfox-primary-reset-after-seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert len(windows) == 1
    assert windows[0]["used"] == 10.0


def test_active_limit_namespace_wins_over_non_active_when_base_absent():
    signals = {
        "x-codex-active-limit": "bengalfox",
        "x-codex-bengalfox-primary-used-percent": "30",
        "x-codex-bengalfox-primary-window-minutes": "300",
        "x-codex-bengalfox-primary-reset-after-seconds": "1800",
        "x-codex-foxcat-primary-used-percent": "50",
        "x-codex-foxcat-primary-window-minutes": "300",
        "x-codex-foxcat-primary-reset-after-seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert len(windows) == 1
    assert windows[0]["used"] == 30.0


def test_active_limit_codex_prefixed_namespace_wins_for_http_signal_names():
    signals = {
        "x-codex-active-limit": "codex_bengalfox",
        "x-codex-bengalfox-primary-used-percent": "30",
        "x-codex-bengalfox-primary-window-minutes": "300",
        "x-codex-bengalfox-primary-reset-after-seconds": "1800",
        "x-codex-foxcat-primary-used-percent": "50",
        "x-codex-foxcat-primary-window-minutes": "300",
        "x-codex-foxcat-primary-reset-after-seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert len(windows) == 1
    assert windows[0]["used"] == 30.0


def test_window_flags_are_preserved_from_namespace_signal_headers():
    signals = {
        "x-codex-bengalfox-primary-used-percent": "30",
        "x-codex-bengalfox-primary-window-minutes": "300",
        "x-codex-bengalfox-primary-reset-after-seconds": "1800",
        "x-codex-bengalfox-allowed": "false",
        "x-codex-bengalfox-limit-reached": "true",
    }
    window = parse_codex_quota_signals(signals, OBSERVED_AT)[0]
    assert window["allowed"] is False
    assert window["limit_reached"] is True


def test_code_review_namespace_is_ignored():
    signals = {
        "x-codex-code-review-primary-used-percent": "99",
        "x-codex-code-review-primary-window-minutes": "300",
        "x-codex-code-review-primary-reset-after-seconds": "1800",
        "x-codex-primary-used-percent": "25",
        "x-codex-primary-window-minutes": "300",
        "x-codex-primary-reset-after-seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert [w["used"] for w in windows] == [25.0]


def test_missing_window_minutes_drops_that_window_only():
    signals = {
        "x-codex-primary-used-percent": "25",
        "x-codex-primary-reset-after-seconds": "1800",
        "x-codex-secondary-used-percent": "40",
        "x-codex-secondary-window-minutes": "10080",
        "x-codex-secondary-reset-after-seconds": "3600",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert [w["label"] for w in windows] == [LABEL_WEEKLY]


def test_non_positive_window_minutes_drops_that_window():
    signals = {
        "x-codex-primary-used-percent": "25",
        "x-codex-primary-window-minutes": "0",
        "x-codex-primary-reset-after-seconds": "1800",
    }
    assert parse_codex_quota_signals(signals, OBSERVED_AT) == []


def test_missing_both_reset_fields_drops_window():
    signals = {
        "x-codex-primary-used-percent": "25",
        "x-codex-primary-window-minutes": "300",
        "x-codex-secondary-used-percent": "40",
        "x-codex-secondary-window-minutes": "10080",
        "x-codex-secondary-reset-after-seconds": "3600",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert [w["label"] for w in windows] == [LABEL_WEEKLY]


def test_remaining_percent_fills_used_when_used_percent_not_numeric():
    # A non-numeric used-percent survives _header_values but _number() returns
    # None, so _parse_window falls back to 100 - remaining-percent.
    signals = {
        "x-codex-primary-used-percent": "n/a",
        "x-codex-primary-remaining-percent": "75",
        "x-codex-primary-window-minutes": "300",
        "x-codex-primary-reset-after-seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert len(windows) == 1
    assert windows[0]["used"] == 25.0
    assert windows[0]["remaining"] == 75.0


def test_used_percent_absent_and_only_remaining_present_is_not_enumerated():
    # Enumeration is keyed on *-used-percent; a window with only
    # remaining-percent and no used-percent key is not emitted.
    signals = {
        "x-codex-primary-remaining-percent": "75",
        "x-codex-primary-window-minutes": "300",
        "x-codex-primary-reset-after-seconds": "1800",
    }
    assert parse_codex_quota_signals(signals, OBSERVED_AT) == []


def test_canonical_header_keys_are_lowercased_before_matching():
    signals = {
        "X-Codex-Plan-Type": "prolite",
        "X-Codex-Primary-Used-Percent": "25",
        "X-Codex-Primary-Window-Minutes": "300",
        "X-Codex-Primary-Reset-After-Seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert len(windows) == 1
    assert windows[0]["used"] == 25.0


def test_empty_signals_returns_empty_list():
    assert parse_codex_quota_signals({}, OBSERVED_AT) == []


def test_invalid_observation_timestamp_returns_empty_list():
    assert parse_codex_quota_signals(
        {
            "x-codex-primary-used-percent": "25",
            "x-codex-primary-window-minutes": "300",
            "x-codex-primary-reset-after-seconds": "1800",
        },
        "not-a-timestamp",
    ) == []


def test_signals_without_window_keys_returns_empty_list():
    assert parse_codex_quota_signals({"x-codex-plan-type": "pro"}, OBSERVED_AT) == []


def test_used_percent_clamped_to_unit_interval():
    signals = {
        "x-codex-primary-used-percent": "150",
        "x-codex-primary-window-minutes": "300",
        "x-codex-primary-reset-after-seconds": "1800",
    }
    windows = parse_codex_quota_signals(signals, OBSERVED_AT)
    assert windows[0]["used"] == 100.0
    assert windows[0]["remaining"] == 0.0


def _auth_file_entry(
    *,
    quota: dict[str, object] | None = ...,
    account_type: str = "plus",
) -> dict[str, object]:
    entry: dict[str, object] = {
        "provider": "codex",
        "auth_index": "auth-1",
        "name": "account.json",
        "email": "person@example.test",
        "account_type": account_type,
    }
    if quota is not ...:
        entry["quota"] = quota
    return entry


def test_parse_auth_files_preserves_quota_observed_at_and_signals(temp_data_dir):
    quota = {
        "observed_at": OBSERVED_AT,
        "signals": {
            "X-Codex-Plan-Type": "pro",
            "X-Codex-Primary-Used-Percent": "25",
            "X-Codex-Primary-Window-Minutes": "300",
            "X-Codex-Primary-Reset-After-Seconds": "1800",
        },
    }
    account = parse_auth_files({"files": [_auth_file_entry(quota=quota)]})[0]
    assert account.quota_observed_at == OBSERVED_AT
    assert account.quota_signals["x-codex-plan-type"] == "pro"
    assert account.quota_signals["x-codex-primary-used-percent"] == "25"
    # signals plan-type overrides the id_token/entry plan.
    assert account.plan == "Pro 20x"


def test_parse_auth_files_keeps_id_token_plan_when_signals_have_no_plan_type(
    temp_data_dir,
):
    quota = {
        "observed_at": OBSERVED_AT,
        "signals": {
            "X-Codex-Primary-Used-Percent": "25",
            "X-Codex-Primary-Window-Minutes": "300",
            "X-Codex-Primary-Reset-After-Seconds": "1800",
        },
    }
    account = parse_auth_files({"files": [_auth_file_entry(quota=quota)]})[0]
    assert account.quota_observed_at == OBSERVED_AT
    assert "x-codex-plan-type" not in account.quota_signals
    assert account.plan == "Plus"


def test_parse_auth_files_without_quota_yields_empty_fields(temp_data_dir):
    account = parse_auth_files({"files": [_auth_file_entry(quota=None)]})[0]
    assert account.quota_observed_at == ""
    assert account.quota_signals == {}
    assert account.plan == "Plus"


def test_parse_auth_files_non_dict_quota_yields_empty_fields(temp_data_dir):
    entry = _auth_file_entry()
    entry["quota"] = "not-a-dict"
    account = parse_auth_files({"files": [entry]})[0]
    assert account.quota_observed_at == ""
    assert account.quota_signals == {}


def test_parse_auth_files_unparseable_observed_at_falls_back_to_empty(temp_data_dir):
    quota = {
        "observed_at": "not-a-timestamp",
        "signals": {
            "X-Codex-Primary-Used-Percent": "25",
            "X-Codex-Primary-Window-Minutes": "300",
            "X-Codex-Primary-Reset-After-Seconds": "1800",
        },
    }
    account = parse_auth_files({"files": [_auth_file_entry(quota=quota)]})[0]
    assert account.quota_observed_at == ""
    assert account.quota_signals["x-codex-primary-used-percent"] == "25"


def test_cpamp_parse_auth_files_propagates_quota_fields(temp_data_dir):
    quota = {
        "observed_at": OBSERVED_AT,
        "signals": {
            "X-Codex-Plan-Type": "pro",
            "X-Codex-Primary-Used-Percent": "25",
            "X-Codex-Primary-Window-Minutes": "300",
            "X-Codex-Primary-Reset-After-Seconds": "1800",
        },
    }
    payload = {
        "files": [
            {
                "provider": "codex",
                "auth_index": "auth-1",
                "name": "account.json",
                "email": "person@example.test",
                "account_type": "plus",
                "quota": quota,
            }
        ]
    }
    account = parse_cpamp_auth_files(payload)[0]
    assert account.quota_observed_at == OBSERVED_AT
    assert account.quota_signals["x-codex-plan-type"] == "pro"
    assert account.plan == "Pro 20x"


def test_cpamp_parse_auth_files_without_quota_yields_empty_fields(temp_data_dir):
    payload = {
        "files": [
            {
                "provider": "codex",
                "auth_index": "auth-1",
                "name": "account.json",
                "email": "person@example.test",
                "account_type": "plus",
            }
        ]
    }
    account = parse_cpamp_auth_files(payload)[0]
    assert account.quota_observed_at == ""
    assert account.quota_signals == {}


def test_parse_codex_quota_signals_consumes_account_signals_round_trip(temp_data_dir):
    """A signals dict stored on an account round-trips through the window parser."""
    raw_signals = {
        "X-Codex-Plan-Type": "prolite",
        "X-Codex-Primary-Used-Percent": "25",
        "X-Codex-Primary-Window-Minutes": "300",
        "X-Codex-Primary-Reset-After-Seconds": "1800",
        "X-Codex-Secondary-Used-Percent": "40",
        "X-Codex-Secondary-Window-Minutes": "10080",
        "X-Codex-Secondary-Reset-After-Seconds": "3600",
    }
    account = parse_auth_files(
        {
            "files": [
                {
                    "provider": "codex",
                    "auth_index": "auth-1",
                    "name": "account.json",
                    "email": "person@example.test",
                    "account_type": "plus",
                    "quota": {"observed_at": OBSERVED_AT, "signals": raw_signals},
                }
            ]
        }
    )[0]
    windows = parse_codex_quota_signals(account.quota_signals, account.quota_observed_at)
    assert [w["label"] for w in windows] == [LABEL_ROLLING, LABEL_WEEKLY]
    assert windows[0]["used"] == 25.0
    assert windows[1]["used"] == 40.0
