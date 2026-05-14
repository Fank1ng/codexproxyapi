"""Codex Account Pool Proxy — main entry point.

Start with: python3 proxy.py
Web UI:      http://127.0.0.1:8800/app
"""

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

from aiohttp import web

from account_manager import ACCOUNTS_DIR, Account, AccountPool
from config import CONFIG_DIR, load, save, get
from proxy_core import handle as proxy_handle
from quota_tracker import run as quota_run

CODE_CLI = "/Applications/Codex.app/Contents/Resources/codex"

# ── Setup ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, str(get("log_level")).upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("proxy")

pool = AccountPool()

STATIC_DIR = CONFIG_DIR / "static"


# ── Management API ─────────────────────────────────────────────────────

async def api_accounts(request: web.Request) -> web.Response:
    """GET /api/accounts — list all accounts."""
    return web.json_response([a.to_dict() for a in pool.accounts])


async def api_accounts_add(request: web.Request) -> web.Response:
    """POST /api/accounts/add — return the codex login command for a new account."""
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name or "/" in name or ".." in name:
        return web.json_response({"error": "invalid name"}, status=400)

    target_dir = ACCOUNTS_DIR / name
    if target_dir.exists():
        return web.json_response({"error": "account already exists"}, status=409)

    target_dir.mkdir(parents=True, exist_ok=True)
    cmd = f'CODEX_HOME={target_dir} {CODE_CLI} login'
    return web.json_response({
        "command": cmd,
        "hint": "Run this in your terminal, then refresh accounts.",
        "account_dir": str(target_dir),
    })


async def api_accounts_delete(request: web.Request) -> web.Response:
    """DELETE /api/accounts/{name} — remove an account directory."""
    name = request.match_info["name"]
    target = ACCOUNTS_DIR / name
    if not target.exists():
        return web.json_response({"error": "not found"}, status=404)
    shutil.rmtree(target)
    pool.scan()
    return web.json_response({"deleted": name})


async def api_accounts_toggle(request: web.Request) -> web.Response:
    """PUT /api/accounts/{name}/toggle — enable or disable an account."""
    name = request.match_info["name"]
    acct = pool.get(name)
    if not acct:
        return web.json_response({"error": "not found"}, status=404)
    acct.enabled = not acct.enabled
    return web.json_response(acct.to_dict())


async def api_accounts_refresh(request: web.Request) -> web.Response:
    """POST /api/accounts/{name}/refresh — manually refresh an account's token."""
    name = request.match_info["name"]
    acct = pool.get(name)
    if not acct:
        return web.json_response({"error": "not found"}, status=404)
    ok = await acct.refresh()
    return web.json_response({"refreshed": ok, "account": acct.to_dict()})


async def api_accounts_scan(request: web.Request) -> web.Response:
    """POST /api/accounts/scan — re-scan the accounts directory."""
    pool.scan()
    return web.json_response([a.to_dict() for a in pool.accounts])


async def api_quota(request: web.Request) -> web.Response:
    """GET /api/quota — return quota info for all accounts.

    Quota data is loaded from per-account quota.json files written by
    the quota_tracker module, or returned as empty if unavailable.
    """
    result = {}
    for acct in pool.accounts:
        quota_file = ACCOUNTS_DIR / acct.name / "quota.json"
        if quota_file.exists():
            with open(quota_file) as f:
                result[acct.name] = json.load(f)
        else:
            result[acct.name] = None
    return web.json_response(result)


async def api_status(request: web.Request) -> web.Response:
    """GET /api/status — proxy health and stats."""
    return web.json_response({
        "total_accounts": len(pool.accounts),
        "active_accounts": pool.active_count(),
        "running": True,
        "port": get("port"),
        "strategy": get("rotation_strategy"),
    })


async def api_config_get(request: web.Request) -> web.Response:
    """GET /api/config — return current config."""
    return web.json_response(load())


async def api_config_put(request: web.Request) -> web.Response:
    """PUT /api/config — update config."""
    body = await request.json()
    current = load()
    current.update(body)
    save(current)
    return web.json_response(current)


# ── Static UI ──────────────────────────────────────────────────────────

async def serve_ui(request: web.Request) -> web.Response:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return web.Response(text="UI not found. Create static/index.html", status=404)
    return web.FileResponse(index)


# ── Proxy catch-all ────────────────────────────────────────────────────

async def proxy_handler(request: web.Request) -> web.Response:
    return await proxy_handle(request, pool)


# ── Main ───────────────────────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()

    # Management API
    app.router.add_get("/api/accounts", api_accounts)
    app.router.add_post("/api/accounts/add", api_accounts_add)
    app.router.add_post("/api/accounts/scan", api_accounts_scan)
    app.router.add_delete("/api/accounts/{name}", api_accounts_delete)
    app.router.add_put("/api/accounts/{name}/toggle", api_accounts_toggle)
    app.router.add_post("/api/accounts/{name}/refresh", api_accounts_refresh)
    app.router.add_get("/api/quota", api_quota)
    app.router.add_get("/api/status", api_status)
    app.router.add_get("/api/config", api_config_get)
    app.router.add_put("/api/config", api_config_put)

    # Web UI
    app.router.add_get("/app", serve_ui)
    app.router.add_get("/app/", serve_ui)

    # Proxy — catch all other paths
    app.router.add_route("*", "/{tail:.*}", proxy_handler)

    return app


async def on_startup(_app: web.Application) -> None:
    asyncio.create_task(quota_run(pool))


if __name__ == "__main__":
    port = get("port")
    logger.info(f"Scanning accounts in {ACCOUNTS_DIR}")
    pool.scan()
    logger.info(f"Loaded {len(pool.accounts)} account(s)")
    logger.info(f"Starting proxy on http://127.0.0.1:{port}")
    logger.info(f"Web UI at http://127.0.0.1:{port}/app")

    app = create_app()
    app.on_startup.append(on_startup)
    web.run_app(app, host="127.0.0.1", port=port)
