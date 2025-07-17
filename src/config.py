"""
Configuration manager for Discord Yoink
Handles loading and validation of configuration settings
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        
        self.validate_config()
    
    def validate_config(self) -> None:
        """Validate required configuration keys"""
        required_keys = ['discord']
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"Missing required config section: {key}")
        
        if 'bot_token' not in self._config['discord']:
            raise ValueError("Missing required config: discord.bot_token")
    
    @property
    def bot_token(self) -> str:
        """Get Discord bot token"""
        return self._config['discord']['bot_token']
    
    @property
    def user_token(self) -> Optional[str]:
        """Get Discord user token (optional)"""
        return self._config['discord'].get('user_token')
    
    @property
    def download_media(self) -> bool:
        """Whether to download media files"""
        return self._config.get('settings', {}).get('download_media', True)
    
    @property
    def download_voice_messages(self) -> bool:
        """Whether to download voice messages"""
        return self._config.get('settings', {}).get('download_voice_messages', True)
    
    @property
    def download_avatars(self) -> bool:
        """Whether to download user avatars"""
        return self._config.get('settings', {}).get('download_avatars', False)
    
    @property
    def backup_reactions(self) -> bool:
        """Whether to backup message reactions"""
        return self._config.get('settings', {}).get('backup_reactions', True)
    
    @property
    def backup_message_history(self) -> bool:
        """Whether to backup message history"""
        return self._config.get('settings', {}).get('backup_message_history', True)
    
    @property
    def backup_forwarded_messages(self) -> bool:
        """Whether to backup forwarded messages"""
        return self._config.get('settings', {}).get('backup_forwarded_messages', True)
    
    @property
    def max_messages_per_channel(self) -> int:
        """Maximum messages to backup per channel (0 = unlimited)"""
        return self._config.get('settings', {}).get('max_messages_per_channel', 0)
    
    @property
    def rate_limit_delay(self) -> float:
        """Delay between API requests to avoid rate limiting"""
        return self._config.get('settings', {}).get('rate_limit_delay', 1.0)
    
    @property
    def chunk_size(self) -> int:
        """Number of messages to process in each chunk"""
        return self._config.get('settings', {}).get('chunk_size', 100)
    
    @property
    def media_folder(self) -> str:
        """Folder name for media files"""
        return self._config.get('settings', {}).get('media_folder', 'media')
    
    @property
    def backup_folder(self) -> str:
        """Folder name for backup files"""
        return self._config.get('settings', {}).get('backup_folder', 'backups')
    
    @property
    def exclude_channels(self) -> List[str]:
        """List of channel IDs to exclude from backup"""
        return self._config.get('filters', {}).get('exclude_channels', [])
    
    @property
    def include_only_channels(self) -> List[str]:
        """List of channel IDs to include (empty = all channels)"""
        return self._config.get('filters', {}).get('include_only_channels', [])
    
    @property
    def exclude_users(self) -> List[str]:
        """List of user IDs to exclude from backup"""
        return self._config.get('filters', {}).get('exclude_users', [])
    
    @property
    def date_from(self) -> Optional[str]:
        """Start date for message filtering (ISO format)"""
        return self._config.get('filters', {}).get('date_from')
    
    @property
    def date_to(self) -> Optional[str]:
        """End date for message filtering (ISO format)"""
        return self._config.get('filters', {}).get('date_to')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self._config[key] = value
    
    def save(self) -> None:
        """Save configuration to file"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
