from datetime import UTC, datetime

from app.quota import build_cookie_header, parse_quota_html


def test_build_cookie_header_raw_value():
    assert build_cookie_header("abc123") == "auth=abc123"


def test_build_cookie_header_full_cookie():
    assert build_cookie_header("auth=token123; other=x") == "auth=token123"


def test_parse_quota_html():
    html = """
    rollingUsage: $R[0] = { usagePercent: 12.5, resetInSec: 3600 }
    weeklyUsage: $R[0] = { usagePercent: 40, resetInSec: 86400 }
    monthlyUsage: $R[0] = { usagePercent: 75.2, resetInSec: 1209600 }
    """
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=UTC)
    windows = parse_quota_html(html, now)
    assert len(windows) == 3
    assert windows[0].label == "5h Rolling"
    assert windows[0].used == 12.5
    assert windows[1].used == 40
    assert windows[2].used == 75.2
