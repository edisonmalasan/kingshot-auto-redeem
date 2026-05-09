# Kingshot Discord Bot Architecture

## Command System

The bot uses Discord slash commands through `discord.py`:

- `/register player_id`
- `/list`
- `/remove player_id`
- `/stopautoredeem player_id`
- `/startautoredeem player_id`
- `/status player_id`
- `/listallplayers` admin-only

All user-facing player detail responses are ephemeral. This prevents other Discord users in the server from seeing player ownership and redeem history.

## Admin Visibility

`/listallplayers` checks the calling Discord user ID against `config.json > admins.user_ids`.
The command is private and returns ephemeral responses. Discord global slash commands can still appear in the command picker for other users; to make it hidden in a specific server, restrict the command using Discord's server Integration command permissions for the bot.

## Permission Logic

Ownership lives in `players.json` on every player record:

```json
{
  "playerId": "222634337",
  "discordUserId": "123456789"
}
```

The bot checks this field before allowing a user to:

- remove a player
- disable auto redeem
- enable auto redeem
- view detailed status

Registration also enforces:

- maximum 2 player IDs per Discord user
- no duplicate player IDs globally
- player must exist according to `GET /player-info?playerId=...`

## JSON Storage

### `users.json`

```json
{
  "schemaVersion": 1,
  "users": {
    "123456789": {
      "discordUserId": "123456789",
      "playerIds": ["222634337"],
      "createdAt": "2026-05-08T10:00:00+00:00",
      "updatedAt": "2026-05-08T10:00:00+00:00"
    }
  }
}
```

### `players.json`

```json
{
  "schemaVersion": 1,
  "players": {
    "222634337": {
      "playerId": "222634337",
      "discordUserId": "123456789",
      "playerName": "Hathaway Noa",
      "kingdom": 1520,
      "level": 19,
      "levelRendered": "19",
      "levelRenderedDetailed": "19",
      "levelImage": 19,
      "profilePhoto": "https://got-global-avatar.akamaized.net/avatar-dev/2023/07/17/1020.png",
      "autoRedeem": true,
      "registeredAt": "2026-05-08T10:00:00+00:00",
      "updatedAt": "2026-05-08T10:00:00+00:00",
      "redeemedCodes": [
        {
          "code": "Childrenday0505",
          "redeemedAt": "2026-05-08T10:05:00+00:00",
          "message": "Redeemed successfully"
        }
      ],
      "failedCodes": {
        "EXAMPLE": {
          "attempts": 1,
          "lastFailedAt": "2026-05-08T10:05:00+00:00",
          "message": "Redeem failed"
        }
      }
    }
  }
}
```

### `codes.json`

```json
{
  "schemaVersion": 1,
  "knownCodes": {
    "Childrenday0505": {
      "code": "Childrenday0505",
      "firstSeenAt": "2026-05-08T10:00:00+00:00",
      "lastSeenAt": "2026-05-08T10:00:00+00:00"
    }
  },
  "lastFetchedAt": "2026-05-08T10:00:00+00:00"
}
```

### `logs.jsonl`

Each line is one JSON event:

```json
{
  "timestamp": "2026-05-08T10:05:00+00:00",
  "event": "code_redeemed",
  "playerId": "222634337",
  "discordUserId": "123456789",
  "code": "Childrenday0505",
  "already": false
}
```

## Background Auto Redeem Workflow

1. The Discord bot starts `auto_redeem_loop`.
2. The loop calls `GET /gift-codes`.
3. `codes.json` is updated and newly discovered codes are detected.
4. Players with `autoRedeem: true` are loaded.
5. Player order is shuffled.
6. Code order is shuffled per player.
7. Each redeem is sent one at a time through the background workflow.
8. Success and already-redeemed responses are stored in `redeemedCodes`.
9. Failures are stored in `failedCodes` and an extra cooldown is applied.
10. All notable actions are appended to `logs.jsonl`.

## Anti-Abuse And Rate Limiting

The bot includes:

- Discord slash command cooldowns per user
- registration cooldowns
- randomized delays between code redeems
- longer randomized pauses between players
- shuffled player order
- shuffled code order per player
- retry backoff on transient API failures
- failure cooldown after failed redeem attempts
- one auto redeem cycle lock so polling cycles cannot overlap

This is intended to reduce accidental bursts and keep request volume controlled. It is not a bypass for Kingshot rate limits or terms.

## Scalability Considerations

JSON is fine for a private or small server, but it has limits:

- all writes serialize through one process lock
- multiple bot instances cannot safely share the same JSON files
- large histories will make reads and writes slower
- querying logs from JSONL is manual

Recommended upgrade path:

1. SQLite for a single-host bot with hundreds or low thousands of players.
2. Postgres for multi-host or public bot deployments.
3. Redis-backed queue if redeem jobs need durable scheduling and worker scaling.
4. Separate tables for `users`, `players`, `codes`, `redeem_attempts`, and `audit_logs`.

## Security And Abuse Prevention

- Store the Discord token only in `.env`.
- Never expose detailed status publicly; use ephemeral responses.
- Enforce ownership on every player management command.
- Keep a global player index so a player cannot be claimed by two users.
- Add Discord permission checks later if you want admin-only maintenance commands.
- Avoid logging Discord tokens or raw secrets.
- Consider adding a manual `/redeemnow` command only for trusted roles.
- Add a backup job for `data/*.json` before heavy usage.
