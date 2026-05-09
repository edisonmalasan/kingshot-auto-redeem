"""
@Author: Edison Malasan
-------
Kingshot Auto Gift Code Redeemer
Entry point

Usage:
    python main.py

The menu lets you:
  1. Register players
  2. List players
  3. Remove a player
  4. Run a manual redeem cycle (all codes)
  5. Run a manual redeem cycle (new codes only)
  6. Start background auto-polling
  7. Exit
"""

import sys
import time
import signal
import threading
from datetime import datetime

from colorama import Fore, Style

from utils.logger import get_logger, log_banner, log_section
from utils.storage import load_config
from services.player_service import register_player, list_players, remove_player
from services.redeem_service import run_redeem_cycle

config = load_config("json/config.json")
log_level = config.get("log_level", "INFO")
logger = get_logger("kingshot", level=log_level)

storage_config = config.get("storage", {})
PLAYERS_FILE  = storage_config.get("players_file", "json/players.json")
CODES_FILE    = storage_config.get(
    "known_codes_file",
    storage_config.get("redeemed_codes_file", "json/known_codes.json"),
)
BASE_URL      = config.get("api", {}).get("base_url", "https://kingshot.net/api")
POLL_INTERVAL = config.get("polling_interval_seconds", 300)

# shutdown handling
_stop_event = threading.Event()


def _handle_signal(sig, frame):
    print(f"\n\n{Fore.YELLOW + Style.BRIGHT}⚠  Interrupt received — shutting down gracefully…{Style.RESET_ALL}")
    _stop_event.set()
    sys.exit(0)


signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# bg polling thread
def _polling_loop():
    """
    Background thread that polls for new gift codes every POLL_INTERVAL seconds.
    Stops when _stop_event is set.
    """
    logger.info(
        f"[SYSTEM] 🚀 Background polling started "
        f"(interval: {POLL_INTERVAL}s / {POLL_INTERVAL // 60}m)"
    )

    while not _stop_event.is_set():
        logger.info("[SYSTEM] ─── Polling cycle started ───")
        try:
            run_redeem_cycle(
                players_filepath=PLAYERS_FILE,
                codes_cache_filepath=CODES_FILE,
                base_url=BASE_URL,
                config=config,
                new_codes_only=True,   # background mode: only redeem newly detected codes
            )
        except Exception as e:
            logger.error(f"[SYSTEM] Unhandled error in polling cycle: {e}", exc_info=True)

        next_run = datetime.now().strftime("%H:%M:%S")
        logger.info(
            f"[SYSTEM] ✓ Cycle done. Next poll in {POLL_INTERVAL}s "
            f"(press Ctrl+C to stop)"
        )

        # Wait, but wake up immediately if stop is signaled
        _stop_event.wait(timeout=POLL_INTERVAL)

    logger.info("[SYSTEM] Polling loop stopped.")


# menu handlers
def _menu_register():
    log_section("REGISTER PLAYER")
    player_id = input(f"{Fore.CYAN}➤  Enter Player ID: {Style.RESET_ALL}").strip()
    if not player_id:
        print(f"{Fore.YELLOW}No ID entered.{Style.RESET_ALL}")
        return
    register_player(
        filepath=PLAYERS_FILE,
        player_id=player_id,
        base_url=BASE_URL,
        max_retries=config.get("max_retries", 3),
    )


def _menu_list():
    log_section("REGISTERED PLAYERS")
    list_players(PLAYERS_FILE)


def _menu_remove():
    log_section("REMOVE PLAYER")
    list_players(PLAYERS_FILE)
    player_id = input(f"{Fore.CYAN}➤  Enter Player ID to remove: {Style.RESET_ALL}").strip()
    if not player_id:
        return
    if remove_player(PLAYERS_FILE, player_id):
        print(f"{Fore.GREEN}✓  Player {player_id} removed.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗  Player {player_id} not found.{Style.RESET_ALL}")


def _menu_manual_all():
    log_section("MANUAL REDEEM — ALL CODES")
    run_redeem_cycle(
        players_filepath=PLAYERS_FILE,
        codes_cache_filepath=CODES_FILE,
        base_url=BASE_URL,
        config=config,
        new_codes_only=False,
    )


def _menu_manual_new():
    log_section("MANUAL REDEEM — NEW CODES ONLY")
    run_redeem_cycle(
        players_filepath=PLAYERS_FILE,
        codes_cache_filepath=CODES_FILE,
        base_url=BASE_URL,
        config=config,
        new_codes_only=True,
    )


def _menu_start_polling():
    log_section("AUTO POLLING")
    if _stop_event.is_set():
        print(f"{Fore.RED}Stop event is set — restart the program to use polling.{Style.RESET_ALL}")
        return

    print(
        f"{Fore.GREEN + Style.BRIGHT}Starting background polling loop…\n"
        f"{Fore.WHITE}Poll interval : {POLL_INTERVAL}s\n"
        f"Press {Fore.YELLOW}Ctrl+C{Fore.WHITE} at any time to stop.{Style.RESET_ALL}\n"
    )

    thread = threading.Thread(target=_polling_loop, daemon=True, name="PollingThread")
    thread.start()

    # block main thread ctrl+c handling while polling thread is running
    try:
        while thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        _handle_signal(None, None)


MENU_OPTIONS = {
    "1": ("Register a player",               _menu_register),
    "2": ("List registered players",          _menu_list),
    "3": ("Remove a player",                  _menu_remove),
    "4": ("Manual redeem — all active codes", _menu_manual_all),
    "5": ("Manual redeem — new codes only",   _menu_manual_new),
    "6": ("Start auto-polling (background)",  _menu_start_polling),
    "7": ("Exit",                             None),
}


def _print_menu():
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'═' * 52}")
    print(f"  MAIN MENU")
    print(f"{'═' * 52}{Style.RESET_ALL}")
    for key, (label, _) in MENU_OPTIONS.items():
        color = Fore.RED if key == "7" else Fore.WHITE
        print(f"  {Fore.YELLOW}[{key}]{Style.RESET_ALL}  {color}{label}{Style.RESET_ALL}")
    print()


def main():
    log_banner(logger)

    while True:
        _print_menu()
        choice = input(f"{Fore.CYAN}➤  Select option: {Style.RESET_ALL}").strip()

        if choice not in MENU_OPTIONS:
            print(f"{Fore.RED}Invalid option. Please choose 1–7.{Style.RESET_ALL}")
            continue

        label, handler = MENU_OPTIONS[choice]

        if choice == "7":
            print(f"\n{Fore.YELLOW + Style.BRIGHT}Goodbye! 👋{Style.RESET_ALL}\n")
            sys.exit(0)

        try:
            handler()
        except Exception as e:
            logger.error(f"Error in menu option '{label}': {e}", exc_info=True)


if __name__ == "__main__":
    main()
