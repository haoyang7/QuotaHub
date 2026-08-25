from datetime import UTC, datetime

import pytest

from app.ollama_quota import build_ollama_cookie_header, parse_ollama_quota_html
from app.quota_sync import _safe_error


def test_build_ollama_cookie_header_raw_value():
    assert build_ollama_cookie_header("abc123") == "__Secure-session=abc123"


def test_build_ollama_cookie_header_full_cookie():
    cookie = "aid=x; __Secure-session=token123"
    assert build_ollama_cookie_header(cookie) == cookie


def test_parse_ollama_quota_html():
    html = """
    <span>Cloud usage</span>
    <span class="text-xs font-normal px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600 capitalize">pro</span>
    <div class="flex justify-between mb-2">
      <span class="text-sm text-neutral-400">Session usage</span>
      <span class="text-sm text-neutral-500">Weekly limit reached</span>
    </div>
    <div data-usage-track aria-label="Session usage 12.5% used"></div>
    <div class="local-time" data-time="2026-06-29T00:00:00Z">Sessions resume in 3 days.</div>
    <div class="flex justify-between mb-2">
      <span class="text-sm">Weekly usage</span>
      <span class="text-sm text-red-500">80% used</span>
    </div>
    <div data-usage-track aria-label="Weekly usage 80% used">
      <button data-usage-segment data-model="glm-5.2" data-requests="100" style="width: 80%; background: #3b82f6"></button>
    </div>
    <div class="local-time" data-time="2026-06-30T00:00:00Z">Resets in 4 days.</div>
    <script>
    """
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=UTC)
    plan, windows = parse_ollama_quota_html(html, now)
    assert plan == "pro"
    assert len(windows) == 2
    assert windows[0].label == "Session"
    assert windows[0].used == 12.5
    assert windows[0].status_text == "Weekly limit reached"
    assert windows[1].used == 80.0
    assert windows[1].models and windows[1].models[0].model == "glm-5.2"


def test_parse_ollama_quota_html_with_section_wrapper():
    html = """
    <section>
      <span class="font-medium">Cloud usage</span>
      <span class="rounded-full capitalize">pro</span>
      <div class="flex justify-between mb-2">
        <span class="text-sm text-neutral-400">Session usage</span>
        <span class="text-sm text-neutral-500">0.8% used</span>
      </div>
      <div data-usage-track aria-label="Session usage 0.8% used">
        <button data-usage-segment data-model="glm-5.2" data-requests="3" style="width: 100%"></button>
      </div>
      <div class="local-time" data-time="2026-08-25T15:00:00Z">Resets soon.</div>
      <div class="flex justify-between mb-2">
        <span class="text-sm text-neutral-400">Weekly usage</span>
        <span class="text-sm text-neutral-500">16.1% used</span>
      </div>
      <div data-usage-track aria-label="Weekly usage 16.1% used">
        <button data-usage-segment data-model="glm-5.2" data-requests="402" style="width: 100%"></button>
      </div>
      <div class="local-time" data-time="2026-08-31T00:00:00Z">Resets later.</div>
    </section>
    <script type="module">
    """
    now = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
    plan, windows = parse_ollama_quota_html(html, now)

    assert plan == "pro"
    assert [window.label for window in windows] == ["Session", "Weekly"]
    assert [window.used for window in windows] == [0.8, 16.1]
    assert [len(window.models or []) for window in windows] == [1, 1]
    assert all(window.reset_at for window in windows)


def test_changed_page_structure_is_not_reported_as_authentication_failure():
    with pytest.raises(ValueError) as exc_info:
        parse_ollama_quota_html("<html><body>Cloud usage moved</body></html>", datetime.now(UTC))

    assert _safe_error(exc_info.value) == "额度采集失败"
