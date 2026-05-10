import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

# =========================
# LOAD ENVIRONMENT VARIABLES
# =========================

ROOT = Path(__file__).resolve().parent

load_dotenv(ROOT / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env file")

# =========================
# DISCORD CONFIG
# =========================

CHANNEL_ID = 1502441858347827214

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# MESSAGE PARTS
# =========================

GUIDE_PART_1 = """
# Kingshot Auto Redeem Bot - User Guide

---

**🇬🇧/🇺🇸 English Guide**

Welcome to the Kingshot Auto Redeem Bot! 

This bot automatically redeems new Kingshot gift codes for your account using only your Player ID.

## How to use the bot

* `/register player_id:<your_player_id>` — Link your Kingshot account to Discord. This is required before using the bot.
* `/list` — View all accounts you have registered.
* `/status player_id:<your_player_id>` — Check recently redeemed gift codes for your account.
* `/stopautoredeem player_id:<your_player_id>` — Temporarily pause automatic code redemption.
* `/startautoredeem player_id:<your_player_id>` — Resume automatic code redemption.
* `/remove player_id:<your_player_id>` — Unlink and remove your Kingshot account from the bot.

💡 **Tip:** Each user can register up to **2 Kingshot accounts**. The bot will automatically manage and redeem codes for all registered accounts.

## Safety Information

✅ This bot is safe to use.

Kingshot publicly provides the official redemption API used for redeeming gift codes. This bot simply automates the redemption process whenever a new code is released by Kingshot.

The bot only uses your **Player ID** to redeem codes and does **not** require your password or account login information.

To help avoid spam or abuse, the bot also uses human-like delays between redemption requests.
"""

GUIDE_PART_2 = """
---

**🇫🇷 Guide en Français**

Bienvenue sur le Bot Kingshot Auto Redeem ! 

Ce bot réclame automatiquement les nouveaux codes cadeaux Kingshot pour votre compte en utilisant uniquement votre ID joueur.

## Comment utiliser le bot

* `/register player_id:<votre_id_joueur>` — Associez votre compte Kingshot à Discord. Cette étape est obligatoire avant d'utiliser le bot.
* `/list` — Affiche tous les comptes que vous avez enregistrés.
* `/status player_id:<votre_id_joueur>` — Vérifie les derniers codes cadeaux réclamés pour votre compte.
* `/stopautoredeem player_id:<votre_id_joueur>` — Met temporairement en pause la réclamation automatique des codes.
* `/startautoredeem player_id:<votre_id_joueur>` — Réactive la réclamation automatique des codes.
* `/remove player_id:<votre_id_joueur>` — Dissocie et supprime votre compte Kingshot du bot.

💡 **Astuce :** Chaque utilisateur peut enregistrer jusqu'à **2 comptes Kingshot**. Le bot gérera automatiquement tous les comptes enregistrés.

## Informations de sécurité

✅ Ce bot est sûr à utiliser.

Kingshot fournit publiquement l’API officielle utilisée pour réclamer les codes cadeaux. Ce bot automatise simplement le processus dès qu’un nouveau code est publié par Kingshot.

Le bot utilise uniquement votre **ID joueur** pour réclamer les récompenses et ne demande jamais votre mot de passe ou vos informations de connexion.

Afin d’éviter le spam ou les abus, le bot applique également des délais similaires à ceux d’un utilisateur humain entre chaque requête.
"""

# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    channel = bot.get_channel(CHANNEL_ID)

    if channel:
        # Send ping
        await channel.send("@everyone")

        # Send guide in multiple messages
        await channel.send(GUIDE_PART_1)
        await channel.send(GUIDE_PART_2)

        print("✅ Guide messages sent!")
    else:
        print("❌ Channel not found.")

    # Close bot automatically
    await bot.close()

# =========================
# OPTIONAL COMMAND
# =========================

@bot.command()
async def postguide(ctx):
    await ctx.send("@everyone")
    await ctx.send(GUIDE_PART_1)
    await ctx.send(GUIDE_PART_2)

# =========================
# RUN BOT
# =========================

bot.run(TOKEN)