import re
from dataclasses import dataclass
from typing import Literal

import discord


Mode = Literal["compact", "expanded"]

DEFAULT_AVATAR_URL = "https://got-global-avatar.akamaized.net/avatar-dev/2023/07/17/1020.png"
CARD_COLOR = discord.Color.from_rgb(29, 185, 84)
TG_BADGE_PATTERN = re.compile(r"\bTG\s*([1-8])\b", re.IGNORECASE)


@dataclass(frozen=True)
class LevelDisplay:
    label: str
    is_tg: bool = False


def parse_level_display(player: dict) -> LevelDisplay:
    rendered = str(
        player.get("levelRenderedDetailed")
        or player.get("levelRendered")
        or player.get("level")
        or ""
    ).strip()
    match = TG_BADGE_PATTERN.search(rendered)
    if match:
        tg_number = match.group(1)
        return LevelDisplay(
            label=f"TG{tg_number}",
            is_tg=True,
        )

    level = _safe_int(player.get("level"))
    if level is None:
        level = _safe_int(player.get("levelRendered"))

    if level is not None and 1 <= level <= 19:
        return LevelDisplay(label=f"TC {level}")

    if rendered:
        return LevelDisplay(label=f"TC {rendered}" if rendered.isdigit() else rendered)

    return LevelDisplay(label="Unknown")


def build_player_embed(
    player: dict,
    *,
    mode: Mode = "compact",
    title_prefix: str | None = None,
) -> discord.Embed:
    level = parse_level_display(player)
    player_id = str(player.get("playerId", "?"))
    name = player.get("playerName") or player.get("name") or "Unknown Player"
    kingdom = player.get("kingdom", "?")
    auto_state = "On" if player.get("autoRedeem", True) else "Off"
    avatar_url = player.get("profilePhoto") or DEFAULT_AVATAR_URL

    title = f"{name} (#{player_id})"
    if title_prefix:
        title = f"{title_prefix} {title}"

    embed = discord.Embed(
        title=title,
        description=f":crossed_swords: K{kingdom}  •  :house: Lv. {level.label}",
        color=CARD_COLOR if player.get("autoRedeem", True) else discord.Color.dark_grey(),
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"Auto redeem: {auto_state}")

    if mode == "expanded":
        redeemed = player.get("redeemedCodes", [])
        last = redeemed[-1] if redeemed else {}
        embed.add_field(name="Player ID", value=f"`{player_id}`", inline=True)
        embed.add_field(name="Kingdom", value=f"`K{kingdom}`", inline=True)
        embed.add_field(name="Level", value=f"`{level.label}`", inline=True)
        embed.add_field(name="Auto Redeem", value=f"`{auto_state}`", inline=True)
        embed.add_field(name="Redeemed Codes", value=f"`{len(redeemed)}`", inline=True)
        embed.add_field(name="Registered", value=f"`{player.get('registeredAt', 'Unknown')}`", inline=False)
        embed.add_field(name="Last Code", value=f"`{last.get('code', 'None')}`", inline=True)
        embed.add_field(name="Last Redeem", value=f"`{last.get('redeemedAt', 'None')}`", inline=True)

    return embed


def build_player_embeds(players: list[dict], *, mode: Mode = "compact") -> list[discord.Embed]:
    return [build_player_embed(player, mode=mode) for player in players[:10]]


def _safe_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
