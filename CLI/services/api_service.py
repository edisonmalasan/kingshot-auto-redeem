"""
@Author: Edison Malasan
-----------------------
Handles all HTTP communication with the Kingshot API

Responsibilities:
  - build and reuse a requests.Session with realistic headers
  - fetch player info
  - fetch active gift codes
  - submit gift code redemptions
  - retry on transient errors with exponential backoff
"""

import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.delay import exponential_backoff

logger = logging.getLogger("kingshot")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "en-US,en;q=0.9",
    # Do not advertise Brotli unless a decoder is installed. Without that,
    # requests leaves the body compressed and response.json() fails.
    "Accept-Encoding":  "gzip, deflate",
    "Connection":       "keep-alive",
    "Referer":          "https://kingshot.net/",
    "Origin":           "https://kingshot.net",
}


def _build_session() -> requests.Session:
    """
    Create a requests.Session with:
      - Persistent connection pooling (keep-alive)
      - Automatic retry on connection errors (not on 4xx/5xx — we handle those)
      - Default browser-like headers
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(DEFAULT_HEADERS)
    return session


# module-level session — reused across all API calls
_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    """Return the shared session, creating it if needed."""
    global _session
    if _session is None:
        _session = _build_session()
    return _session


def _json_or_none(response: requests.Response) -> Optional[dict]:
    """Parse JSON and log useful response details when parsing fails."""
    try:
        return response.json()
    except ValueError as e:
        preview = response.text[:160].replace("\n", " ")
        logger.error(
            "[API] Invalid JSON response: status=%s content-type=%s encoding=%s error=%s preview=%r",
            response.status_code,
            response.headers.get("content-type"),
            response.headers.get("content-encoding"),
            e,
            preview,
        )
        return None


def _extract_gift_codes(data) -> list[str]:
    """Extract code strings from API data in either legacy or current format."""
    if isinstance(data, dict):
        data = data.get("giftCodes") or data.get("codes") or data.get("activeCodes") or []

    if not isinstance(data, list):
        logger.warning(f"[API] Unexpected gift codes format: {type(data)}")
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


def _api_error_key(payload: dict) -> str:
    meta = payload.get("meta")
    if isinstance(meta, dict):
        return str(meta.get("errorKey") or "")
    return ""


def _redeem_result(data: dict) -> dict:
    status = data.get("status", "")
    message = data.get("message", "")
    error_key = _api_error_key(data)

    if status == "success":
        return {"success": True, "already": False, "message": message, "raw": data}

    if error_key == "GIFT_CODE_ALREADY_REDEEMED":
        return {"success": False, "already": True, "message": message, "raw": data}

    return {
        "success": False,
        "already": False,
        "message": message or error_key or "Redeem failed",
        "raw": data,
    }


# API FUNC
def fetch_player_info(base_url: str, player_id: str, max_retries: int = 3) -> Optional[dict]:
    """
    GET /api/player-info?playerId=<id>

    Returns the 'data' dict on success, None on failure.
    Retries up to max_retries times with exponential backoff.
    """
    url = f"{base_url}/player-info"
    params = {"playerId": player_id}
    session = get_session()

    for attempt in range(max_retries):
        try:
            logger.debug(f"[API] GET player info → playerId={player_id} (attempt {attempt + 1})")
            response = session.get(url, params=params, timeout=15)
            response.raise_for_status()
            payload = _json_or_none(response)
            if payload is None:
                return None

            if payload.get("status") == "success":
                return payload.get("data")
            else:
                logger.warning(f"[API] Player not found: {payload.get('message', 'Unknown error')}")
                return None  # Non-retriable: player simply doesn't exist

        except requests.exceptions.Timeout:
            logger.warning(f"[API] Timeout fetching player {player_id}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"[API] Connection error fetching player {player_id}")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[API] HTTP error fetching player {player_id}: {e}")
        except Exception as e:
            logger.error(f"[API] Unexpected error: {e}")
            return None

        if attempt < max_retries - 1:
            exponential_backoff(attempt)

    logger.error(f"[API] All {max_retries} attempts failed for player {player_id}")
    return None


def fetch_active_gift_codes(base_url: str, max_retries: int = 3) -> list[str]:
    """
    GET /api/gift-codes

    Returns a list of active gift code strings.
    Returns empty list on failure.
    """
    url = f"{base_url}/gift-codes"
    session = get_session()

    for attempt in range(max_retries):
        try:
            logger.debug(f"[API] GET active gift codes (attempt {attempt + 1})")
            response = session.get(url, timeout=15)
            response.raise_for_status()
            payload = _json_or_none(response)
            if payload is None:
                return []

            if payload.get("status") == "success":
                # API may return a list directly or nest it under data.giftCodes.
                data = payload.get("data", [])
                codes = _extract_gift_codes(data)
                logger.debug(f"[API] Fetched {len(codes)} active codes")
                return codes
            else:
                logger.warning(f"[API] Gift codes fetch failed: {payload.get('message')}")
                return []

        except requests.exceptions.Timeout:
            logger.warning("[API] Timeout fetching gift codes")
        except requests.exceptions.ConnectionError:
            logger.warning("[API] Connection error fetching gift codes")
        except Exception as e:
            logger.error(f"[API] Unexpected error fetching codes: {e}")
            return []

        if attempt < max_retries - 1:
            exponential_backoff(attempt)

    logger.error(f"[API] Failed to fetch gift codes after {max_retries} attempts")
    return []


def redeem_gift_code(
    base_url: str,
    player_id: str,
    gift_code: str,
    max_retries: int = 3
) -> dict:
    """
    POST /api/gift-codes/redeem
    Body: {"playerId": "<id>", "giftCode": "<code>"}

    Returns a result dict:
      {
        "success":  bool,
        "already":  bool,   # True if already redeemed
        "message":  str,
        "raw":      dict    # Full API response
      }
    """
    url = f"{base_url}/gift-codes/redeem"
    payload = {"playerId": str(player_id), "giftCode": gift_code}
    session = get_session()

    for attempt in range(max_retries):
        try:
            logger.debug(
                f"[API] POST redeem → player={player_id} code={gift_code} "
                f"(attempt {attempt + 1})"
            )
            response = session.post(url, json=payload, timeout=15)
            data = _json_or_none(response)
            if data is None:
                response.raise_for_status()
                return {"success": False, "already": False, "message": "Invalid JSON response", "raw": {}}

            if response.ok or 400 <= response.status_code < 500:
                return _redeem_result(data)

            response.raise_for_status()

        except requests.exceptions.Timeout:
            logger.warning(f"[API] Timeout redeeming {gift_code} for {player_id}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"[API] Connection error redeeming {gift_code}")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[API] HTTP error: {e}")
        except Exception as e:
            logger.error(f"[API] Unexpected redeem error: {e}")
            return {"success": False, "already": False, "message": str(e), "raw": {}}

        if attempt < max_retries - 1:
            exponential_backoff(attempt)

    return {
        "success": False,
        "already": False,
        "message": f"Failed after {max_retries} attempts",
        "raw": {}
    }
