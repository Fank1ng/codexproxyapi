"""Quota tracker — fetches usage stats from Codex API in the background."""

import asyncio
import json
import logging
import time
from typing import Optional

import aiohttp

from account_manager import AccountPool, ACCOUNTS_DIR
from config import get

USAGE_URL = "https://chatgpt.com/backend-api/codex/usage"

logger = logging.getLogger(__name__)


async def _fetch_usage(account, session: aiohttp.ClientSession) -> Optional[dict]:
    if not account.access_token:
        return None
    headers = {
        "Authorization": f"Bearer {account.access_token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Origin": "https://chatgpt.com",
    }
    try:
        async with session.get(
            USAGE_URL,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=8),
        ) as resp:
            if resp.status != 200:
                logger.debug(
                    f"Account {account.name}: usage API returned {resp.status}"
                )
                return None
            return await resp.json()
    except asyncio.TimeoutError:
        raise
    except Exception as e:
        logger.debug(f"Account {account.name}: usage fetch error: {e}")
        return None


async def _run_once(pool: AccountPool) -> None:
    await refresh_once(pool)


async def refresh_once(pool: AccountPool) -> dict:
    """Fetch and persist quota data for all enabled accounts once."""
    async def refresh_account(acct, session):
        if not acct.enabled:
            return acct.name, {"refreshed": False, "skipped": "disabled"}
        try:
            data = await _fetch_usage(acct, session)
        except asyncio.TimeoutError:
            logger.debug(f"Account {acct.name}: usage fetch timed out")
            return acct.name, {"refreshed": False, "error": "timeout"}
        if data:
            quota_file = ACCOUNTS_DIR / acct.name / "quota.json"
            data["_fetched_at"] = time.time()
            quota_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = quota_file.with_suffix(".json.tmp")
            with open(tmp_file, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            tmp_file.replace(quota_file)
            logger.debug(f"Account {acct.name}: quota updated")
            return acct.name, {"refreshed": True, "fetched_at": data["_fetched_at"]}
        return acct.name, {"refreshed": False, "error": "usage_unavailable"}

    async with aiohttp.ClientSession() as session:
        pairs = await asyncio.gather(
            *(refresh_account(acct, session) for acct in pool.accounts)
        )
    return {name: item for name, item in pairs}


async def run(pool: AccountPool) -> None:
    """Run the quota tracker loop. Meant to be launched as a background task."""
    while True:
        try:
            await _run_once(pool)
        except Exception as e:
            logger.error(f"quota tracker error: {e}")
        await asyncio.sleep(get("quota_refresh_interval"))
