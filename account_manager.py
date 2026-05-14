"""Account management — CRUD, token loading, OAuth token refresh."""

import asyncio
import json
import logging
import time
from typing import Optional
from pathlib import Path

import aiohttp

from config import CONFIG_DIR

ACCOUNTS_DIR = CONFIG_DIR / "accounts"
TOKEN_ENDPOINT = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

logger = logging.getLogger(__name__)


class Account:
    def __init__(self, name: str, auth_path: Path):
        self.name = name
        self.auth_path = auth_path
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.email: str = ""
        self.account_id: str = ""
        self.expires_at: float = 0
        self.rate_limited_until: float = 0
        self.enabled: bool = True
        self._refresh_lock = asyncio.Lock()

    def load(self) -> bool:
        """Load tokens from auth.json. Returns False if file missing or invalid."""
        if not self.auth_path.exists():
            return False
        try:
            with open(self.auth_path) as f:
                data = json.load(f)
            tokens = data.get("tokens", {})
            self.access_token = tokens.get("access_token", "")
            self.refresh_token = tokens.get("refresh_token", "")
            self.email = self._decode_email(self.access_token)
            self.account_id = tokens.get("account_id", "")
            self.expires_at = self._decode_expiry(self.access_token)
            return bool(self.access_token)
        except Exception as e:
            logger.warning(f"Account {self.name}: failed to load tokens: {e}")
            return False

    def save(self) -> None:
        """Persist current tokens back to auth.json."""
        data = {
            "auth_mode": "chatgpt",
            "OPENAI_API_KEY": None,
            "tokens": {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "id_token": "",
                "account_id": self.account_id,
            },
            "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()),
        }
        if self.auth_path.exists():
            try:
                with open(self.auth_path) as f:
                    old = json.load(f)
                data["tokens"]["id_token"] = old.get("tokens", {}).get("id_token", "")
                data["tokens"]["account_id"] = old.get("tokens", {}).get("account_id", "")
            except Exception:
                pass
        self.auth_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.auth_path, "w") as f:
            json.dump(data, f, indent=2)

    async def refresh(self) -> bool:
        """Refresh the OAuth token. Returns False on failure."""
        async with self._refresh_lock:
            if not self.refresh_token:
                logger.warning(f"Account {self.name}: no refresh token")
                return False
            logger.info(f"Account {self.name}: refreshing token...")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        TOKEN_ENDPOINT,
                        data={
                            "grant_type": "refresh_token",
                            "refresh_token": self.refresh_token,
                            "client_id": CLIENT_ID,
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            logger.error(
                                f"Account {self.name}: refresh failed ({resp.status}): {text}"
                            )
                            return False
                        data = await resp.json()
                        self.access_token = data["access_token"]
                        if "refresh_token" in data:
                            self.refresh_token = data["refresh_token"]
                        self.expires_at = self._decode_expiry(self.access_token)
                        self.save()
                        logger.info(f"Account {self.name}: token refreshed OK")
                        return True
            except Exception as e:
                logger.error(f"Account {self.name}: refresh error: {e}")
                return False

    @property
    def is_rate_limited(self) -> bool:
        return time.time() < self.rate_limited_until

    @property
    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "account_id": self.account_id,
            "enabled": self.enabled,
            "rate_limited": self.is_rate_limited,
            "rate_limited_until": self.rate_limited_until,
            "expires_at": self.expires_at,
            "has_tokens": bool(self.access_token),
        }

    @staticmethod
    def _decode_email(token: str) -> str:
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            import base64
            claims = json.loads(base64.urlsafe_b64decode(payload))
            return claims.get("email", "") or claims.get(
                "https://api.openai.com/email", ""
            )
        except Exception:
            return ""

    @staticmethod
    def _decode_expiry(token: str) -> float:
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            import base64
            claims = json.loads(base64.urlsafe_b64decode(payload))
            return claims.get("exp", 0)
        except Exception:
            return 0


class AccountPool:
    def __init__(self):
        self.accounts: list[Account] = []
        self._next_idx = 0

    def scan(self) -> None:
        """Scan accounts/ directory and load all valid accounts."""
        seen = set()
        for entry in sorted(ACCOUNTS_DIR.iterdir()):
            if not entry.is_dir():
                continue
            auth_file = entry / "auth.json"
            if not auth_file.exists():
                continue
            name = entry.name
            seen.add(name)
            existing = self.get(name)
            if existing:
                existing.load()
            else:
                acct = Account(name, auth_file)
                if acct.load():
                    self.accounts.append(acct)
                    logger.info(f"Account '{name}' loaded: {acct.email}")
        # Remove accounts whose directory no longer exists
        self.accounts = [a for a in self.accounts if a.name in seen]

    def get(self, name: str) -> Optional["Account"]:
        for a in self.accounts:
            if a.name == name:
                return a
        return None

    def pick(self) -> Optional["Account"]:
        """Round-robin selection, skipping disabled and rate-limited accounts."""
        if not self.accounts:
            return None
        for _ in range(len(self.accounts)):
            idx = self._next_idx % len(self.accounts)
            self._next_idx += 1
            acct = self.accounts[idx]
            if acct.enabled and not acct.is_rate_limited and acct.access_token:
                return acct
        return None

    def mark_rate_limited(self, account: Account, cooldown: int = 60) -> None:
        account.rate_limited_until = time.time() + cooldown
        logger.warning(
            f"Account {account.name}: rate-limited until "
            f"{time.strftime('%H:%M:%S', time.localtime(account.rate_limited_until))}"
        )

    def all_limited(self) -> bool:
        return all(
            a.is_rate_limited or not a.enabled or not a.access_token
            for a in self.accounts
        )

    def active_count(self) -> int:
        return sum(
            1 for a in self.accounts if a.enabled and not a.is_rate_limited and a.access_token
        )
