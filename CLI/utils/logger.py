"""
@Author: Edison Malasan
---------------
colored logging system using colorama
writes to both terminal (colored) and log file (plain text).
"""

import logging
import os
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds ANSI color codes to terminal log output."""

    LEVEL_COLORS = {
        logging.DEBUG:    Fore.CYAN,
        logging.INFO:     Fore.GREEN,
        logging.WARNING:  Fore.YELLOW,
        logging.ERROR:    Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    LABEL_COLORS = {
        "REDEEM":   Fore.BLUE + Style.BRIGHT,
        "PLAYER":   Fore.CYAN + Style.BRIGHT,
        "API":      Fore.YELLOW,
        "SYSTEM":   Fore.WHITE + Style.BRIGHT,
        "SUCCESS":  Fore.GREEN + Style.BRIGHT,
        "SKIP":     Fore.WHITE,
        "ERROR":    Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_tag = f"{color}[{record.levelname:8s}]{Style.RESET_ALL}"
        time_tag  = f"{Fore.WHITE}{Style.DIM}[{timestamp}]{Style.RESET_ALL}"
        message   = record.getMessage()
        return f"{time_tag} {level_tag} {message}"


class PlainFormatter(logging.Formatter):
    """Plain formatter for file output (no ANSI codes)."""

    def format(self, record):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{record.levelname:8s}] {record.getMessage()}"


def get_logger(name: str = "kingshot", level: str = "INFO") -> logging.Logger:
    """
    Build and return a logger with:
      - Colored StreamHandler → terminal
      - PlainFormatter FileHandler → logs/kingshot_YYYY-MM-DD.log
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # terminal handler
    sh = logging.StreamHandler()
    sh.setFormatter(ColoredFormatter())
    sh.setLevel(numeric_level)
    logger.addHandler(sh)

    # file handler
    log_filename = datetime.now().strftime("kingshot_%Y-%m-%d.log")
    log_path = os.path.join(LOG_DIR, log_filename)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(PlainFormatter())
    fh.setLevel(logging.DEBUG)  # Always capture everything in file
    logger.addHandler(fh)

    return logger


def log_banner(logger: logging.Logger):
    """Print the startup banner."""
    banner = f"""
{Fore.YELLOW + Style.BRIGHT}
╔══════════════════════════════════════════════════════╗
║         KINGSHOT AUTO GIFT CODE REDEEMER             ║
╚══════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)
    logger.info("Kingshot Auto Redeemer started.")


def log_section(title: str):
    """Print a section divider to the terminal."""
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'─' * 52}")
    print(f"  {title}")
    print(f"{'─' * 52}{Style.RESET_ALL}\n")
