"""
Backup manager for Discord servers
Handles the complete backup process including messages, media, and server structure
"""

import os
import json
import asyncio
import aiofiles
import discord
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta, timedelta
import logging
from tqdm.asyncio import tqdm

from .config import Config
from .discord_client import DiscordYoinkClient
from .media_downloader import MediaDownloader

logger = logging.getLogger(__name__)


class BackupManager:
    def __init__(self, config: Config, output_dir: str):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.media_downloader: Optional[MediaDownloader] = (
            None  # Will be initialized when needed
        )
        self.stats = {
            "total_messages": 0,
            "total_channels": 0,
            "total_users": 0,
            "media_files": 0,
            "start_time": None,
            "end_time": None,
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.media_downloader = MediaDownloader(self.config)
        await self.media_downloader.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.media_downloader:
            await self.media_downloader.__aexit__(exc_type, exc_val, exc_tb)

    async def backup_server(
        self,
        guild,
        client,
        incremental: bool = False,
        channel_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Perform complete server backup"""
        self.stats["start_time"] = datetime.now(timezone.utc)

        # Create backup directory structure
        timestamp = self.stats["start_time"].strftime("%Y%m%d_%H%M%S")
        backup_name = f"{guild.name}_{timestamp}"
        backup_dir = self.output_dir / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        media_dir = backup_dir / self.config.media_folder
        media_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting backup of server: {guild.name}")

        # Initialize backup data structure
        backup_data = {
            "backup_info": {
                "version": "1.1.1",
                "timestamp": self.stats["start_time"].isoformat(),
                "incremental": incremental,
                "backup_name": backup_name,
            },
            "server_info": {},
            "channels": {},
            "roles": {},
            "members": {},
            "emojis": {},
            "stickers": {},
            "stats": {},
        }

        try:
            # Backup server information
            logger.info("Backing up server information...")
            backup_data["server_info"] = await self._backup_server_info(
                guild, client, media_dir
            )

            # Backup roles
            logger.info("Backing up roles...")
            backup_data["roles"] = await self._backup_roles(guild, client)

            # Backup emojis
            logger.info("Backing up emojis...")
            backup_data["emojis"] = await self._backup_emojis(guild, media_dir)

            # Backup stickers
            logger.info("Backing up stickers...")
            backup_data["stickers"] = await self._backup_stickers(guild, media_dir)

            # Backup members
            logger.info("Backing up members...")
            backup_data["members"] = await self._backup_members(
                guild, client, media_dir
            )

            # Backup channels and messages
            logger.info("Backing up channels and messages...")
            backup_data["channels"] = await self._backup_channels(
                guild, client, media_dir, channel_filter, incremental
            )

            # Calculate final statistics
            self.stats["end_time"] = datetime.now(timezone.utc)
            backup_data["stats"] = self._calculate_stats(backup_dir)

            # Save backup data
            backup_file = backup_dir / "backup.json"
            async with aiofiles.open(backup_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(backup_data, indent=2, ensure_ascii=False))

            logger.info(f"Backup completed successfully: {backup_file}")

            return {
                "backup_path": str(backup_file),
                "backup_dir": str(backup_dir),
                "stats": backup_data["stats"],
            }

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise

    async def _backup_server_info(
        self, guild, client, media_dir: Path
    ) -> Dict[str, Any]:
        """Backup server information and settings"""
        try:
            server_info = await client.get_server_info(guild)

            # Download server icons/banners to backup-specific folder
            if server_info.get("icon_url") and self.media_downloader:
                icon_path = await self.media_downloader.download_image(
                    server_info["icon_url"],
                    f"server_icon.{server_info['icon_url'].split('.')[-1]}",
                    media_dir,
                )
                server_info["local_icon_path"] = icon_path

            if server_info.get("banner_url") and self.media_downloader:
                banner_path = await self.media_downloader.download_image(
                    server_info["banner_url"],
                    f"server_banner.{server_info['banner_url'].split('.')[-1]}",
                    media_dir,
                )
                server_info["local_banner_path"] = banner_path

            return server_info
        except Exception as e:
            logger.error(f"Failed to backup server info: {e}")
            return {"id": str(guild.id), "name": guild.name}

    async def _backup_roles(self, guild, client) -> Dict[str, Any]:
        """Backup all server roles"""
        roles = {}
        try:
            for role in guild.roles:
                if role.is_default():
                    continue

                role_info = await client.get_role_info(role)
                roles[str(role.id)] = role_info

            self.stats["total_roles"] = len(roles)
            logger.info(f"Backed up {len(roles)} roles")

        except Exception as e:
            logger.error(f"Failed to backup roles: {e}")

        return roles

    async def _backup_emojis(self, guild, media_dir: Path) -> Dict[str, Any]:
        """Backup all server emojis"""
        emojis = {}
        try:
            for emoji in guild.emojis:
                emoji_info = {
                    "id": str(emoji.id),
                    "name": emoji.name,
                    "animated": emoji.animated,
                    "managed": emoji.managed,
                    "available": emoji.available,
                    "created_at": emoji.created_at.isoformat(),
                    "url": str(emoji.url),
                }

                # Download emoji
                if self.config.download_media and self.media_downloader:
                    extension = "gif" if emoji.animated else "png"
                    emoji_path = await self.media_downloader.download_image(
                        str(emoji.url),
                        f"emojis/{emoji.name}_{emoji.id}.{extension}",
                        media_dir,
                    )
                    emoji_info["local_path"] = emoji_path

                emojis[str(emoji.id)] = emoji_info

            logger.info(f"Backed up {len(emojis)} emojis")

        except Exception as e:
            logger.error(f"Failed to backup emojis: {e}")

        return emojis

    async def _backup_stickers(self, guild, media_dir: Path) -> Dict[str, Any]:
        """Backup all server stickers"""
        stickers = {}
        try:
            for sticker in guild.stickers:
                sticker_info = {
                    "id": str(sticker.id),
                    "name": sticker.name,
                    "description": sticker.description,
                    "tags": sticker.tags,
                    "format": str(sticker.format),
                    "available": sticker.available,
                    "created_at": sticker.created_at.isoformat(),
                    "url": str(sticker.url),
                }

                # Download sticker
                if self.config.download_media and self.media_downloader:
                    extension = "png"  # Most stickers are PNG
                    if sticker.format.name == "lottie":
                        extension = "json"
                    elif sticker.format.name == "gif":
                        extension = "gif"

                    sticker_path = await self.media_downloader.download_image(
                        str(sticker.url),
                        f"stickers/{sticker.name}_{sticker.id}.{extension}",
                        media_dir,
                    )
                    sticker_info["local_path"] = sticker_path

                stickers[str(sticker.id)] = sticker_info

            logger.info(f"Backed up {len(stickers)} stickers")

        except Exception as e:
            logger.error(f"Failed to backup stickers: {e}")

        return stickers

    async def _backup_members(self, guild, client, media_dir: Path) -> Dict[str, Any]:
        """Backup all server members"""
        members = {}
        try:
            # Fetch all members
            if not guild.chunked:
                await guild.chunk(cache=True)

            for member in guild.members:
                if str(member.id) in self.config.exclude_users:
                    continue

                member_info = await client.get_member_info(member)

                # Download member avatar (only if enabled)
                if (
                    member_info.get("avatar_url")
                    and self.config.download_media
                    and self.config.download_avatars
                    and self.media_downloader
                ):
                    avatar_path = await self.media_downloader.download_image(
                        member_info["avatar_url"],
                        f"avatars/{member.id}_avatar.png",
                        media_dir,  # Use the backup-specific media directory
                    )
                    member_info["local_avatar_path"] = avatar_path

                members[str(member.id)] = member_info

            self.stats["total_users"] = len(members)
            logger.info(f"Backed up {len(members)} members")

        except Exception as e:
            logger.error(f"Failed to backup members: {e}")

        return members

    async def _backup_channels(
        self,
        guild,
        client,
        media_dir: Path,
        channel_filter: Optional[List[str]] = None,
        incremental: bool = False,
    ) -> Dict[str, Any]:
        """Backup all channels and their messages"""
        channels = {}

        # Get channels to backup
        channels_to_backup = []
        for channel in guild.channels:
            # Apply filters
            if channel_filter and str(channel.id) not in channel_filter:
                continue

            if str(channel.id) in self.config.exclude_channels:
                continue

            if (
                self.config.include_only_channels
                and str(channel.id) not in self.config.include_only_channels
            ):
                continue

            channels_to_backup.append(channel)

        logger.info(f"Backing up {len(channels_to_backup)} channels...")

        # Backup each channel
        for channel in tqdm(channels_to_backup, desc="Backing up channels"):
            try:
                channel_info = await client.get_channel_info(channel)

                # Backup messages for text channels
                if hasattr(channel, "history") and self.config.backup_message_history:
                    messages = await self._backup_channel_messages(
                        channel, client, media_dir, incremental
                    )
                    channel_info["messages"] = messages
                    self.stats["total_messages"] += len(messages)

                channels[str(channel.id)] = channel_info

                # Rate limiting
                await asyncio.sleep(self.config.rate_limit_delay)

            except Exception as e:
                logger.error(f"Failed to backup channel {channel.name}: {e}")
                continue

        self.stats["total_channels"] = len(channels)
        return channels

    async def _backup_channel_messages(
        self, channel, client, media_dir: Path, incremental: bool = False
    ) -> List[Dict[str, Any]]:
        """Backup all messages from a channel"""
        messages = []

        try:
            # For incremental backups, find the last backup timestamp
            last_backup_time = None
            if incremental:
                last_backup_time = await self._find_last_backup_timestamp(
                    str(channel.guild.id), str(channel.id)
                )
                if last_backup_time:
                    logger.info(
                        f"Incremental backup for #{channel.name}: "
                        f"backing up messages since {last_backup_time}"
                    )
                else:
                    logger.info(
                        f"No previous backup found for #{channel.name}, "
                        f"performing full backup"
                    )

            # Determine message limit
            limit = None
            if self.config.max_messages_per_channel > 0:
                limit = self.config.max_messages_per_channel

            # Get message history
            message_history = await client.get_channel_history(channel, limit)

            for message in tqdm(
                message_history, desc=f"Processing #{channel.name}", leave=False
            ):
                try:
                    # Apply user filter
                    if str(message.author.id) in self.config.exclude_users:
                        continue

                    # Apply incremental backup filter
                    if not self._should_backup_message(
                        message, last_backup_time, incremental
                    ):
                        continue

                    # Apply date filter
                    if self.config.date_from:
                        date_from = datetime.fromisoformat(
                            self.config.date_from.replace("Z", "+00:00")
                        )
                        if message.created_at < date_from:
                            continue

                    if self.config.date_to:
                        date_to = datetime.fromisoformat(
                            self.config.date_to.replace("Z", "+00:00")
                        )
                        if message.created_at > date_to:
                            continue

                    # Get message info
                    message_info = await client.get_message_info(message)

                    # DEBUG: Enhanced logging for forwarded messages
                    if message.reference and not message.content:
                        is_cross_server = message_info.get("reference", {}).get(
                            "cross_server", False
                        )
                        logger.debug(
                            f"Forwarded message {message.id} in #{channel.name}: "
                            f"cross_server={is_cross_server}, "
                            f"embeds={len(message.embeds)}, "
                            f"attachments={len(message.attachments)}"
                        )
                    else:
                        # Regular message debug
                        content_preview = (
                            message.content[:50] if message.content else "(empty)"
                        )
                        ref_content = (
                            message_info.get("reference", {}).get(
                                "original_content", "no ref content"
                            )[:50]
                            if message_info.get("reference")
                            else "no reference"
                        )
                        logger.debug(
                            f"Message {message.id}: main_content='{content_preview}', ref_content='{ref_content}', type={message.type}"
                        )

                    # DEBUG: Always backup all messages for now
                    # TODO: Re-enable forwarded message filtering later
                    # if (not self.config.backup_forwarded_messages and
                    #     message_info.get('reference') and
                    #     message.type in [discord.MessageType.reply, discord.MessageType.thread_starter_message]):
                    #     continue

                    # Download attachments
                    if (
                        message.attachments
                        and self.config.download_media
                        and self.media_downloader
                    ):
                        for i, attachment in enumerate(message.attachments):
                            attachment_path = await self.media_downloader.download_attachment(
                                attachment,
                                f"attachments/{channel.id}/{message.id}_{i}_{attachment.filename}",
                                media_dir,
                            )
                            if attachment_path:
                                message_info["attachments"][i][
                                    "local_path"
                                ] = attachment_path
                                self.stats["media_files"] += 1

                    messages.append(message_info)

                    # Rate limiting
                    await asyncio.sleep(self.config.rate_limit_delay / 1000)

                except Exception as e:
                    logger.error(f"Failed to backup message {message.id}: {e}")
                    continue

            logger.debug(f"Backed up {len(messages)} messages from #{channel.name}")

        except Exception as e:
            logger.error(f"Failed to backup messages from #{channel.name}: {e}")

        return messages

    def _calculate_stats(self, backup_dir: Path) -> Dict[str, Any]:
        """Calculate backup statistics"""
        backup_size = 0
        file_count = 0

        for file_path in backup_dir.rglob("*"):
            if file_path.is_file():
                backup_size += file_path.stat().st_size
                file_count += 1

        duration = None
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()

        return {
            "total_messages": self.stats["total_messages"],
            "total_channels": self.stats["total_channels"],
            "total_users": self.stats["total_users"],
            "media_files": self.stats["media_files"],
            "backup_size_bytes": backup_size,
            "backup_size_mb": round(backup_size / (1024 * 1024), 2),
            "file_count": file_count,
            "duration_seconds": duration,
            "start_time": (
                self.stats["start_time"].isoformat()
                if self.stats["start_time"]
                else None
            ),
            "end_time": (
                self.stats["end_time"].isoformat() if self.stats["end_time"] else None
            ),
        }

    async def _find_last_backup_timestamp(
        self, guild_id: str, channel_id: Optional[str] = None
    ) -> Optional[datetime]:
        """Find the timestamp of the most recent backup for incremental updates"""
        try:
            backup_dirs = []

            # Search for backup directories
            for item in self.output_dir.iterdir():
                if item.is_dir():
                    backup_json = item / "backup.json"
                    if backup_json.exists():
                        try:
                            # Read the backup file to check guild ID
                            async with aiofiles.open(
                                backup_json, "r", encoding="utf-8"
                            ) as f:
                                content = await f.read()
                                backup_data = json.loads(content)

                            # Check if this backup is for the same guild
                            backup_guild_id = backup_data.get("server_info", {}).get(
                                "id"
                            )
                            if backup_guild_id == guild_id:
                                backup_dirs.append((item, backup_json, backup_data))
                        except (json.JSONDecodeError, FileNotFoundError):
                            continue

            if not backup_dirs:
                logger.debug(f"No previous backups found for guild {guild_id}")
                return None

            # Sort by backup timestamp, get the most recent
            backup_dirs.sort(
                key=lambda x: x[2].get("backup_info", {}).get("timestamp", ""),
                reverse=True,
            )
            latest_backup_data = backup_dirs[0][2]

            # Get the timestamp from backup info
            backup_timestamp = latest_backup_data.get("backup_info", {}).get(
                "timestamp"
            )
            if backup_timestamp:
                # Parse ISO format timestamp
                last_backup_time = datetime.fromisoformat(
                    backup_timestamp.replace("Z", "+00:00")
                )
                logger.info(f"Found last backup timestamp: {last_backup_time}")
                return last_backup_time

            # Fallback: get timestamp from file modification time
            latest_backup_file = backup_dirs[0][1]
            file_mtime = datetime.fromtimestamp(
                latest_backup_file.stat().st_mtime, tz=timezone.utc
            )
            logger.info(f"Using file modification time as fallback: {file_mtime}")
            return file_mtime

        except Exception as e:
            logger.warning(f"Failed to find last backup timestamp: {e}")
            return None

    def _should_backup_message(
        self, message, last_backup_time: Optional[datetime], incremental: bool
    ) -> bool:
        """Determine if a message should be backed up based on incremental settings"""
        if not incremental or last_backup_time is None:
            return True

        # For incremental backups, only backup messages newer than last backup
        # Add a small buffer (1 minute) to ensure we don't miss messages due to timing
        buffer_time = last_backup_time - timedelta(minutes=1)
        return message.created_at > buffer_time
