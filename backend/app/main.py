from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_config, mask_cookie, mask_ollama_cookie
from .ollama_quota import fetch_all_ollama_quotas
from .quota import fetch_all_quotas

app = FastAPI(title="QuotaHub", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/quota")
async def quota() -> list[dict]:
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return await fetch_all_quotas(cfg.opencode_accounts)


@app.get("/api/ollama/quota")
async def ollama_quota() -> list[dict]:
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return await fetch_all_ollama_quotas(cfg.ollama_accounts)


@app.get("/api/config")
async def config_status() -> dict:
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "refresh": {
            "ollama": {
                "auto_refresh": cfg.refresh_ollama.auto_refresh,
                "interval_sec": cfg.refresh_ollama.interval_sec,
            },
            "opencode_go": {
                "auto_refresh": cfg.refresh_opencode_go.auto_refresh,
                "interval_sec": cfg.refresh_opencode_go.interval_sec,
            },
        },
        "opencode_accounts": [
            {
                "name": account.name,
                "workspace_id": account.workspace_id,
                "auth_cookie_masked": mask_cookie(account.auth_cookie),
                "configured": bool(account.auth_cookie.strip()),
                "show_rolling": account.show_rolling,
                "show_weekly": account.show_weekly,
                "show_monthly": account.show_monthly,
            }
            for account in cfg.opencode_accounts
        ],
        "ollama_accounts": [
            {
                "name": account.name,
                "session_cookie_masked": mask_ollama_cookie(account.session_cookie),
                "configured": bool(account.session_cookie.strip()),
                "show_session": account.show_session,
                "show_weekly": account.show_weekly,
            }
            for account in cfg.ollama_accounts
        ],
    }


if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        static_file = (FRONTEND_DIST / full_path).resolve()
        try:
            static_file.relative_to(FRONTEND_DIST.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404) from exc
        if static_file.is_file():
            return FileResponse(static_file)
        index = FRONTEND_DIST / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404)
        return FileResponse(index)


def run() -> None:
    import uvicorn

    cfg = load_config()
    uvicorn.run(
        "app.main:app",
        host=cfg.listen_host,
        port=cfg.listen_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
