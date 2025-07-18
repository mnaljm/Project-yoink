"""
Media downloader for Discord attachments, images, and other files
Handles downloading and organizing media files from Discord
"""

import os
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from urllib.parse import urlparse
import hashlib

from .config import Config

logger = logging.getLogger(__name__)


class MediaDownloader:
    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.downloaded_files: Dict[str, str] = {}  # URL -> local_path mapping

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem storage"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Limit filename length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[: 200 - len(ext)] + ext

        return filename

    def _get_file_hash(self, url: str) -> str:
        """Generate a hash for the URL to avoid duplicate downloads"""
        return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

    async def download_file(
        self, url: str, filename: str, base_dir: Path, max_size_mb: int = 100
    ) -> Optional[str]:
        """Download a file from URL and save to local filesystem"""
        try:
            # Check if already downloaded
            file_hash = self._get_file_hash(url)
            if file_hash in self.downloaded_files:
                return self.downloaded_files[file_hash]

            # Sanitize filename
            safe_filename = self._sanitize_filename(filename)
            file_path = base_dir / safe_filename

            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Skip if file already exists
            if file_path.exists():
                self.downloaded_files[file_hash] = str(file_path)
                return str(file_path)

            session = await self._get_session()

            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download {url}: HTTP {response.status}")
                    return None

                # Check file size
                content_length = response.headers.get("content-length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > max_size_mb:
                        logger.warning(
                            f"Skipping large file {filename}: {size_mb:.2f}MB"
                        )
                        return None

                # Download file
                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)

                logger.debug(f"Downloaded: {filename}")
                self.downloaded_files[file_hash] = str(file_path)
                return str(file_path)

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None

    async def download_attachment(
        self, attachment, relative_path: str, base_dir: Path
    ) -> Optional[str]:
        """Download a Discord attachment"""
        if not self.config.download_media:
            return None

        try:
            # Use attachment's save method for better compatibility
            file_path = base_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Skip if file already exists
            if file_path.exists():
                return str(file_path)

            await attachment.save(file_path)
            logger.debug(f"Downloaded attachment: {attachment.filename}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to download attachment {attachment.filename}: {e}")
            # Fallback to URL download
            return await self.download_file(
                attachment.url,
                attachment.filename,
                base_dir / Path(relative_path).parent,
            )

    async def download_image(
        self, url: str, relative_path: str, base_dir: Optional[Path] = None
    ) -> Optional[str]:
        """Download an image from URL"""
        if not self.config.download_media:
            return None

        if base_dir is None:
            base_dir = Path.cwd()

        # Extract filename from URL if not provided in relative_path
        if not Path(relative_path).suffix:
            parsed_url = urlparse(url)
            url_filename = Path(parsed_url.path).name
            if url_filename:
                relative_path = str(Path(relative_path) / url_filename)
            else:
                # Default extension for images
                relative_path = f"{relative_path}.png"

        return await self.download_file(
            url, Path(relative_path).name, base_dir / Path(relative_path).parent
        )

    async def download_avatar(
        self, user_id: str, avatar_url: str, base_dir: Path
    ) -> Optional[str]:
        """Download a user's avatar"""
        if not avatar_url:
            return None

        # Extract format from URL
        format_ext = "png"
        if ".gif" in avatar_url:
            format_ext = "gif"
        elif ".jpg" in avatar_url or ".jpeg" in avatar_url:
            format_ext = "jpg"
        elif ".webp" in avatar_url:
            format_ext = "webp"

        filename = f"{user_id}_avatar.{format_ext}"
        return await self.download_image(avatar_url, f"avatars/{filename}", base_dir)

    async def download_emoji(
        self,
        emoji_id: str,
        emoji_name: str,
        emoji_url: str,
        animated: bool,
        base_dir: Path,
    ) -> Optional[str]:
        """Download a custom emoji"""
        format_ext = "gif" if animated else "png"
        filename = f"{emoji_name}_{emoji_id}.{format_ext}"
        return await self.download_image(emoji_url, f"emojis/{filename}", base_dir)

    async def download_sticker(
        self,
        sticker_id: str,
        sticker_name: str,
        sticker_url: str,
        sticker_format: str,
        base_dir: Path,
    ) -> Optional[str]:
        """Download a sticker"""
        format_map = {"png": "png", "apng": "png", "lottie": "json", "gif": "gif"}

        format_ext = format_map.get(sticker_format.lower(), "png")
        filename = f"{sticker_name}_{sticker_id}.{format_ext}"
        return await self.download_image(sticker_url, f"stickers/{filename}", base_dir)

    async def download_video(
        self, url: str, filename: str, base_dir: Path, max_size_mb: int = 500
    ) -> Optional[str]:
        """Download a video file"""
        if not self.config.download_media:
            return None

        return await self.download_file(url, filename, base_dir / "videos", max_size_mb)

    async def download_voice_message(
        self, url: str, filename: str, base_dir: Path
    ) -> Optional[str]:
        """Download a voice message"""
        if not self.config.download_voice_messages:
            return None

        return await self.download_file(
            url, filename, base_dir / "voice", max_size_mb=50
        )

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None
