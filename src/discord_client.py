"""
Discord client wrapper for the Yoink tool
Handles Discord API interactions and authentication
"""

import discord
from discord.ext import commands
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
import logging

from .config import Config

logger = logging.getLogger(__name__)


class DiscordYoinkClient(commands.Bot):
    def __init__(self, config: Config):
        self.config = config

        # Set up intents - start with default and add what we need
        intents = discord.Intents.default()

        # Enable specific intents needed for backup
        intents.message_content = True  # Required for reading message content
        intents.members = True  # Required for member information
        intents.guilds = True  # Required for guild information
        intents.guild_messages = True  # Required for message history
        intents.guild_reactions = True  # Required for reactions

        super().__init__(
            command_prefix="!yoink_",  # Unique prefix to avoid conflicts
            intents=intents,
            help_command=None,
        )

        self.session: Optional[aiohttp.ClientSession] = None
        self._ready_event = asyncio.Event()

    async def setup_hook(self) -> None:
        """Called when the bot is starting up"""
        self.session = aiohttp.ClientSession()
        logger.info("Discord client setup completed")

    async def on_ready(self) -> None:
        """Called when the bot has logged in and is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        self._ready_event.set()

    async def start(self, token: Optional[str] = None) -> None:
        """Start the Discord client"""
        if token is None:
            token = self.config.bot_token

        try:
            await super().start(token, reconnect=True)
        except discord.LoginFailure:
            raise ValueError("Invalid Discord bot token")

    async def wait_until_ready(self) -> None:
        """Wait until the bot is ready"""
        await self._ready_event.wait()

    async def close(self) -> None:
        """Close the Discord client and cleanup resources"""
        if self.session:
            await self.session.close()
        await super().close()

    async def download_attachment(
        self, attachment: discord.Attachment, save_path: str
    ) -> bool:
        """Download an attachment from Discord"""
        try:
            await attachment.save(save_path)
            logger.debug(f"Downloaded attachment: {attachment.filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to download attachment {attachment.filename}: {e}")
            return False

    async def get_channel_history(
        self, channel: discord.TextChannel, limit: Optional[int] = None
    ) -> List[discord.Message]:
        """Get message history from a channel"""
        messages = []
        try:
            async for message in channel.history(limit=limit, oldest_first=False):
                messages.append(message)

                # Add rate limiting
                await asyncio.sleep(self.config.rate_limit_delay / 1000)

            logger.info(f"Retrieved {len(messages)} messages from #{channel.name}")
            return messages
        except discord.Forbidden:
            logger.warning(f"No permission to read #{channel.name}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving messages from #{channel.name}: {e}")
            return []

    async def get_server_info(self, guild: discord.Guild) -> Dict[str, Any]:
        """Get comprehensive server information"""
        try:
            # Get server icon and banner
            icon_url = guild.icon.url if guild.icon else None
            banner_url = guild.banner.url if guild.banner else None
            splash_url = guild.splash.url if guild.splash else None

            # Get server features
            features = list(guild.features)

            # Get verification level
            verification_level = str(guild.verification_level)

            # Get explicit content filter
            explicit_content_filter = str(guild.explicit_content_filter)

            # Get MFA level
            mfa_level = guild.mfa_level

            server_info = {
                "id": str(guild.id),
                "name": guild.name,
                "description": guild.description,
                "icon_url": icon_url,
                "banner_url": banner_url,
                "splash_url": splash_url,
                "owner_id": str(guild.owner_id),
                "created_at": guild.created_at.isoformat(),
                "member_count": guild.member_count,
                "max_members": guild.max_members,
                "verification_level": verification_level,
                "explicit_content_filter": explicit_content_filter,
                "mfa_level": mfa_level,
                "features": features,
                "premium_tier": guild.premium_tier,
                "premium_subscription_count": guild.premium_subscription_count,
                "preferred_locale": str(guild.preferred_locale),
                "afk_timeout": guild.afk_timeout,
                "afk_channel_id": (
                    str(guild.afk_channel.id) if guild.afk_channel else None
                ),
                "system_channel_id": (
                    str(guild.system_channel.id) if guild.system_channel else None
                ),
                "rules_channel_id": (
                    str(guild.rules_channel.id) if guild.rules_channel else None
                ),
                "public_updates_channel_id": (
                    str(guild.public_updates_channel.id)
                    if guild.public_updates_channel
                    else None
                ),
            }

            return server_info
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            return {"id": str(guild.id), "name": guild.name}

    async def get_channel_info(
        self, channel: discord.abc.GuildChannel
    ) -> Dict[str, Any]:
        """Get comprehensive channel information"""
        channel_info = {
            "id": str(channel.id),
            "name": channel.name,
            "type": str(channel.type),
            "category_id": str(channel.category.id) if channel.category else None,
            "position": channel.position,
            "created_at": channel.created_at.isoformat(),
        }

        # Add channel-specific information
        if isinstance(channel, discord.TextChannel):
            channel_info.update(
                {
                    "topic": channel.topic,
                    "slowmode_delay": channel.slowmode_delay,
                    "nsfw": channel.nsfw,
                    "last_message_id": (
                        str(channel.last_message_id)
                        if channel.last_message_id
                        else None
                    ),
                }
            )
        elif isinstance(channel, discord.VoiceChannel):
            channel_info.update(
                {
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit,
                    "rtc_region": (
                        str(channel.rtc_region) if channel.rtc_region else None
                    ),
                }
            )
        elif isinstance(channel, discord.CategoryChannel):
            channel_info.update({"channels": [str(ch.id) for ch in channel.channels]})

        return channel_info

    async def get_role_info(self, role: discord.Role) -> Dict[str, Any]:
        """Get comprehensive role information"""
        return {
            "id": str(role.id),
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "position": role.position,
            "permissions": role.permissions.value,
            "created_at": role.created_at.isoformat(),
            "managed": role.managed,
            "tags": (
                {
                    "bot_id": (
                        str(role.tags.bot_id)
                        if role.tags and role.tags.bot_id
                        else None
                    ),
                    "integration_id": (
                        str(role.tags.integration_id)
                        if role.tags and role.tags.integration_id
                        else None
                    ),
                    "premium_subscriber": (
                        role.tags.premium_subscriber if role.tags else None
                    ),
                }
                if role.tags
                else None
            ),
        }

    async def get_member_info(self, member: discord.Member) -> Dict[str, Any]:
        """Get comprehensive member information"""
        return {
            "id": str(member.id),
            "username": member.name,
            "display_name": member.display_name,
            "discriminator": member.discriminator,
            "avatar_url": member.avatar.url if member.avatar else None,
            "banner_url": member.banner.url if member.banner else None,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "premium_since": (
                member.premium_since.isoformat() if member.premium_since else None
            ),
            "roles": [
                str(role.id)
                for role in member.roles
                if role.id != member.guild.default_role.id
            ],
            "permissions": member.guild_permissions.value,
            "bot": member.bot,
            "system": member.system,
            "created_at": member.created_at.isoformat(),
            "status": str(member.status),
            "activity": str(member.activity) if member.activity else None,
        }

    async def get_message_info(self, message: discord.Message) -> Dict[str, Any]:
        """Get comprehensive message information"""
        message_info = {
            "id": str(message.id),
            "channel_id": str(message.channel.id),
            "author": (
                await self.get_member_info(message.author)
                if isinstance(message.author, discord.Member)
                else {
                    "id": str(message.author.id),
                    "username": message.author.name,
                    "discriminator": message.author.discriminator,
                    "avatar_url": (
                        message.author.avatar.url if message.author.avatar else None
                    ),
                    "bot": message.author.bot,
                }
            ),
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
            "edited_timestamp": (
                message.edited_at.isoformat() if message.edited_at else None
            ),
            "tts": message.tts,
            "mention_everyone": message.mention_everyone,
            "mentions": [str(user.id) for user in message.mentions],
            "mention_roles": [str(role.id) for role in message.role_mentions],
            "mention_channels": [
                str(channel.id) for channel in message.channel_mentions
            ],
            "attachments": [],
            "embeds": [],
            "reactions": [],
            "pinned": message.pinned,
            "type": str(message.type),
            "flags": message.flags.value,
            "reference": None,
            "interaction": None,
            "thread": None,
            "stickers": [],
        }

        # Add attachments
        for attachment in message.attachments:
            message_info["attachments"].append(
                {
                    "id": str(attachment.id),
                    "filename": attachment.filename,
                    "size": attachment.size,
                    "url": attachment.url,
                    "proxy_url": attachment.proxy_url,
                    "content_type": attachment.content_type,
                    "width": attachment.width,
                    "height": attachment.height,
                    "ephemeral": attachment.ephemeral,
                }
            )

        # Add embeds
        for embed in message.embeds:
            embed_dict = embed.to_dict()
            message_info["embeds"].append(embed_dict)

        # Add reactions
        if self.config.backup_reactions:
            for reaction in message.reactions:
                reaction_info = {
                    "emoji": {
                        "name": (
                            reaction.emoji.name
                            if hasattr(reaction.emoji, "name")
                            else str(reaction.emoji)
                        ),
                        "id": (
                            str(reaction.emoji.id)
                            if hasattr(reaction.emoji, "id")
                            else None
                        ),
                        "animated": (
                            reaction.emoji.animated
                            if hasattr(reaction.emoji, "animated")
                            else False
                        ),
                    },
                    "count": reaction.count,
                    "users": [],
                }

                # Get users who reacted (limited for privacy)
                try:
                    async for user in reaction.users():
                        reaction_info["users"].append(str(user.id))
                        if (
                            len(reaction_info["users"]) >= 100
                        ):  # Limit to prevent excessive API calls
                            break
                except Exception as e:
                    # Log the exception and continue processing
                    # This handles cases where reaction users cannot be accessed
                    # (e.g., permissions, API rate limits, network issues)
                    print(f"Warning: Could not fetch reaction users: {e}")
                    pass

                message_info["reactions"].append(reaction_info)

        # Add message reference (replies and forwards)
        if message.reference:
            message_info["reference"] = {
                "message_id": (
                    str(message.reference.message_id)
                    if message.reference.message_id
                    else None
                ),
                "channel_id": str(message.reference.channel_id),
                "guild_id": (
                    str(message.reference.guild_id)
                    if message.reference.guild_id
                    else None
                ),
                "type": (
                    "reply"
                    if message.type == discord.MessageType.reply
                    else "reference"
                ),
            }

            # Check if this is a cross-server forward
            is_cross_server = (
                message.reference.guild_id
                and str(message.reference.guild_id) != str(message.guild.id)
                if message.guild
                else False
            )

            if is_cross_server:
                message_info["reference"]["cross_server"] = True
                # Add explanation for empty content
                if not message_info["content"]:
                    message_info["reference"][
                        "note"
                    ] = "Original text content unavailable for cross-server forwarded messages"

            # Try to get the referenced message content (for same-server forwards)
            try:
                if (
                    message.reference.resolved
                    and hasattr(message.reference.resolved, "content")
                    and isinstance(message.reference.resolved, discord.Message)
                ):
                    referenced_msg = message.reference.resolved
                    message_info["reference"][
                        "original_content"
                    ] = referenced_msg.content
                    if hasattr(referenced_msg, "author"):
                        message_info["reference"]["original_author"] = {
                            "id": str(referenced_msg.author.id),
                            "username": referenced_msg.author.name,
                            "discriminator": referenced_msg.author.discriminator,
                        }

            except Exception as e:
                logger.debug(f"Could not access referenced message: {e}")
                pass

        # Add interaction info
        if message.interaction:
            message_info["interaction"] = {
                "id": str(message.interaction.id),
                "type": str(message.interaction.type),
                "name": message.interaction.name,
                "user_id": str(message.interaction.user.id),
            }

        # Add thread info
        if hasattr(message, "thread") and message.thread:
            message_info["thread"] = {
                "id": str(message.thread.id),
                "name": message.thread.name,
                "archived": message.thread.archived,
            }

        # Add stickers
        for sticker in message.stickers:
            message_info["stickers"].append(
                {
                    "id": str(sticker.id),
                    "name": sticker.name,
                    "format": str(sticker.format),
                    "url": sticker.url,
                }
            )

        return message_info
