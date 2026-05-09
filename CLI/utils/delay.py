"""
@Author: Edison Malasan
--------------
human-like delay utilities.
provides randomized sleeps, shuffling, and exponential backoff to make automated requests appear more organic
"""

import time
import random
import logging

logger = logging.getLogger("kingshot")


def random_delay(min_sec: float = 2.0, max_sec: float = 7.0, label: str = ""):
    """
    Sleep for a random duration between min_sec and max_sec.
    Uses a slightly weighted distribution toward the middle of the range
    to mimic natural human timing.
    """
    # triangular distribution: peaks near middle of [min, max]
    duration = random.triangular(min_sec, max_sec, (min_sec + max_sec) / 2)
    if label:
        logger.debug(f"⏳ Waiting {duration:.1f}s {label}")
    time.sleep(duration)


def batch_pause(min_sec: float = 10.0, max_sec: float = 30.0):
    """
    Longer pause between processing batches of players.
    Simulates a human taking a short break.
    """
    duration = random.uniform(min_sec, max_sec)
    logger.debug(f"⏸  Batch pause: {duration:.1f}s")
    time.sleep(duration)


def exponential_backoff(attempt: int, base: float = 2.0, jitter: bool = True) -> float:
    """
    Calculate sleep time using exponential backoff:
      sleep = base^attempt + optional random jitter

    Args:
        attempt:  0-indexed retry attempt number
        base:     Base multiplier (default 2 → 2, 4, 8, 16 …)
        jitter:   Add ±0–1s of random jitter to avoid thundering herd

    Returns:
        Actual seconds slept.
    """
    sleep_time = (base ** attempt)
    if jitter:
        sleep_time += random.uniform(0, 1)
    sleep_time = min(sleep_time, 60)  # Cap at 60s
    logger.debug(f"🔄 Retry backoff attempt {attempt + 1}: sleeping {sleep_time:.1f}s")
    time.sleep(sleep_time)
    return sleep_time


def shuffle_list(items: list) -> list:
    """
    Return a shuffled copy of a list.
    Used to randomize player processing order each cycle.
    """
    copy = items[:]
    random.shuffle(copy)
    return copy
