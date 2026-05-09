import asyncio
import logging
import random
from dataclasses import dataclass

from .api import KingshotApi
from .repository import JsonRepository


logger = logging.getLogger("kingshot-bot.redeemer")


@dataclass(frozen=True)
class RedeemJob:
    player: dict
    code: str
    pause_after_player: bool = False


class AutoRedeemer:
    def __init__(self, repository: JsonRepository, api: KingshotApi, config: dict) -> None:
        self.repository = repository
        self.api = api
        self.config = config
        self._run_lock = asyncio.Lock()

    async def run_once(self) -> dict[str, int]:
        if self._run_lock.locked():
            logger.info("Auto redeem cycle skipped because another cycle is still running")
            return {"success": 0, "already": 0, "failed": 0, "skipped": 0}

        async with self._run_lock:
            return await self._run_once_locked()

    async def _run_once_locked(self) -> dict[str, int]:
        stats = {"success": 0, "already": 0, "failed": 0, "skipped": 0}
        active_codes = await self.api.fetch_active_gift_codes()
        if not active_codes:
            logger.info("No active gift codes found")
            return stats

        new_codes = await self.repository.update_code_cache(active_codes)
        if not new_codes:
            logger.info("No new gift codes found")
            return stats

        players = await self.repository.list_auto_redeem_players()
        random.shuffle(players)
        logger.info("Processing %s new code(s) for %s player(s)", len(new_codes), len(players))

        queue: asyncio.Queue[RedeemJob] = asyncio.Queue()
        for player_index, player in enumerate(players):
            codes_for_player = new_codes[:]
            random.shuffle(codes_for_player)
            for code_index, code in enumerate(codes_for_player):
                queue.put_nowait(
                    RedeemJob(
                        player=player,
                        code=code,
                        pause_after_player=(
                            code_index == len(codes_for_player) - 1
                            and player_index < len(players) - 1
                        ),
                    )
                )

        while not queue.empty():
            job = await queue.get()
            try:
                result = await self._redeem_for_player(job.player, job.code)
                stats[result] += 1
                if queue.empty():
                    continue
                if job.pause_after_player:
                    await self._batch_pause()
                else:
                    await self._delay_between_codes()
            finally:
                queue.task_done()

        await queue.join()

        await self.repository.log_event("auto_redeem_cycle_finished", **stats)
        return stats

    async def _redeem_for_player(self, player: dict, code: str) -> str:
        player_id = str(player["playerId"])
        redeemed_codes = {item.get("code") for item in player.get("redeemedCodes", [])}
        if code in redeemed_codes:
            return "skipped"

        result = await self.api.redeem_gift_code(player_id, code)
        if result["success"] or result["already"]:
            await self.repository.mark_redeemed(player_id, code, result)
            await self.repository.log_event(
                "code_redeemed",
                playerId=player_id,
                discordUserId=player.get("discordUserId"),
                code=code,
                already=result["already"],
            )
            return "already" if result["already"] else "success"

        await self.repository.mark_failed(player_id, code, result["message"])
        await self.repository.log_event(
            "code_redeem_failed",
            playerId=player_id,
            discordUserId=player.get("discordUserId"),
            code=code,
            message=result["message"],
        )
        await asyncio.sleep(self.config["failure_cooldown_seconds"])
        return "failed"

    async def _delay_between_codes(self) -> None:
        delay = random.triangular(
            self.config["min_delay_seconds"],
            self.config["max_delay_seconds"],
            (self.config["min_delay_seconds"] + self.config["max_delay_seconds"]) / 2,
        )
        await asyncio.sleep(delay)

    async def _batch_pause(self) -> None:
        await asyncio.sleep(
            random.uniform(
                self.config["batch_pause_min_seconds"],
                self.config["batch_pause_max_seconds"],
            )
        )
