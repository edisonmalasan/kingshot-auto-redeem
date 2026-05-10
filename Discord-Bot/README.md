# Kingshot Auto Redeem Discord Bot

A Discord slash-command bot for managing Kingshot player registrations and redeeming new gift codes automatically.

## Features

- `/register player_id:<id>` validates a Kingshot player, stores it under the Discord user, and returns a clean player card embed.
- `/list` shows the requesting user's registered players as player card embeds.
- `/listallplayers` shows every registered player to the configured admin user only.
- `/remove player_id:<id>` removes a player only if the requester owns it.
- `/stopautoredeem player_id:<id>` disables auto redeem for an owned player.
- `/startautoredeem player_id:<id>` re-enables auto redeem for an owned player.
- `/status player_id:<id>` shows private redemption status for an owned player in expanded card mode.
- Background polling checks Kingshot gift codes and redeems new codes through a single queue.

## Player Cards

Cards use the Kingshot `profilePhoto` as the embed thumbnail and display:

- player name with `#playerId`
- kingdom
- town center / TG level
- TG level text when `levelRendered` contains `TG1` through `TG8`
- auto redeem and redemption history in expanded mode

## Admin Commands

Admin user IDs are configured in `config.json`:

```json
"admins": {
  "user_ids": ["11111111111111111"]
}
```

`/listallplayers` is blocked for everyone else at runtime. Discord may still show globally synced slash commands in the command picker unless you also restrict the command in your server's Discord Integration command permissions.

## Auto-Delete Text Channel

Normal user messages are automatically deleted in configured channels:

```json
"moderation": {
  "delete_normal_messages_channel_ids": ["1502441858347827214"]
}
```

Slash commands still work normally because they are Discord interactions, not normal text messages. The bot needs `Manage Messages` permission in the configured channel.

## Setup

Follow these steps to set up and run the application locally:

1. **Clone the repository**

   ```bash
   git clone https://github.com/edisonmalasan/kingshot-auto-redeem
   cd kingshot-auto-redeem
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Mac/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

Edit `.env` using the values from your Discord Developer Portal application:

```env
APP_ID=your-application-id
DISCORD_TOKEN=your-bot-token
PUBLIC_KEY=your-public-key
```

`APP_ID` is used as the bot application ID. `DISCORD_TOKEN` is required to run the gateway bot. `PUBLIC_KEY` is kept in the env file for Discord app completeness, but this `discord.py` bot does not need it unless you later switch to a webhook/interactions server.

How to Run:

```bash
python bot.py
```

## Storage Files

The bot stores data in `data/`:

- `users.json`: Discord users and their owned player IDs.
- `players.json`: Global player records keyed by `playerId`.
- `codes.json`: Gift code cache and discovery timestamps.
- `logs.jsonl`: Append-only event log.

The important rule is enforced globally: one `playerId` can only appear once in `players.json`, and it points to exactly one `discordUserId`.
