"""
Server recreator for Discord Yoink
Recreates Discord servers from backup data
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import discord
from discord.ext import commands

from .config import Config
from .media_downloader import MediaDownloader

logger = logging.getLogger(__name__)


class ServerRecreator:
    def __init__(self, config: Config):
        self.config = config
        self.media_downloader = MediaDownloader(config)
        self.role_mapping: Dict[str, str] = {}  # old_id -> new_id
        self.channel_mapping: Dict[str, str] = {}  # old_id -> new_id
        self.stats = {
            "channels_created": 0,
            "channels_removed": 0,
            "roles_created": 0,
            "roles_removed": 0,
            "messages_restored": 0,
            "server_renamed": False,
            "errors": [],
        }

    def _get_rate_limit_delay(self, multiplier: float = 1.0) -> float:
        """Get the rate limit delay from config with optional multiplier"""
        base_delay = self.config.get("rate_limit_delay", 1.0)
        return base_delay * multiplier

    async def recreate_server(
        self,
        backup_data: Dict[str, Any],
        target_guild: discord.Guild,
        skip_media: bool = False,
    ) -> Dict[str, Any]:
        """Recreate a server from backup data"""
        logger.info(f"Starting server recreation for: {target_guild.name}")

        try:
            # Step 1: Clean up existing server to match backup
            await self._cleanup_server(backup_data, target_guild)

            # Step 2: Create roles
            await self._recreate_roles(backup_data.get("roles", {}), target_guild)

            # Step 3: Create channels and categories
            await self._recreate_channels(backup_data.get("channels", {}), target_guild)

            # Step 4: Set server settings (including renaming)
            await self._apply_server_settings(
                backup_data.get("server_info", {}), target_guild
            )

            # Step 5: Upload emojis
            if not skip_media:
                await self._recreate_emojis(backup_data.get("emojis", {}), target_guild)
                await self._recreate_stickers(
                    backup_data.get("stickers", {}), target_guild
                )

            # Step 6: Restore messages (optional, can be very slow)
            await self._restore_messages(backup_data.get("channels", {}), target_guild)

            logger.info("Server recreation completed successfully")
            return self.stats

        except Exception as e:
            logger.error(f"Server recreation failed: {e}")
            self.stats["errors"].append(str(e))
            raise

    async def preview_recreation(
        self, backup_data: Dict[str, Any], target_guild: discord.Guild
    ) -> Dict[str, Any]:
        """Preview what would be created during recreation"""
        preview = {
            "server_info": backup_data.get("server_info", {}),
            "roles_to_create": [],
            "channels_to_create": [],
            "roles_to_remove": [],
            "channels_to_remove": [],
            "emojis_to_upload": [],
            "stickers_to_upload": [],
            "warnings": [],
        }

        # Get backup data
        backup_channels = backup_data.get("channels", {})
        backup_roles = backup_data.get("roles", {})

        # Create sets of names that should exist
        backup_channel_names = {
            channel_data.get("name", "").lower()
            for channel_data in backup_channels.values()
            if channel_data.get("name")
        }
        backup_role_names = {
            role_data.get("name", "").lower()
            for role_data in backup_roles.values()
            if role_data.get("name")
        }

        # Analyze what would be removed
        for channel in target_guild.channels:
            if channel.name.lower() not in backup_channel_names:
                preview["channels_to_remove"].append(channel.name)

        for role in target_guild.roles:
            if role.name != "@everyone" and role.name.lower() not in backup_role_names:
                preview["roles_to_remove"].append(role.name)

        # Analyze roles to create
        existing_roles = {role.name.lower(): role for role in target_guild.roles}
        for role_id, role_data in backup_roles.items():
            role_name = role_data.get("name", "Unknown")
            if role_name.lower() in existing_roles:
                preview["warnings"].append(f"Role '{role_name}' already exists")
            else:
                preview["roles_to_create"].append(role_name)

        # Analyze channels to create
        existing_channels = {
            channel.name.lower(): channel for channel in target_guild.channels
        }
        for channel_id, channel_data in backup_channels.items():
            channel_name = channel_data.get("name", "Unknown")
            if channel_name.lower() in existing_channels:
                preview["warnings"].append(f"Channel '{channel_name}' already exists")
            else:
                preview["channels_to_create"].append(channel_name)

        # Analyze emojis
        existing_emojis = {emoji.name: emoji for emoji in target_guild.emojis}
        for emoji_id, emoji_data in backup_data.get("emojis", {}).items():
            emoji_name = emoji_data.get("name", "Unknown")
            if emoji_name in existing_emojis:
                preview["warnings"].append(f"Emoji '{emoji_name}' already exists")
            else:
                preview["emojis_to_upload"].append(emoji_name)

        return preview

    async def _cleanup_server(
        self, backup_data: Dict[str, Any], guild: discord.Guild
    ) -> None:
        """Clean up existing server to match backup structure"""
        logger.info("Cleaning up server to match backup...")

        # Get channels and roles from backup
        backup_channels = backup_data.get("channels", {})
        backup_roles = backup_data.get("roles", {})

        # Create sets of names that should exist
        backup_channel_names = {
            channel_data.get("name", "").lower()
            for channel_data in backup_channels.values()
            if channel_data.get("name")
        }
        backup_role_names = {
            role_data.get("name", "").lower()
            for role_data in backup_roles.values()
            if role_data.get("name")
        }

        # Remove channels that don't exist in backup
        for channel in guild.channels:
            if channel.name.lower() not in backup_channel_names:
                try:
                    await channel.delete(reason="Removing channel not in backup")
                    logger.info(f"Removed channel: {channel.name}")
                    self.stats["channels_removed"] += 1
                    await asyncio.sleep(self._get_rate_limit_delay())
                except discord.Forbidden:
                    logger.warning(f"No permission to delete channel: {channel.name}")
                    self.stats["errors"].append(
                        f"No permission to delete channel: {channel.name}"
                    )
                except discord.HTTPException as e:
                    logger.error(f"Failed to delete channel {channel.name}: {e}")
                    self.stats["errors"].append(
                        f"Failed to delete channel {channel.name}: {e}"
                    )

        # Remove roles that don't exist in backup (except @everyone)
        for role in guild.roles:
            if role.name != "@everyone" and role.name.lower() not in backup_role_names:
                try:
                    await role.delete(reason="Removing role not in backup")
                    logger.info(f"Removed role: {role.name}")
                    self.stats["roles_removed"] += 1
                    await asyncio.sleep(self._get_rate_limit_delay())
                except discord.Forbidden:
                    logger.warning(f"No permission to delete role: {role.name}")
                    self.stats["errors"].append(
                        f"No permission to delete role: {role.name}"
                    )
                except discord.HTTPException as e:
                    logger.error(f"Failed to delete role {role.name}: {e}")
                    self.stats["errors"].append(
                        f"Failed to delete role {role.name}: {e}"
                    )

        logger.info("Server cleanup completed")

    async def _recreate_roles(
        self, roles_data: Dict[str, Any], guild: discord.Guild
    ) -> None:
        """Recreate server roles"""
        logger.info("Recreating roles...")

        # Sort roles by position (lowest first, excluding @everyone)
        sorted_roles = sorted(roles_data.items(), key=lambda x: x[1].get("position", 0))

        for old_role_id, role_data in sorted_roles:
            try:
                # Skip if role already exists
                existing_role = discord.utils.get(guild.roles, name=role_data["name"])
                if existing_role:
                    self.role_mapping[old_role_id] = str(existing_role.id)
                    logger.debug(f"Role '{role_data['name']}' already exists")
                    continue

                # Create role permissions
                permissions = discord.Permissions(role_data.get("permissions", 0))

                # Create role
                new_role = await guild.create_role(
                    name=role_data["name"],
                    permissions=permissions,
                    color=discord.Color(role_data.get("color", 0)),
                    hoist=role_data.get("hoist", False),
                    mentionable=role_data.get("mentionable", False),
                    reason="Server recreation from backup",
                )

                self.role_mapping[old_role_id] = str(new_role.id)
                self.stats["roles_created"] += 1

                logger.debug(f"Created role: {role_data['name']}")

                # Rate limiting
                await asyncio.sleep(1)

            except discord.Forbidden:
                logger.error(f"No permission to create role: {role_data['name']}")
                self.stats["errors"].append(
                    f"No permission to create role: {role_data['name']}"
                )
            except discord.HTTPException as e:
                logger.error(f"Failed to create role {role_data['name']}: {e}")
                self.stats["errors"].append(
                    f"Failed to create role {role_data['name']}: {e}"
                )
            except Exception as e:
                logger.error(f"Unexpected error creating role {role_data['name']}: {e}")
                self.stats["errors"].append(
                    f"Unexpected error creating role {role_data['name']}: {e}"
                )

    async def _recreate_channels(
        self, channels_data: Dict[str, Any], guild: discord.Guild
    ) -> None:
        """Recreate server channels and categories"""
        logger.info("Recreating channels...")

        # Separate categories and regular channels
        categories = {}
        regular_channels = {}

        for channel_id, channel_data in channels_data.items():
            if channel_data.get("type") == "category":
                categories[channel_id] = channel_data
            else:
                regular_channels[channel_id] = channel_data

        # Create categories first
        for old_category_id, category_data in categories.items():
            try:
                # Skip if category already exists
                existing_category = discord.utils.get(
                    guild.categories, name=category_data["name"]
                )
                if existing_category:
                    self.channel_mapping[old_category_id] = str(existing_category.id)
                    continue

                new_category = await guild.create_category(
                    name=category_data["name"],
                    position=category_data.get("position", 0),
                    reason="Server recreation from backup",
                )

                self.channel_mapping[old_category_id] = str(new_category.id)
                self.stats["channels_created"] += 1

                logger.debug(f"Created category: {category_data['name']}")
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Failed to create category {category_data['name']}: {e}")
                self.stats["errors"].append(
                    f"Failed to create category {category_data['name']}: {e}"
                )

        # Create regular channels
        for old_channel_id, channel_data in regular_channels.items():
            try:
                # Skip if channel already exists
                existing_channel = discord.utils.get(
                    guild.channels, name=channel_data["name"]
                )
                if existing_channel:
                    self.channel_mapping[old_channel_id] = str(existing_channel.id)
                    continue

                # Get category if specified
                category = None
                if (
                    channel_data.get("category_id")
                    and channel_data["category_id"] in self.channel_mapping
                ):
                    new_category_id = self.channel_mapping[channel_data["category_id"]]
                    category_channel = guild.get_channel(int(new_category_id))
                    if isinstance(category_channel, discord.CategoryChannel):
                        category = category_channel

                # Create channel based on type
                channel_type = channel_data.get("type", "text")

                if channel_type == "text":
                    new_channel = await guild.create_text_channel(
                        name=channel_data["name"],
                        topic=channel_data.get("topic"),
                        slowmode_delay=channel_data.get("slowmode_delay", 0),
                        nsfw=channel_data.get("nsfw", False),
                        category=category,
                        position=channel_data.get("position", 0),
                        reason="Server recreation from backup",
                    )

                elif channel_type == "voice":
                    new_channel = await guild.create_voice_channel(
                        name=channel_data["name"],
                        bitrate=min(
                            int(channel_data.get("bitrate", 64000)),
                            int(guild.bitrate_limit),
                        ),
                        user_limit=channel_data.get("user_limit", 0),
                        category=category,
                        position=channel_data.get("position", 0),
                        reason="Server recreation from backup",
                    )

                elif channel_type == "forum":
                    # Forum channels (newer Discord feature)
                    try:
                        new_channel = await guild.create_forum(
                            name=channel_data["name"],
                            topic=channel_data.get("topic"),
                            category=category,
                            position=channel_data.get("position", 0),
                            reason="Server recreation from backup",
                        )
                    except AttributeError:
                        # Fallback to text channel if forum not supported
                        logger.warning(
                            f"Forum channels not supported, creating text channel: {channel_data['name']}"
                        )
                        new_channel = await guild.create_text_channel(
                            name=channel_data["name"],
                            topic=channel_data.get("topic"),
                            category=category,
                            position=channel_data.get("position", 0),
                            reason="Server recreation from backup",
                        )

                else:
                    logger.warning(f"Unsupported channel type: {channel_type}")
                    continue

                self.channel_mapping[old_channel_id] = str(new_channel.id)
                self.stats["channels_created"] += 1

                logger.debug(f"Created {channel_type} channel: {channel_data['name']}")
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Failed to create channel {channel_data['name']}: {e}")
                self.stats["errors"].append(
                    f"Failed to create channel {channel_data['name']}: {e}"
                )

    async def _apply_server_settings(
        self, server_info: Dict[str, Any], guild: discord.Guild
    ) -> None:
        """Apply server settings from backup"""
        logger.info("Applying server settings...")

        try:
            # Update server name
            if server_info.get("name") and server_info["name"] != guild.name:
                await guild.edit(name=server_info["name"])
                logger.info(f"Updated server name to: {server_info['name']}")
                self.stats["server_renamed"] = True

            # Update server icon
            if (
                server_info.get("local_icon_path")
                and Path(server_info["local_icon_path"]).exists()
            ):
                with open(server_info["local_icon_path"], "rb") as f:
                    icon_data = f.read()
                await guild.edit(icon=icon_data)
                logger.debug("Updated server icon")

            # Update server banner (if available)
            if (
                server_info.get("local_banner_path")
                and Path(server_info["local_banner_path"]).exists()
            ):
                with open(server_info["local_banner_path"], "rb") as f:
                    banner_data = f.read()
                await guild.edit(banner=banner_data)
                logger.debug("Updated server banner")

            # Update server description
            if server_info.get("description"):
                await guild.edit(description=server_info["description"])

            # Note: Many server settings require specific permissions or boost levels
            # and cannot be easily recreated

        except discord.Forbidden:
            logger.warning("Insufficient permissions to update server settings")
        except Exception as e:
            logger.error(f"Failed to apply server settings: {e}")
            self.stats["errors"].append(f"Failed to apply server settings: {e}")

    async def _recreate_emojis(
        self, emojis_data: Dict[str, Any], guild: discord.Guild
    ) -> None:
        """Recreate server emojis"""
        logger.info("Recreating emojis...")

        for old_emoji_id, emoji_data in emojis_data.items():
            try:
                # Skip if emoji already exists
                existing_emoji = discord.utils.get(
                    guild.emojis, name=emoji_data["name"]
                )
                if existing_emoji:
                    continue

                # Check emoji limits (unless bypassed)
                ignore_emoji_limit = self.config.get("ignore_emoji_limit", False)
                if not ignore_emoji_limit and len(guild.emojis) >= guild.emoji_limit:
                    logger.warning("Emoji limit reached, skipping remaining emojis")
                    break
                elif ignore_emoji_limit and len(guild.emojis) >= guild.emoji_limit:
                    logger.info(
                        f"Emoji limit bypass: continuing despite {len(guild.emojis)}/{guild.emoji_limit} emojis"
                    )

                # Load emoji file
                emoji_path = emoji_data.get("local_path")
                if not emoji_path or not Path(emoji_path).exists():
                    logger.warning(f"Emoji file not found: {emoji_data['name']}")
                    continue

                with open(emoji_path, "rb") as f:
                    emoji_bytes = f.read()

                # Create emoji
                new_emoji = await guild.create_custom_emoji(
                    name=emoji_data["name"],
                    image=emoji_bytes,
                    reason="Server recreation from backup",
                )

                logger.debug(f"Created emoji: {emoji_data['name']}")
                await asyncio.sleep(self._get_rate_limit_delay())  # Rate limiting

            except discord.Forbidden:
                logger.error(f"No permission to create emoji: {emoji_data['name']}")
            except discord.HTTPException as e:
                logger.error(f"Failed to create emoji {emoji_data['name']}: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error creating emoji {emoji_data['name']}: {e}"
                )

    async def _recreate_stickers(
        self, stickers_data: Dict[str, Any], guild: discord.Guild
    ) -> None:
        """Recreate server stickers"""
        logger.info("Recreating stickers...")

        for old_sticker_id, sticker_data in stickers_data.items():
            try:
                # Skip if sticker already exists
                existing_sticker = discord.utils.get(
                    guild.stickers, name=sticker_data["name"]
                )
                if existing_sticker:
                    continue

                # Check sticker limits (unless bypassed)
                ignore_sticker_limit = self.config.get("ignore_sticker_limit", False)
                if (
                    not ignore_sticker_limit
                    and len(guild.stickers) >= guild.sticker_limit
                ):
                    logger.warning("Sticker limit reached, skipping remaining stickers")
                    break
                elif (
                    ignore_sticker_limit and len(guild.stickers) >= guild.sticker_limit
                ):
                    logger.info(
                        f"Sticker limit bypass: continuing despite {len(guild.stickers)}/{guild.sticker_limit} stickers"
                    )

                # Load sticker file
                sticker_path = sticker_data.get("local_path")
                if not sticker_path or not Path(sticker_path).exists():
                    logger.warning(f"Sticker file not found: {sticker_data['name']}")
                    continue

                with open(sticker_path, "rb") as f:
                    sticker_bytes = f.read()

                # Create sticker
                new_sticker = await guild.create_sticker(
                    name=sticker_data["name"],
                    description=sticker_data.get("description", ""),
                    emoji="📁",  # Default emoji for sticker
                    file=discord.File(fp=sticker_path),
                    reason="Server recreation from backup",
                )

                logger.debug(f"Created sticker: {sticker_data['name']}")
                await asyncio.sleep(self._get_rate_limit_delay())  # Rate limiting

            except discord.Forbidden:
                logger.error(f"No permission to create sticker: {sticker_data['name']}")
            except discord.HTTPException as e:
                logger.error(f"Failed to create sticker {sticker_data['name']}: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error creating sticker {sticker_data['name']}: {e}"
                )

    async def _restore_messages(
        self, channels_data: Dict[str, Any], guild: discord.Guild
    ) -> None:
        """Restore messages to channels with improved functionality"""
        logger.info("Restoring messages...")

        # Get configuration for message restoration
        config = self.config
        max_messages = config.get(
            "restore_max_messages", 50
        )  # Default to 50 messages per channel

        # Handle unlimited messages (0 = unlimited)
        unlimited_messages = max_messages == 0
        if unlimited_messages:
            logger.info("📝 Unlimited message restoration mode enabled")

        restore_media = config.get("restore_media", True)  # Default to restore media

        # Note: Message restoration limitations:
        # 1. Cannot restore messages with original timestamps
        # 2. Uses webhooks to approximate original authors
        # 3. Rate limits make this slow for large channels
        # 4. Cross-server forwarded messages may have limited content

        for old_channel_id, channel_data in channels_data.items():
            if old_channel_id not in self.channel_mapping:
                continue

            new_channel_id = self.channel_mapping[old_channel_id]
            channel = guild.get_channel(int(new_channel_id))

            # Only restore messages to text-based channels
            if (
                not channel
                or not hasattr(channel, "send")
                or channel.type
                not in [discord.ChannelType.text, discord.ChannelType.news]
            ):
                continue

            messages = channel_data.get("messages", [])

            if not messages:
                logger.debug(f"No messages found for channel {channel.name}")
                continue

            if unlimited_messages:
                logger.info(
                    f"Restoring ALL {len(messages)} messages in #{channel.name}"
                )
                messages_to_restore = messages
            else:
                logger.info(
                    f"Restoring up to {max_messages} messages in #{channel.name}"
                )
                messages_to_restore = (
                    messages[-max_messages:]
                    if len(messages) > max_messages
                    else messages
                )

            # Create a webhook for this channel to send messages with original usernames/avatars
            webhook = None
            try:
                # Only text channels support webhooks
                if (
                    hasattr(channel, "create_webhook")
                    and channel.type == discord.ChannelType.text
                ):
                    webhook = await channel.create_webhook(
                        name="Backup Restore", reason="Message restoration from backup"
                    )
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.warning(
                    f"Could not create webhook for #{channel.name}: {e}. Using bot messages instead."
                )

            for i, message in enumerate(messages_to_restore):
                try:
                    # Cast channel to proper type for message restoration
                    if isinstance(channel, (discord.TextChannel, discord.Thread)):
                        await self._restore_single_message(
                            message, channel, webhook, restore_media
                        )
                        self.stats["messages_restored"] += 1

                    # Rate limiting - be more aggressive to avoid hitting limits
                    if i % 5 == 0:  # Every 5 messages, longer pause
                        await asyncio.sleep(self._get_rate_limit_delay(3.0))
                    else:
                        await asyncio.sleep(self._get_rate_limit_delay())

                except Exception as e:
                    logger.error(f"Failed to restore message in #{channel.name}: {e}")
                    # Continue with other messages instead of breaking
                    continue

            # Clean up webhook
            if webhook:
                try:
                    await webhook.delete(reason="Backup restoration complete")
                except Exception as e:
                    logger.warning(f"Could not delete webhook: {e}")

            logger.info(f"Completed message restoration for #{channel.name}")
            await asyncio.sleep(
                self._get_rate_limit_delay(2.0)
            )  # Pause between channels

    async def _restore_single_message(
        self,
        message: Dict[str, Any],
        channel: Union[discord.TextChannel, discord.Thread],
        webhook: Optional[discord.Webhook],
        restore_media: bool,
    ) -> None:
        """Restore a single message to a channel"""
        username = "Unknown User"  # Default value
        try:
            content = message.get("content", "")
            author = message.get("author", {})
            username = author.get("username", "Unknown User")
            avatar_url = author.get("avatar_url")
            attachments = message.get("attachments", [])
            embeds = message.get("embeds", [])
            timestamp = message.get("timestamp", "")

            # Handle forwarded messages
            is_forwarded = message.get("reference") is not None
            forwarded_note = ""
            if is_forwarded:
                ref = message.get("reference", {})
                forwarded_note = (
                    f"*[Forwarded from #{ref.get('channel_name', 'unknown')}]*\n"
                )

            # Handle cross-server forwarded messages with metadata
            if message.get("is_cross_server_forward"):
                cross_server_info = message.get("cross_server_metadata", {})
                forwarded_note = f"*[Cross-server forward from {cross_server_info.get('guild_name', 'unknown server')}]*\n"
                if not content and cross_server_info.get("note"):
                    content = f"*{cross_server_info['note']}*"

            # Skip if no content and no attachments
            if not content and not attachments and not embeds:
                logger.debug(f"Skipping empty message from {username}")
                return

            # Prepare content with timestamp info
            if timestamp:
                formatted_time = timestamp.replace("T", " ").replace("Z", " UTC")
                footer_text = f"\n*Original time: {formatted_time}*"
            else:
                footer_text = "\n*Original time: Unknown*"

            # Combine content
            full_content = forwarded_note + content + footer_text

            # Handle attachments/media if enabled
            files_to_send = []
            if restore_media and attachments:
                for attachment in attachments[:5]:  # Limit to 5 files per message
                    file_path = attachment.get("local_path")
                    if file_path and os.path.exists(file_path):
                        try:
                            # Check file size (Discord limit is 25MB for bots)
                            if os.path.getsize(file_path) <= 25 * 1024 * 1024:
                                filename = attachment.get(
                                    "filename", os.path.basename(file_path)
                                )
                                files_to_send.append(
                                    discord.File(file_path, filename=filename)
                                )
                            else:
                                full_content += f"\n*[Attachment too large: {attachment.get('filename', 'unknown')}]*"
                        except Exception as e:
                            logger.warning(f"Could not attach file {file_path}: {e}")
                            full_content += f"\n*[Attachment unavailable: {attachment.get('filename', 'unknown')}]*"
                    else:
                        # Add note about missing attachment
                        full_content += f"\n*[Attachment not downloaded: {attachment.get('filename', 'unknown')}]*"

            # Truncate content if too long
            if len(full_content) > 2000:
                full_content = full_content[:1997] + "..."

            # Send the message
            if webhook and isinstance(channel, discord.TextChannel):
                # Use webhook for better representation
                await webhook.send(
                    content=full_content,
                    username=username,
                    avatar_url=avatar_url,
                    files=files_to_send,
                )
            else:
                # Fallback to regular bot message
                formatted_content = f"**{username}**: {full_content}"
                if len(formatted_content) > 2000:
                    formatted_content = formatted_content[:1997] + "..."

                if files_to_send:
                    await channel.send(formatted_content, files=files_to_send)
                else:
                    await channel.send(formatted_content)

        except Exception as e:
            logger.error(f"Error restoring message from {username}: {e}")
            raise
