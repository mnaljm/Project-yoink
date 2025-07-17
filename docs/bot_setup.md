# Discord Bot Setup Guide

This guide will walk you through creating a Discord bot and getting the necessary tokens for Discord Yoink.

## Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give your application a name (e.g., "Discord Yoink Bot")
4. Click "Create"

## Step 2: Create a Bot

1. In your application, go to the "Bot" section in the left sidebar
2. Click "Add Bot"
3. Confirm by clicking "Yes, do it!"

## Step 3: Get Your Bot Token

1. In the Bot section, you'll see a "Token" section
2. Click "Copy" to copy your bot token
3. **Keep this token secret!** Don't share it publicly

## Step 4: Configure Bot Permissions

In the Bot section, configure these settings:

- **Public Bot**: Disable this if you only want to use the bot yourself
- **Requires OAuth2 Code Grant**: Leave disabled

### Enable Privileged Intents (Critical)

Your bot needs **privileged intents** enabled to access message content and member information:

1. Scroll down to the **"Privileged Gateway Intents"** section
2. Enable these intents:

   ✅ **MESSAGE CONTENT INTENT**
   - Required to read message content
   - Toggle this ON

   ✅ **SERVER MEMBERS INTENT**  
   - Required to access member information
   - Toggle this ON

   ✅ **PRESENCE INTENT** (Optional)
   - Required for user status information
   - Toggle this ON (recommended)

3. Click **"Save Changes"** at the bottom
4. You might see a warning about privileged intents - click **"Yes, I understand"**

**Important:** Without these intents enabled, the bot cannot read message content or access member lists.

## Step 5: Invite Bot to Your Server

1. Go to the "OAuth2" → "URL Generator" section
2. Select these scopes:
   - `bot`
   - `applications.commands`

3. Select these bot permissions:
   - **General Permissions:**
     - View Channels
   - **Text Permissions:**
     - Send Messages
     - Read Messages
     - Read Message History
     - Embed Links
     - Attach Files
     - Add Reactions
   - **Voice Permissions:**
     - Connect
     - View Channel
   - **Advanced Permissions (for recreation):**
     - Manage Channels
     - Manage Roles
     - Manage Emojis and Stickers
     - Manage Webhooks

4. Copy the generated URL and open it in your browser
5. Select the server you want to add the bot to
6. Click "Authorize"

## Step 6: Configure Discord Yoink

1. Copy `config.example.json` to `config.json`
2. Edit `config.json` and paste your bot token:

```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN_HERE"
  }
}
```

## Important Security Notes

- **Never share your bot token publicly**
- **Don't commit your token to version control**
- **Regenerate your token if it's compromised**
- **Use environment variables for production deployments**

## Testing Your Bot

Run this command to test if your bot is working:

```bash
python discord_yoink.py backup --server-id YOUR_SERVER_ID --output ./test_backup
```

Replace `YOUR_SERVER_ID` with the ID of a server your bot has access to.

## Getting Server/Channel IDs

To get Discord IDs:

1. Enable Developer Mode in Discord:
   - User Settings → Advanced → Developer Mode
2. Right-click on servers, channels, or users to copy their IDs

## Troubleshooting

### Bot can't see messages
- Ensure "Message Content Intent" is enabled
- Check that the bot has "Read Messages" permission in the channels

### Bot can't access server
- Make sure you invited the bot with the correct permissions
- Verify the server ID is correct

### Permission errors during backup
- The bot needs "Read Message History" permission
- For voice channels, the bot needs "Connect" permission

### Recreation fails
- Ensure the bot has "Manage Channels", "Manage Roles" permissions
- Check that you're not hitting Discord's limits (channel/role limits)

## Rate Limits

Discord has rate limits to prevent spam. Discord Yoink includes built-in rate limiting, but you can adjust it in `config.json`:

```json
{
  "settings": {
    "rate_limit_delay": 1.0
  }
}
```

Increase this value if you're hitting rate limits frequently.
