# Kingshot Auto Redeem

This repository contains two main components:

1. A Command Line Interface (CLI)
2. A Discord Bot

Both are designed for managing Kingshot player registrations and redeeming new gift codes automatically.

---

## 1. Kingshot Auto Redeem CLI

### Local Setup

Follow these steps to set up and run the application:

1. **Clone the repository**

   ```bash
   git clone https://github.com/edisonmalasan/kingshot-auto-redeem
   cd kingshot-auto-redeem/CLI
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

### How to Run

Start the application by running:

```bash
python main.py
```

### JSON State

Runtime JSON files live in `json/`:

- `json/config.json` stores app settings and API paths.
- `json/players.json` stores registered players and each player's redeemed codes.
- `json/known_codes.json` stores globally seen active codes so option 5 and auto-polling can detect new codes.

---

## 2. Kingshot Auto Redeem Discord Bot

A Discord slash-command bot for managing Kingshot player registrations and redeeming new gift codes automatically.

### Features

- `/register player_id:<id>` validates a Kingshot player, stores it under the Discord user, and returns a clean player card embed.
- `/list` shows the requesting user's registered players as player card embeds.
- `/listallplayers` shows every registered player to the configured admin user only.
- `/remove player_id:<id>` removes a player only if the requester owns it.
- `/stopautoredeem player_id:<id>` disables auto redeem for an owned player.
- `/startautoredeem player_id:<id>` re-enables auto redeem for an owned player.
- `/status player_id:<id>` shows private redemption status for an owned player in expanded card mode.
- Background polling checks Kingshot gift codes and redeems new codes through a single queue.

### Admin Commands

Admin user IDs are configured in `config.json`:

```json
"admins": {
  "user_ids": ["11111111111111111"]
}
```

`/listallplayers` is blocked for everyone else at runtime. Discord may still show globally synced slash commands in the command picker unless you also restrict the command in your server's Discord Integration command permissions.

### Setup

Follow these steps to set up and run the application locally:

1. **Navigate to the Discord Bot directory**

   ```bash
   cd kingshot-auto-redeem/Discord-Bot
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

### How to Run:

```bash
python bot.py
```

### Storage Files

The bot stores data in `data/`:

- `users.json`: Discord users and their owned player IDs.
- `players.json`: Global player records keyed by `playerId`.
- `codes.json`: Gift code cache and discovery timestamps.
- `logs.jsonl`: Append-only event log.

The important rule is enforced globally: one `playerId` can only appear once in `players.json`, and it points to exactly one `discordUserId`.

---

## License

This project is licensed under the [MIT License](LICENSE).
