# 🎯 Discord Yoink - Complete Server Backup & Recreation Tool

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)

**Discord Yoink** is a comprehensive tool to backup and recreate Discord servers, including messages, media, voice recordings, server structure, and settings. Perfect for server migrations, archival, or creating backups of important communities.

## ⚠️ Important Legal Notice

**This tool is for educational and backup purposes only.** 

- ✅ Only backup servers you **own** or have **explicit permission** to backup
- ✅ Respect Discord's Terms of Service and user privacy
- ✅ Use responsibly and ethically
- ❌ Do not backup servers without permission
- ❌ Do not violate Discord's ToS or user privacy

## 🌟 Features

- **Complete Message Backup**: Extract all text messages, embeds, reactions, and replies
- **Media Download**: Save all images, videos, files, and voice messages
- **Server Structure**: Backup channels, categories, roles, and permissions
- **User Data**: Preserve user information and member roles
- **Server Recreation**: Recreate the entire server structure from backup
- **Incremental Backups**: Update existing backups with new content
- **Export Formats**: JSON, HTML, and CSV export options

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Discord bot with appropriate permissions
- Active internet connection

### 📦 Installation

#### Option 1: Automated Setup (Recommended)

**Windows:**
```cmd
git clone https://github.com/mnaljm/discord-yoink.git
cd discord-yoink
setup.bat
```

**Linux/macOS:**
```bash
git clone https://github.com/mnaljm/discord-yoink.git
cd discord-yoink
chmod +x setup.sh
./setup.sh
```

#### Option 2: Manual Setup
```bash
git clone https://github.com/mnaljm/discord-yoink.git
cd discord-yoink
pip install -r requirements.txt
python setup.py
```

### 🤖 Discord Bot Setup

1. **Create a Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to "Bot" section and click "Add Bot"

2. **Enable Privileged Intents:**
   - In Bot section, enable these intents:
     - ✅ Message Content Intent
     - ✅ Server Members Intent  
     - ✅ Presence Intent (optional)

3. **Get Your Bot Token:**
   - Copy the bot token from the Bot section
   - **Keep this secret!**

4. **Configure the Tool:**
   - Copy `config.example.json` to `config.json`
   - Edit `config.json` and add your bot token:
   ```json
   {
     "discord": {
       "bot_token": "YOUR_BOT_TOKEN_HERE"
     }
   }
   ```

5. **Invite Bot to Server:**
   - Use OAuth2 URL Generator with these permissions:
     - View Channels, Read Messages, Read Message History
     - Connect (for voice channels)
     - Manage Channels, Roles, Emojis (for recreation)

### 🎯 Quick Commands

#### Backup a Server
```bash
python discord_yoink.py backup --server-id YOUR_SERVER_ID
```

Get server ID by:
1. Enable Developer Mode in Discord settings
2. Right-click your server → Copy ID

#### Export to HTML
```bash
python discord_yoink.py export --backup-path ./backups/your_backup.json --format html
```

#### Backup Specific Channels
```bash
python discord_yoink.py backup --server-id 123456789012345678 --channels 111111111111111111 222222222222222222
```

#### Recreate Server (Experimental)
```bash
python discord_yoink.py recreate --backup-path ./backups/backup.json --server-id 987654321098765432
```

#### Analyze Backup
```bash
python discord_yoink.py analyze --backup-path ./backups/backup.json
```

### 🔧 Troubleshooting

**"Bot token is invalid"**
- Check that you copied the token correctly
- Regenerate the token in Discord Developer Portal

**"Cannot access server"**
- Make sure the bot is invited to the server
- Check the server ID is correct
- Verify bot has proper permissions

**"Rate limited"**
- Increase `rate_limit_delay` in config.json
- Try backing up smaller sections at a time

**"Permission denied"**
- Bot needs "Read Message History" permission
- For private channels, bot needs explicit access

📋 **Detailed setup guide:** [Bot Setup Documentation](docs/bot_setup.md)

## 📖 Usage & Examples

Backups are saved to `./backups/SERVERNAME_TIMESTAMP/`

### Basic Commands
```bash
# Backup a server
python discord_yoink.py backup --server-id YOUR_SERVER_ID --output ./backups/

# Recreate a server (with message restoration)
python discord_yoink.py recreate --backup-path ./backups/server_backup.json --server-id NEW_SERVER_ID

# Recreate structure only (skip messages)
python discord_yoink.py recreate --backup-path ./backups/server_backup.json --server-id NEW_SERVER_ID --skip-media

# Preview recreation changes
python discord_yoink.py recreate --backup-path ./backups/server_backup.json --server-id NEW_SERVER_ID --dry-run

# Export to HTML
python discord_yoink.py export --backup-path ./backups/server_backup.json --format html
```

### Programmatic Usage

The `examples/` directory contains Python scripts showing how to use Discord Yoink programmatically:

- `basic_backup.py` - Basic server backup using the Python API
- `export_example.py` - Export backup data to HTML format

Run examples from the project root:
```bash
python examples/basic_backup.py
python examples/export_example.py
```

## ⚙️ Configuration

Copy `config.example.json` to `config.json` and customize settings:

```json
{
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN_HERE"
  },
  "settings": {
    "download_media": true,
    "backup_reactions": true,
    "max_messages_per_channel": 0,
    "rate_limit_delay": 1.0
  }
}
```

📋 **Full configuration guide:** [Configuration Documentation](docs/configuration.md)

## 🏗️ Server Recreation

Discord Yoink can recreate servers from backups with the following features:

### What Gets Restored
- ✅ **Server Structure**: Channels, categories, roles, permissions
- ✅ **Server Settings**: Icon, banner, description (where possible)
- ✅ **Emojis & Stickers**: Custom server emojis and stickers
- ✅ **Messages**: Recent messages with original usernames/avatars (via webhooks)
- ✅ **Media**: Attachments and images (if available in backup)

### Message Restoration Features
- Uses webhooks to preserve original usernames and avatars
- Configurable message limit per channel (default: 50 recent messages)
- Includes forwarded message metadata and cross-server forwarding notes
- Preserves message timestamps as notes (original timestamps cannot be restored)
- Rate-limited to respect Discord API limits

### Configuration Options
```json
{
  "settings": {
    "restore_max_messages": 50,    // Messages per channel (0 = none)
    "restore_media": true          // Include media/attachments
  }
}
```

### Recreation Limitations
- Messages restored with current timestamp (original time shown in footer)
- Cross-server forwarded content may be limited (Discord API restriction)
- Large message restorations are slow due to Discord rate limits
- Requires bot permissions on target server

## ⚠️ Limitations

### Cross-Server Forwarded Messages

When messages are forwarded from other Discord servers (cross-server forwards), Discord's API limitations prevent the bot from accessing the original content:

- **Text Content**: Not available - forwarded messages appear with empty content
- **Media/Attachments**: Not available - forwarded messages have no attachments
- **Embeds**: Not available - forwarded messages have no embed data

This is a Discord API limitation, not a bug in the tool. The backup will include:
- ✅ Metadata about the forwarded message (timestamp, author, reference info)
- ✅ Information indicating it's a cross-server forward
- ❌ Original text content, images, videos, or other media

**Workaround**: If you need the original content, you must have bot access to the source server where the original messages were posted.

### Other Limitations

- Bot requires appropriate permissions on the target server
- Rate limiting may slow down large backups
- Some Discord features (like threads, stage channels) may have limited support
- Private/DM channels cannot be backed up through server bots

## Legal Notice

This tool is for educational and backup purposes only. Ensure you have proper permissions before backing up any Discord server. Respect Discord's Terms of Service and API rate limits.
