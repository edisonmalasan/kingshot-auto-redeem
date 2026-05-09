"""
@Author: Edison Malasan
--------------------------
Manages the local player database (json/players.json)

Responsibilities:
  - register new players (validate via API, then save)
  - load/save player list
  - update a player's redeemed codes list
  - list registered players
"""

import logging
from datetime import datetime
from colorama import Fore, Style

from utils.storage import load_json, save_json
from services.api_service import fetch_player_info

logger = logging.getLogger("kingshot")


def _load_players(filepath: str) -> dict:
    return load_json(filepath, default={"players": []})


def _save_players(filepath: str, data: dict) -> bool:
    return save_json(filepath, data)


def get_all_players(filepath: str) -> list[dict]:
    """Return the list of registered players."""
    return _load_players(filepath).get("players", [])


def find_player(filepath: str, player_id: str) -> dict | None:
    """Find a player by ID. Returns None if not found."""
    players = get_all_players(filepath)
    for p in players:
        if str(p.get("playerId")) == str(player_id):
            return p
    return None


def register_player(filepath: str, player_id: str, base_url: str, max_retries: int = 3) -> bool:
    """
    Register a new player:
      1. Check if already registered
      2. Validate via API
      3. Save to local database

    Returns True on success.
    """
    player_id = str(player_id).strip()

    # check for duplicate
    existing = find_player(filepath, player_id)
    if existing:
        print(
            f"\n{Fore.YELLOW}⚠  Player {Fore.WHITE + Style.BRIGHT}{existing['name']}"
            f"{Fore.YELLOW} (ID: {player_id}) is already registered.{Style.RESET_ALL}"
        )
        return False

    print(f"\n{Fore.CYAN}🔍 Fetching player info for ID: {player_id} …{Style.RESET_ALL}")
    info = fetch_player_info(base_url, player_id, max_retries=max_retries)

    if not info:
        print(f"{Fore.RED}✗  Player ID {player_id} not found or API error.{Style.RESET_ALL}")
        return False

    # display player card
    _print_player_card(info)

    # confirm registration
    confirm = input(
        f"\n{Fore.CYAN}➤  Register this player? (y/n): {Style.RESET_ALL}"
    ).strip().lower()

    if confirm != "y":
        print(f"{Fore.YELLOW}Registration cancelled.{Style.RESET_ALL}")
        return False

    # build player record
    new_player = {
        "playerId":      str(info["playerId"]),
        "name":          info.get("name", "Unknown"),
        "kingdom":       info.get("kingdom"),
        "level":         info.get("levelRendered", info.get("level")),
        "redeemedCodes": [],
        "registeredAt":  datetime.utcnow().isoformat() + "Z",
    }

    # save
    data = _load_players(filepath)
    data["players"].append(new_player)
    if _save_players(filepath, data):
        print(
            f"\n{Fore.GREEN + Style.BRIGHT}✓  {new_player['name']} registered successfully!"
            f"{Style.RESET_ALL}"
        )
        logger.info(f"[PLAYER] Registered: {new_player['name']} (ID: {player_id})")
        return True
    else:
        print(f"{Fore.RED}✗  Failed to save player to database.{Style.RESET_ALL}")
        return False


def remove_player(filepath: str, player_id: str) -> bool:
    """Remove a player from the database."""
    player_id = str(player_id)
    data = _load_players(filepath)
    before = len(data["players"])
    data["players"] = [
        p for p in data["players"] if str(p.get("playerId")) != player_id
    ]
    if len(data["players"]) < before:
        _save_players(filepath, data)
        logger.info(f"[PLAYER] Removed player ID: {player_id}")
        return True
    return False


def mark_code_redeemed(filepath: str, player_id: str, code: str) -> bool:
    """
    Add a gift code to a player's redeemed list and persist.
    Returns True if the player was found and updated.
    """
    player_id = str(player_id)
    data = _load_players(filepath)

    for player in data["players"]:
        if str(player.get("playerId")) == player_id:
            redeemed_codes = player.setdefault("redeemedCodes", [])
            if code not in redeemed_codes:
                redeemed_codes.append(code)
                return _save_players(filepath, data)
            return True  # Already marked — no-op

    logger.warning(f"[PLAYER] mark_code_redeemed: player {player_id} not found")
    return False


def list_players(filepath: str):
    """Print a formatted table of registered players."""
    players = get_all_players(filepath)
    if not players:
        print(f"\n{Fore.YELLOW}No players registered yet.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN + Style.BRIGHT}{'─' * 60}")
    print(f"  {'ID':<15} {'Name':<22} {'Kingdom':<10} {'Level':<8} {'Codes'}")
    print(f"{'─' * 60}{Style.RESET_ALL}")

    for p in players:
        code_count = len(p.get("redeemedCodes", []))
        print(
            f"  {Fore.WHITE}{p['playerId']:<15}{Style.RESET_ALL}"
            f"{Fore.GREEN}{p.get('name', '?'):<22}{Style.RESET_ALL}"
            f"{Fore.YELLOW}{str(p.get('kingdom', '?')):<10}{Style.RESET_ALL}"
            f"{Fore.CYAN}{str(p.get('level', '?')):<8}{Style.RESET_ALL}"
            f"{Fore.MAGENTA}{code_count} redeemed{Style.RESET_ALL}"
        )
    print()


def _print_player_card(info: dict):
    """Display a formatted player info card."""
    print(f"""
{Fore.CYAN + Style.BRIGHT}┌─────────────────────────────────────┐
│  PLAYER INFO                        │
├─────────────────────────────────────┤
│  {Fore.WHITE}Name    : {Fore.GREEN}{info.get('name', '?'):<27}{Fore.CYAN}│
│  {Fore.WHITE}ID      : {Fore.YELLOW}{str(info.get('playerId', '?')):<27}{Fore.CYAN}│
│  {Fore.WHITE}Kingdom : {Fore.MAGENTA}{str(info.get('kingdom', '?')):<27}{Fore.CYAN}│
│  {Fore.WHITE}Level   : {Fore.WHITE}{info.get('levelRendered', str(info.get('level', '?'))):<27}{Fore.CYAN}│
└─────────────────────────────────────┘{Style.RESET_ALL}""")
