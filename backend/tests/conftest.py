from pathlib import Path

import pytest

from app import db


@pytest.fixture()
def temp_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    config = data / "config.json"
    config.write_text(
        '{"listen_host":"127.0.0.1","listen_port":8788,"refresh":{}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("QUOTAHUB_CONFIG", str(config))
    db.init_db()
    yield data
