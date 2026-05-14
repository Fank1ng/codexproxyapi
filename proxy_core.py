"""Core proxy — request forwarding with account pool, failover, and SSE streaming."""

import asyncio
import logging
import random
from typing import Optional

import aiohttp
from aiohttp import web

from account_manager import AccountPool
from config import get

logger = logging.getLogger(__name__)

UPSTREAM_MAP = {
    "/v1/": "https://api.openai.com",
    "/backend-api/": "https://chatgpt.com",
}

HOP_HEADERS = {
    "host", "transfer-encoding", "content-length", "connection",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "upgrade",
}


def _get_upstream(path: str) -> Optional[str]:
    for prefix, host in UPSTREAM_MAP.items():
        if path.startswith(prefix):
            return host
    return None


def _clean_headers(headers: dict) -> dict:
    return {
        k: v for k, v in headers.items()
        if k.lower() not in HOP_HEADERS
        and not k.lower().startswith("x-forwarded")
        and k.lower() != "via"
    }


async def handle(request: web.Request, pool: AccountPool) -> web.Response:
    path = request.path
    upstream = _get_upstream(path)
    if upstream is None:
        return web.Response(status=404, text=f"unknown upstream for path: {path}")

    target_url = f"{upstream}{path}"
    if request.query_string:
        target_url += f"?{request.query_string}"

    body = await request.read()
    headers = _clean_headers(dict(request.headers))

    cooldown = get("rate_limit_cooldown")
    max_retries = get("max_retries")

    for _ in range(max_retries):
        account = pool.pick()
        if account is None:
            return web.Response(
                status=429,
                text='{"error": "all accounts rate-limited"}',
                content_type="application/json",
            )

        headers["authorization"] = f"Bearer {account.access_token}"

        try:
            async with aiohttp.ClientSession() as upstream_session:
                async with upstream_session.request(
                    request.method,
                    target_url,
                    headers=headers,
                    data=body,
                    timeout=aiohttp.ClientTimeout(total=300, sock_connect=10),
                ) as upstream_resp:
                    if upstream_resp.status == 429:
                        pool.mark_rate_limited(account, cooldown)
                        await asyncio.sleep(random.uniform(0.01, 0.05))
                        continue

                    if upstream_resp.status == 401:
                        logger.info(f"Account {account.name}: got 401, refreshing")
                        ok = await account.refresh()
                        if not ok:
                            pool.mark_rate_limited(account, 300)
                        continue

                    # Stream response back
                    resp = web.StreamResponse(status=upstream_resp.status)
                    for k, v in upstream_resp.headers.items():
                        if k.lower() not in HOP_HEADERS:
                            resp.headers[k] = v

                    await resp.prepare(request)
                    async for chunk, _ in upstream_resp.content.iter_chunks():
                        await resp.write(chunk)
                    await resp.write_eof()
                    return resp

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"upstream error: {e}")
            continue

    return web.Response(
        status=502,
        text='{"error": "upstream unavailable"}',
        content_type="application/json",
    )
