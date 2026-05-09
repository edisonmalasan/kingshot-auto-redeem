import asyncio
import logging
import random
from typing import Any

import aiohttp


logger = logging.getLogger("kingshot-bot.api")


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Referer": "https://kingshot.net/",
    "Origin": "https://kingshot.net",
}


class KingshotApi:
    def __init__(self, base_url: str, max_retries: int = 3, backoff_base: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._session: aiohttp.ClientSession | None = None

    async def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=20)
            self._session = aiohttp.ClientSession(headers=DEFAULT_HEADERS, timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_player_info(self, player_id: str) -> dict[str, Any] | None:
        data = await self._request_json("GET", "/player-info", params={"playerId": player_id})
        if data and data.get("status") == "success":
            return data.get("data")
        return None

    async def fetch_active_gift_codes(self) -> list[str]:
        data = await self._request_json("GET", "/gift-codes")
        if not data or data.get("status") != "success":
            return []
        return self._extract_codes(data.get("data", []))

    async def redeem_gift_code(self, player_id: str, gift_code: str) -> dict[str, Any]:
        data = await self._request_json(
            "POST",
            "/gift-codes/redeem",
            json={"playerId": str(player_id), "giftCode": gift_code},
            retry_client_errors=False,
        )
        if not data:
            return {"success": False, "already": False, "message": "Invalid response", "raw": {}}

        if data.get("status") == "success":
            return {"success": True, "already": False, "message": data.get("message", ""), "raw": data}

        error_key = ""
        meta = data.get("meta")
        if isinstance(meta, dict):
            error_key = str(meta.get("errorKey") or "")

        return {
            "success": False,
            "already": error_key == "GIFT_CODE_ALREADY_REDEEMED",
            "message": data.get("message") or error_key or "Redeem failed",
            "raw": data,
        }

    async def _request_json(self, method: str, endpoint: str, retry_client_errors: bool = True, **kwargs) -> Any | None:
        url = f"{self.base_url}{endpoint}"
        for attempt in range(self.max_retries):
            try:
                session = await self.session()
                async with session.request(method, url, **kwargs) as response:
                    if response.status < 500 and (retry_client_errors or response.status < 400):
                        return await response.json(content_type=None)
                    if response.status < 500:
                        return await response.json(content_type=None)
                    response.raise_for_status()
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                logger.warning("%s %s failed on attempt %s: %s", method, endpoint, attempt + 1, exc)

            if attempt < self.max_retries - 1:
                await self._sleep_backoff(attempt)

        return None

    async def _sleep_backoff(self, attempt: int) -> None:
        delay = min((self.backoff_base**attempt) + random.uniform(0, 1), 60)
        await asyncio.sleep(delay)

    @staticmethod
    def _extract_codes(data: Any) -> list[str]:
        if isinstance(data, dict):
            data = data.get("giftCodes") or data.get("codes") or data.get("activeCodes") or []
        if not isinstance(data, list):
            return []

        codes = []
        for item in data:
            if isinstance(item, str):
                codes.append(item)
            elif isinstance(item, dict):
                code = item.get("code") or item.get("giftCode") or item.get("gift_code")
                if code:
                    codes.append(str(code))
        return codes
