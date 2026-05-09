"""
@Author: Edison Malasan
--------------------------
Core auto-redeem engine.

Responsibilities:
  - fetch active gift codes
  - detect NEW codes not seen before in the global known-code cache
  - for each player, redeem codes they havent used yet
  - human-like delays between actions
  - persist results immediately after each success
"""

import logging
from datetime import datetime, timezone
from colorama import Fore, Style

from utils.delay import random_delay, batch_pause, shuffle_list
from utils.storage import load_json, save_json
from services.api_service import fetch_active_gift_codes, redeem_gift_code
from services.player_service import get_all_players, mark_code_redeemed

logger = logging.getLogger("kingshot")


# manage known-code caching to detect new codes each cycle
def load_code_cache(filepath: str) -> dict:
    return load_json(filepath, default={"known_codes": [], "last_fetched": None})


def save_code_cache(filepath: str, cache: dict) -> bool:
    return save_json(filepath, cache)


def get_new_codes(active_codes: list[str], cache: dict) -> list[str]:
    """Return codes that are in active_codes but NOT in cache['known_codes']."""
    known = set(cache.get("known_codes", []))
    return [c for c in active_codes if c not in known]


def update_code_cache(filepath: str, active_codes: list[str]) -> list[str]:
    """
    Update the code cache with the current active list.
    Returns the list of newly discovered codes.
    """
    cache = load_code_cache(filepath)
    new_codes = get_new_codes(active_codes, cache)

    # Merge and deduplicate while preserving first-seen order.
    all_known = list(dict.fromkeys(cache.get("known_codes", []) + active_codes))
    cache["known_codes"] = all_known
    cache["last_fetched"] = datetime.now(timezone.utc).isoformat()
    save_code_cache(filepath, cache)

    if new_codes:
        logger.info(
            f"[SYSTEM] 🆕 {len(new_codes)} new code(s) detected: "
            f"{Fore.GREEN + Style.BRIGHT}{', '.join(new_codes)}{Style.RESET_ALL}"
        )
    else:
        logger.info("[SYSTEM] No new gift codes this cycle.")

    return new_codes


# per player redemption
def redeem_codes_for_player(
    player: dict,
    codes_to_try: list[str],
    players_filepath: str,
    base_url: str,
    config: dict
) -> dict:
    """
    Attempt to redeem a list of gift codes for a single player.

    Only redeems codes NOT already in player['redeemedCodes'].

    Returns a stats dict:
      { "success": int, "already": int, "failed": int }
    """
    stats = {"success": 0, "already": 0, "failed": 0}
    player_id = str(player["playerId"])
    player_name = player.get("name", player_id)
    already_redeemed = set(player.get("redeemedCodes", []))

    pending = [c for c in codes_to_try if c not in already_redeemed]

    if not pending:
        logger.info(
            f"[SKIP] {Fore.WHITE}{player_name}{Style.RESET_ALL} "
            f"— all codes already redeemed"
        )
        stats["already"] += len(codes_to_try)
        return stats

    logger.info(
        f"\n[PLAYER] Processing {Fore.CYAN + Style.BRIGHT}{player_name}{Style.RESET_ALL} "
        f"(ID: {player_id}) — {len(pending)} code(s) to try"
    )

    min_delay = config["min_delay_seconds_gift_code"]
    max_delay = config["max_delay_seconds_gift_code"]
    max_retries = config.get("max_retries", 3)

    for i, code in enumerate(pending):
        result = redeem_gift_code(
            base_url=base_url,
            player_id=player_id,
            gift_code=code,
            max_retries=max_retries
        )

        if result["success"]:
            logger.info(
                f"[SUCCESS] {Fore.GREEN + Style.BRIGHT}✓{Style.RESET_ALL} "
                f"{player_name} redeemed {Fore.GREEN + Style.BRIGHT}{code}{Style.RESET_ALL}"
            )
            mark_code_redeemed(players_filepath, player_id, code)
            stats["success"] += 1

        elif result["already"]:
            logger.info(
                f"[SKIP]    {Fore.WHITE}↷{Style.RESET_ALL} "
                f"{player_name} already had {Fore.WHITE}{code}{Style.RESET_ALL}"
            )
            # Sync local state — mark it so we don't try again
            mark_code_redeemed(players_filepath, player_id, code)
            stats["already"] += 1

        else:
            logger.warning(
                f"[ERROR]   {Fore.RED}✗{Style.RESET_ALL} "
                f"{player_name} failed {Fore.RED}{code}{Style.RESET_ALL} "
                f"— {result['message']}"
            )
            stats["failed"] += 1

        # Human-like delay between codes (skip after last code)
        if i < len(pending) - 1:
            random_delay(min_delay, max_delay, label=f"after {code}")

    return stats


# full redeem cycle

def run_redeem_cycle(
    players_filepath: str,
    codes_cache_filepath: str,
    base_url: str,
    config: dict,
    new_codes_only: bool = False
) -> dict:
    """
    One complete redeem cycle:
      1. Fetch active codes from API
      2. Detect new codes (if new_codes_only=True, skip known ones)
      3. Shuffle player order
      4. Redeem pending codes for each player
      5. Pause between players

    Returns aggregated stats.
    """
    total_stats = {"success": 0, "already": 0, "failed": 0}

    # Step 1 — Fetch codes
    logger.info("[SYSTEM] Fetching active gift codes…")
    active_codes = fetch_active_gift_codes(base_url, max_retries=config.get("max_retries", 3))

    if not active_codes:
        logger.warning("[SYSTEM] No active gift codes found this cycle.")
        return total_stats

    logger.info(f"[SYSTEM] Active codes: {Fore.YELLOW}{', '.join(active_codes)}{Style.RESET_ALL}")

    # Step 2 — update cache, detect new
    new_codes = update_code_cache(codes_cache_filepath, active_codes)

    codes_to_process = new_codes if new_codes_only else active_codes
    if not codes_to_process:
        logger.info("[SYSTEM] Nothing new to redeem this cycle.")
        return total_stats

    # Step 3 — load and shuffle players
    players = get_all_players(players_filepath)
    if not players:
        logger.warning("[SYSTEM] No players registered. Use option 1 to add players.")
        return total_stats

    players = shuffle_list(players)
    logger.info(
        f"[SYSTEM] Processing {len(players)} player(s) in randomized order…"
    )

    # Step 4 — process each player
    for idx, player in enumerate(players):
        player_stats = redeem_codes_for_player(
            player=player,
            codes_to_try=codes_to_process,
            players_filepath=players_filepath,
            base_url=base_url,
            config=config,
        )
        for k in total_stats:
            total_stats[k] += player_stats[k]

        # Step 5 — pause between players (not after the last one)
        if idx < len(players) - 1:
            batch_pause(
                config["batch_pause_redeem_min"],
                config["batch_pause_redeem_max"],
            )

    _print_cycle_summary(total_stats)
    return total_stats


def _print_cycle_summary(stats: dict):
    """Print a concise summary of the cycle results."""
    print(f"""
{Fore.CYAN + Style.BRIGHT}╔══════════════════════════════╗
║  CYCLE SUMMARY               ║
╠══════════════════════════════╣
║  {Fore.GREEN}✓ Success  : {stats['success']:<16}{Fore.CYAN}║
║  {Fore.WHITE}↷ Redeemed : {stats['already']:<16}{Fore.CYAN}║
║  {Fore.RED}✗ Failed   : {stats['failed']:<16}{Fore.CYAN}║
╚══════════════════════════════╝{Style.RESET_ALL}""")
