"""
Utility functions for Discord Yoink
Common helper functions and logging setup
"""

import logging
import sys
from typing import Any, Optional
import discord
from pathlib import Path


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Setup file handler
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / 'discord_yoink.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Reduce discord.py logging noise
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    # Reduce aiohttp logging noise
    aiohttp_logger = logging.getLogger('aiohttp')
    aiohttp_logger.setLevel(logging.WARNING)


async def validate_permissions(guild: discord.Guild, bot_user: Optional[discord.ClientUser]) -> bool:
    """Validate that the bot has sufficient permissions"""
    try:
        if not bot_user:
            return False
            
        bot_member = guild.get_member(bot_user.id)
        if not bot_member:
            return False
        
        permissions = bot_member.guild_permissions
        
        required_permissions = [
            'read_messages',
            'read_message_history',
            'view_channel',
            'connect',  # For voice channels
        ]
        
        recommended_permissions = [
            'manage_channels',
            'manage_roles',
            'manage_emojis',
            'manage_webhooks',
            'embed_links',
            'attach_files',
            'add_reactions'
        ]
        
        missing_required = []
        missing_recommended = []
        
        for perm in required_permissions:
            if not getattr(permissions, perm, False):
                missing_required.append(perm)
        
        for perm in recommended_permissions:
            if not getattr(permissions, perm, False):
                missing_recommended.append(perm)
        
        if missing_required:
            logging.error(f"Missing required permissions: {missing_required}")
            return False
        
        if missing_recommended:
            logging.warning(f"Missing recommended permissions: {missing_recommended}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error validating permissions: {e}")
        return False


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem storage"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip('. ')
    
    # Limit filename length
    if len(filename) > 200:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:200-len(ext)] + ext
    
    return filename or 'unnamed_file'


def is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
    return Path(filename).suffix.lower() in image_extensions


def is_video_file(filename: str) -> bool:
    """Check if file is a video based on extension"""
    video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v'}
    return Path(filename).suffix.lower() in video_extensions


def is_audio_file(filename: str) -> bool:
    """Check if file is an audio file based on extension"""
    audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma'}
    return Path(filename).suffix.lower() in audio_extensions


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.last_call = 0.0
    
    async def wait(self):
        """Wait if necessary to respect rate limit"""
        import time
        import asyncio
        
        now = time.time()
        time_since_last = now - self.last_call
        min_interval = 1.0 / self.calls_per_second
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_call = time.time()


class ProgressTracker:
    """Track progress of long-running operations"""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self._last_percent = -1
    
    def update(self, increment: int = 1):
        """Update progress"""
        self.current += increment
        percent = int((self.current / self.total) * 100) if self.total > 0 else 0
        
        # Only log every 10% to avoid spam
        if percent >= self._last_percent + 10:
            logging.info(f"{self.description}: {percent}% ({self.current}/{self.total})")
            self._last_percent = percent
    
    def finish(self):
        """Mark as completed"""
        logging.info(f"{self.description}: 100% ({self.total}/{self.total}) - Complete!")


def validate_discord_id(discord_id: str) -> bool:
    """Validate Discord ID format (snowflake)"""
    try:
        id_int = int(discord_id)
        # Discord IDs are 64-bit integers (snowflakes)
        return 0 < id_int < (1 << 63)
    except ValueError:
        return False


def parse_discord_timestamp(timestamp_str: str) -> Optional[Any]:
    """Parse Discord timestamp string"""
    try:
        from datetime import datetime
        # Handle both with and without timezone
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        elif '+' not in timestamp_str and timestamp_str.count(':') == 2:
            # Assume UTC if no timezone specified
            timestamp_str += '+00:00'
        
        return datetime.fromisoformat(timestamp_str)
    except Exception:
        return None


class ConfigValidator:
    """Validate configuration settings"""
    
    @staticmethod
    def validate_token(token: str) -> bool:
        """Validate Discord token format"""
        if not token or len(token) < 50:
            return False
        
        # Basic format check for bot tokens
        if token.startswith('Bot '):
            token = token[4:]
        
        # Discord tokens are base64-encoded
        try:
            import base64
            base64.b64decode(token.split('.')[0] + '==')
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_permissions_value(permissions: int) -> bool:
        """Validate Discord permissions value"""
        # Discord permissions are 64-bit integers
        return 0 <= permissions < (1 << 53)  # JavaScript safe integer limit


def chunk_list(lst: list, chunk_size: int) -> list:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


async def safe_request(func, *args, max_retries: int = 3, **kwargs):
    """Safely execute an async function with retries"""
    import asyncio
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logging.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                logging.error(f"Request failed after {max_retries} attempts: {e}")
    
    raise last_exception
