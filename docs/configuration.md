# Discord Yoink Configuration Guide

This guide explains all configuration options available in `config.json`.

## Basic Configuration

### Discord Settings

```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "user_token": "YOUR_USER_TOKEN_HERE (OPTIONAL)"
  }
}
```

- **bot_token**: Required. Your Discord bot token from the Developer Portal.
- **user_token**: Optional. User token for enhanced permissions (use with caution).

### General Settings

```json
{
  "settings": {
    "download_media": true,
    "download_voice_messages": true,
    "backup_reactions": true,
    "backup_message_history": true,
    "max_messages_per_channel": 0,
    "rate_limit_delay": 1.0,
    "chunk_size": 100,
    "media_folder": "media",
    "backup_folder": "backups"
  }
}
```

#### Setting Details

- **download_media** (boolean): Whether to download images, videos, and files
- **download_voice_messages** (boolean): Whether to download voice messages
- **backup_reactions** (boolean): Whether to backup message reactions
- **backup_message_history** (boolean): Whether to backup message content
- **max_messages_per_channel** (integer): Maximum messages per channel (0 = unlimited)
- **rate_limit_delay** (float): Delay between API requests in seconds
- **chunk_size** (integer): Number of messages to process at once
- **media_folder** (string): Folder name for downloaded media
- **backup_folder** (string): Folder name for backup files

## Filters

### Channel Filters

```json
{
  "filters": {
    "exclude_channels": ["123456789012345678"],
    "include_only_channels": [],
    "exclude_users": ["987654321098765432"],
    "date_from": "2023-01-01T00:00:00Z",
    "date_to": "2023-12-31T23:59:59Z"
  }
}
```

#### Filter Details

- **exclude_channels**: Array of channel IDs to skip during backup
- **include_only_channels**: Array of channel IDs to backup (empty = all channels)
- **exclude_users**: Array of user IDs whose messages to skip
- **date_from**: ISO format date to start backing up messages from
- **date_to**: ISO format date to stop backing up messages

### Example Configurations

#### Minimal Backup (Text Only)

```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN"
  },
  "settings": {
    "download_media": false,
    "download_voice_messages": false,
    "backup_reactions": false,
    "max_messages_per_channel": 1000
  }
}
```

#### Complete Backup

```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN"
  },
  "settings": {
    "download_media": true,
    "download_voice_messages": true,
    "backup_reactions": true,
    "backup_message_history": true,
    "rate_limit_delay": 0.5
  }
}
```

#### Filtered Backup (Specific Channels)

```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN"
  },
  "filters": {
    "include_only_channels": [
      "123456789012345678",
      "234567890123456789"
    ],
    "date_from": "2023-01-01T00:00:00Z"
  }
}
```

## Advanced Configuration

### Rate Limiting

Discord has strict rate limits. Adjust these settings if you encounter issues:

```json
{
  "settings": {
    "rate_limit_delay": 2.0,
    "chunk_size": 50
  }
}
```

- Increase `rate_limit_delay` if you get rate limited
- Decrease `chunk_size` for more conservative API usage

### Large Server Optimization

For very large servers:

```json
{
  "settings": {
    "max_messages_per_channel": 10000,
    "chunk_size": 200,
    "download_media": false
  }
}
```

### Media Download Settings

Control what media gets downloaded:

```json
{
  "settings": {
    "download_media": true,
    "media_types": {
      "images": true,
      "videos": true,
      "audio": true,
      "documents": false
    },
    "max_file_size_mb": 100
  }
}
```

## Environment Variables

You can also use environment variables for sensitive data:

```bash
export DISCORD_BOT_TOKEN="your_token_here"
export DISCORD_USER_TOKEN="your_user_token_here"
```

Then in config.json:

```json
{
  "discord": {
    "bot_token": "${DISCORD_BOT_TOKEN}",
    "user_token": "${DISCORD_USER_TOKEN}"
  }
}
```

## Configuration Validation

Discord Yoink validates your configuration on startup. Common issues:

### Missing Bot Token
```
Error: Missing required config: discord.bot_token
```
**Solution**: Add your bot token to the config file.

### Invalid Channel ID
```
Warning: Invalid channel ID in filters
```
**Solution**: Check that channel IDs are valid Discord snowflakes.

### Rate Limit Too Low
```
Warning: Rate limit delay is very low, you may get rate limited
```
**Solution**: Increase `rate_limit_delay` to 1.0 or higher.

## Best Practices

1. **Start with conservative settings** for large servers
2. **Test with a small server first** to verify your configuration
3. **Monitor logs** for rate limit warnings
4. **Use filters** to avoid backing up unnecessary data
5. **Regular backups** rather than one-time large backups
6. **Secure your tokens** - never commit them to version control

## Configuration Templates

### Development/Testing
```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN"
  },
  "settings": {
    "max_messages_per_channel": 100,
    "download_media": false,
    "rate_limit_delay": 2.0
  }
}
```

### Production/Archive
```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN"
  },
  "settings": {
    "download_media": true,
    "backup_reactions": true,
    "rate_limit_delay": 1.0,
    "chunk_size": 100
  }
}
```
