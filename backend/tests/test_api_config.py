from fastapi.testclient import TestClient

from app.main import app


def test_update_config_readonly_base(temp_data_dir):
    client = TestClient(app)
    config = temp_data_dir / "config.json"
    config.chmod(0o444)

    resp = client.put(
        "/api/config",
        json={
            "refresh": {
                "ollama": {"auto_refresh": False, "interval_sec": 120},
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json()["refresh"]["ollama"]["auto_refresh"] is False
    assert resp.json()["refresh"]["ollama"]["interval_sec"] == 120

    runtime = temp_data_dir / "service.json"
    assert runtime.exists()
    assert config.read_text(encoding="utf-8") == '{"listen_host":"127.0.0.1","listen_port":8788,"refresh":{}}'

    config.chmod(0o644)

    client = TestClient(app)
    resp = client.put(
        "/api/config",
        json={
            "refresh": {
                "ollama": {"auto_refresh": False, "interval_sec": 120},
                "opencode_go": {"auto_refresh": True, "interval_sec": 90},
            },
            "usage_sync": {
                "auto_sync": False,
                "interval_sec": 600,
                "backfill_pages_per_request": 3,
                "max_pages_per_incremental": 8,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["refresh"]["ollama"]["auto_refresh"] is False
    assert data["refresh"]["ollama"]["interval_sec"] == 120
    assert data["refresh"]["opencode_go"]["interval_sec"] == 90
    assert data["usage_sync"]["auto_sync"] is False
    assert data["usage_sync"]["backfill_pages_per_request"] == 3

    get_resp = client.get("/api/config")
    assert get_resp.json()["usage_sync"]["max_pages_per_incremental"] == 8
