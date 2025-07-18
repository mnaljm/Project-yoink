#!/usr/bin/env python3
"""
Discord Server Yoink - Main CLI Application
Complete Discord server backup and recreation tool
"""

import asyncio
import json
import os
import sys
from pathlib import Path
import click
from datetime import datetime

from src.discord_client import DiscordYoinkClient
from src.backup_manager import BackupManager
from src.server_recreator import ServerRecreator
from src.exporter import DataExporter
from src.config import Config
from src.utils import setup_logging, validate_permissions

__version__ = "1.1.1"


async def choose_server_interactive(client):
    """Interactive server selection for backup"""
    guilds = client.guilds

    if not guilds:
        click.echo("❌ Bot is not a member of any servers.")
        return None

    click.echo(f"\n🤖 Bot is connected to {len(guilds)} server(s):")
    click.echo("=" * 60)

    # Display servers with numbers
    for i, guild in enumerate(guilds, 1):
        member_count = guild.member_count or "Unknown"
        click.echo(f"{i:2}. 📋 {guild.name}")
        click.echo(f"     ID: {guild.id}")
        click.echo(f"     Members: {member_count} | Channels: {len(guild.channels)}")
        click.echo("-" * 40)

    # Get user choice
    while True:
        try:
            choice = click.prompt(
                f"\nSelect a server to backup (1-{len(guilds)}, or 0 to cancel)",
                type=int,
            )

            if choice == 0:
                return None
            elif 1 <= choice <= len(guilds):
                selected_guild = guilds[choice - 1]
                click.echo(
                    f"\n✅ Selected: {selected_guild.name} (ID: {selected_guild.id})"
                )
                return str(selected_guild.id)
            else:
                click.echo(
                    f"❌ Invalid choice. Please enter 1-{len(guilds)} or 0 to cancel."
                )

        except (ValueError, click.Abort):
            click.echo("\n❌ Operation cancelled.")
            return None


def choose_backup_file_interactive():
    """Interactive backup file selection"""
    import glob
    import os
    from datetime import datetime

    # Search for backup files in common locations
    backup_patterns = [
        "./backups/**/*.json",
        "./backups/*.json",
        "./**/*backup*.json",
        "./*.json",
    ]

    backup_files = []
    for pattern in backup_patterns:
        backup_files.extend(glob.glob(pattern, recursive=True))

    # Filter and validate backup files
    valid_backups = []
    for file_path in set(backup_files):  # Remove duplicates
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Check if it looks like a Discord Yoink backup
                if "server_info" in data or "channels" in data:
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size / (1024 * 1024)  # MB
                    mod_time = datetime.fromtimestamp(file_stat.st_mtime)

                    server_name = data.get("server_info", {}).get(
                        "name", "Unknown Server"
                    )
                    backup_time = data.get("timestamp", mod_time.isoformat())

                    valid_backups.append(
                        {
                            "path": file_path,
                            "server_name": server_name,
                            "backup_time": backup_time,
                            "file_size": file_size,
                            "mod_time": mod_time,
                            "stats": data.get("stats", {}),
                        }
                    )
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            continue

    if not valid_backups:
        click.echo("❌ No valid backup files found in current directory or ./backups/")
        click.echo("   Search locations:")
        for pattern in backup_patterns:
            click.echo(f"   - {pattern}")
        return None

    # Sort by modification time (newest first)
    valid_backups.sort(key=lambda x: x["mod_time"], reverse=True)

    click.echo(f"\n📁 Found {len(valid_backups)} backup file(s):")
    click.echo("=" * 80)

    # Display backup files with numbers
    for i, backup in enumerate(valid_backups, 1):
        click.echo(f"{i:2}. 💾 {backup['server_name']}")
        click.echo(f"     File: {backup['path']}")
        click.echo(f"     Backup Date: {backup['backup_time'][:19]}")
        click.echo(f"     Size: {backup['file_size']:.1f} MB")

        stats = backup["stats"]
        if stats:
            click.echo(
                f"     Messages: {stats.get('total_messages', 0):,} | "
                f"Channels: {stats.get('total_channels', 0)} | "
                f"Media: {stats.get('media_files', 0)}"
            )

        click.echo("-" * 60)

    # Get user choice
    while True:
        try:
            choice = click.prompt(
                f"\nSelect a backup file to restore (1-{len(valid_backups)}, or 0 to cancel)",
                type=int,
            )

            if choice == 0:
                return None
            elif 1 <= choice <= len(valid_backups):
                selected_backup = valid_backups[choice - 1]
                click.echo(f"\n✅ Selected backup: {selected_backup['server_name']}")
                click.echo(f"   File: {selected_backup['path']}")
                return selected_backup["path"]
            else:
                click.echo(
                    f"❌ Invalid choice. Please enter 1-{len(valid_backups)} or 0 to cancel."
                )

        except (ValueError, click.Abort):
            click.echo("\n❌ Operation cancelled.")
            return None


async def choose_target_server_interactive(client, original_server_name):
    """Interactive target server selection for recreation"""
    guilds = client.guilds

    if not guilds:
        click.echo("❌ Bot is not a member of any servers.")
        return None

    click.echo(f"\n🎯 Choose target server to recreate '{original_server_name}' into:")
    click.echo("=" * 80)

    # Display servers with numbers
    for i, guild in enumerate(guilds, 1):
        member_count = guild.member_count or "Unknown"
        click.echo(f"{i:2}. 🏠 {guild.name}")
        click.echo(f"     ID: {guild.id}")
        click.echo(f"     Members: {member_count} | Channels: {len(guild.channels)}")

        # Warn if recreating into the same server name
        if guild.name.lower() == original_server_name.lower():
            click.echo(f"     ⚠️  WARNING: Same name as original server!")

        click.echo("-" * 60)

    # Get user choice
    while True:
        try:
            choice = click.prompt(
                f"\nSelect target server for recreation (1-{len(guilds)}, or 0 to cancel)",
                type=int,
            )

            if choice == 0:
                return None
            elif 1 <= choice <= len(guilds):
                selected_guild = guilds[choice - 1]

                # Confirmation for potentially dangerous operations
                if selected_guild.name.lower() == original_server_name.lower():
                    confirm = click.confirm(
                        f"\n⚠️  You're about to recreate into a server with the same name!\n"
                        f"This will modify: {selected_guild.name}\n"
                        f"Are you sure you want to continue?"
                    )
                    if not confirm:
                        continue

                click.echo(
                    f"\n✅ Target server selected: {selected_guild.name} (ID: {selected_guild.id})"
                )
                return str(selected_guild.id)
            else:
                click.echo(
                    f"❌ Invalid choice. Please enter 1-{len(guilds)} or 0 to cancel."
                )

        except (ValueError, click.Abort):
            click.echo("\n❌ Operation cancelled.")
            return None


@click.group()
@click.version_option(version=__version__)
@click.option("--config", "-c", default="config.json", help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, config, verbose):
    """Discord Server Yoink - Complete server backup and recreation tool"""
    ctx.ensure_object(dict)

    # Setup logging
    setup_logging(verbose)

    # Load configuration
    try:
        ctx.obj["config"] = Config(config)
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--server-id", "-s", help="Discord server ID to backup")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode - choose server from list",
)
@click.option("--output", "-o", default="./backups", help="Output directory for backup")
@click.option("--incremental", is_flag=True, help="Perform incremental backup")
@click.option(
    "--channels", "-ch", multiple=True, help="Specific channels to backup (IDs)"
)
@click.pass_context
def backup(ctx, server_id, interactive, output, incremental, channels):
    """Backup a Discord server completely"""
    config = ctx.obj["config"]

    # Validate that either server_id or interactive mode is specified
    if not server_id and not interactive:
        click.echo("Error: Must specify either --server-id or --interactive", err=True)
        return

    if server_id and interactive:
        click.echo("Error: Cannot use both --server-id and --interactive", err=True)
        return

    async def run_backup():
        client = DiscordYoinkClient(config)
        start_task = None

        try:
            # Start the client in the background
            start_task = asyncio.create_task(client.start())

            # Wait for the client to be ready
            await client.wait_until_ready()

            # Interactive mode - let user choose server
            if interactive:
                server_id_chosen = await choose_server_interactive(client)
                if not server_id_chosen:
                    click.echo("No server selected. Exiting.")
                    return
            else:
                server_id_chosen = server_id

            # Validate permissions
            server = client.get_guild(int(server_id_chosen))
            if not server:
                click.echo(
                    f"Error: Cannot access server {server_id_chosen}. Check permissions.",
                    err=True,
                )
                return

            if not await validate_permissions(server, client.user):
                click.echo(
                    "Warning: Bot may not have sufficient permissions for complete backup",
                    err=True,
                )

            click.echo(f"Starting backup of server: {server.name}")
            click.echo(
                f"Channels: {len(server.channels)}, Members: {server.member_count}"
            )

            # Perform backup with proper session management
            async with BackupManager(config, output) as backup_manager:
                backup_data = await backup_manager.backup_server(
                    server,
                    client,
                    incremental=incremental,
                    channel_filter=list(channels) if channels else None,
                )

            click.echo(f"Backup completed successfully!")
            click.echo(f"Data saved to: {backup_data['backup_path']}")
            click.echo(f"Messages backed up: {backup_data['stats']['total_messages']}")
            click.echo(f"Media files downloaded: {backup_data['stats']['media_files']}")

        except Exception as e:
            click.echo(f"Backup failed: {e}", err=True)
        finally:
            # Cancel the start task and close the client
            if start_task:
                start_task.cancel()
            await client.close()

    asyncio.run(run_backup())


@cli.command()
@click.option("--backup-path", "-b", help="Path to backup file")
@click.option("--server-id", "-s", help="Target server ID for recreation")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode - choose backup file and target server",
)
@click.option("--dry-run", "-d", is_flag=True, help="Preview changes without applying")
@click.option("--skip-media", is_flag=True, help="Skip media upload during recreation")
@click.option(
    "--no-limits",
    is_flag=True,
    help="Bypass all Discord limits (restore all messages, ignore emoji/sticker limits)",
)
@click.option(
    "--max-messages",
    type=int,
    help="Maximum messages to restore per channel (0 = unlimited)",
)
@click.option(
    "--ignore-emoji-limit",
    is_flag=True,
    help="Ignore Discord emoji limits and continue creating",
)
@click.option(
    "--ignore-sticker-limit",
    is_flag=True,
    help="Ignore Discord sticker limits and continue creating",
)
@click.option(
    "--fast-mode",
    is_flag=True,
    help="Reduce rate limiting delays (may hit Discord rate limits)",
)
@click.pass_context
def recreate(
    ctx,
    backup_path,
    server_id,
    interactive,
    dry_run,
    skip_media,
    no_limits,
    max_messages,
    ignore_emoji_limit,
    ignore_sticker_limit,
    fast_mode,
):
    """Recreate a Discord server from backup"""
    config = ctx.obj["config"]

    # Validate input combinations
    if interactive:
        if backup_path or server_id:
            click.echo(
                "Error: Cannot use --backup-path or --server-id with --interactive",
                err=True,
            )
            return
    else:
        if not backup_path:
            click.echo(
                "Error: Must specify --backup-path or use --interactive mode", err=True
            )
            return
        if not server_id:
            click.echo(
                "Error: Must specify --server-id or use --interactive mode", err=True
            )
            return

    async def run_recreation():
        # Apply bypass options to config
        modified_config = config.copy()

        if no_limits:
            # Enable all bypass options when --no-limits is used
            modified_config.settings["restore_max_messages"] = 0  # 0 = unlimited
            modified_config.settings["ignore_emoji_limit"] = True
            modified_config.settings["ignore_sticker_limit"] = True
            modified_config.settings["rate_limit_delay"] = 0.1  # Fast mode
            click.echo("🚀 No limits mode enabled - bypassing all Discord limits")
        else:
            # Apply individual bypass options
            if max_messages is not None:
                modified_config.settings["restore_max_messages"] = max_messages
                if max_messages == 0:
                    click.echo("📝 Unlimited message restoration enabled")
                else:
                    click.echo(f"📝 Message limit set to {max_messages} per channel")

            if ignore_emoji_limit:
                modified_config.settings["ignore_emoji_limit"] = True
                click.echo("😀 Emoji limit bypass enabled")

            if ignore_sticker_limit:
                modified_config.settings["ignore_sticker_limit"] = True
                click.echo("🎯 Sticker limit bypass enabled")

            if fast_mode:
                modified_config.settings["rate_limit_delay"] = 0.1
                click.echo("⚡ Fast mode enabled - reduced rate limiting")

        client = DiscordYoinkClient(modified_config)
        recreator = ServerRecreator(modified_config)
        start_task = None

        try:
            # Start the client in the background
            start_task = asyncio.create_task(client.start())

            # Wait for the client to be ready
            await client.wait_until_ready()

            # Interactive mode - let user choose backup file first
            if interactive:
                backup_path_chosen = choose_backup_file_interactive()
                if not backup_path_chosen:
                    click.echo("No backup file selected. Exiting.")
                    return

                # Ask about bypass options in interactive mode
                if (
                    not no_limits
                    and not max_messages
                    and not ignore_emoji_limit
                    and not ignore_sticker_limit
                    and not fast_mode
                ):
                    click.echo("\n🎚️  Recreation Options:")
                    click.echo("=" * 50)

                    use_no_limits = click.confirm(
                        "🚀 Enable NO LIMITS mode? (Restore ALL messages, bypass Discord limits, faster speed)",
                        default=False,
                    )

                    if use_no_limits:
                        # Apply no-limits settings dynamically
                        modified_config.settings["restore_max_messages"] = (
                            0  # Unlimited
                        )
                        modified_config.settings["ignore_emoji_limit"] = True
                        modified_config.settings["ignore_sticker_limit"] = True
                        modified_config.settings["rate_limit_delay"] = 0.1  # Fast mode
                        click.echo(
                            "🚀 No limits mode enabled - bypassing all Discord limits"
                        )
                    else:
                        # Ask for individual options
                        restore_all_messages = click.confirm(
                            "📝 Restore ALL messages? (Default: only last 50 per channel)",
                            default=False,
                        )
                        if restore_all_messages:
                            modified_config.settings["restore_max_messages"] = 0
                            click.echo("📝 Unlimited message restoration enabled")

                        ignore_limits = click.confirm(
                            "🚫 Ignore Discord emoji/sticker limits?", default=False
                        )
                        if ignore_limits:
                            modified_config.settings["ignore_emoji_limit"] = True
                            modified_config.settings["ignore_sticker_limit"] = True
                            click.echo("🚫 Emoji and sticker limit bypass enabled")

                        use_fast_mode = click.confirm(
                            "⚡ Use fast mode? (Faster but may hit rate limits)",
                            default=False,
                        )
                        if use_fast_mode:
                            modified_config.settings["rate_limit_delay"] = 0.1
                            click.echo("⚡ Fast mode enabled - reduced rate limiting")

                # Recreate the client and recreator with updated config
                await client.close()
                client = DiscordYoinkClient(modified_config)
                recreator = ServerRecreator(modified_config)

                # Restart the client task
                if start_task:
                    start_task.cancel()
                start_task = asyncio.create_task(client.start())
                await client.wait_until_ready()
            else:
                backup_path_chosen = backup_path

            # Load backup data to show what we're recreating
            try:
                with open(backup_path_chosen, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
            except FileNotFoundError:
                click.echo(f"❌ Backup file not found: {backup_path_chosen}", err=True)
                return
            except json.JSONDecodeError:
                click.echo(
                    f"❌ Invalid backup file format: {backup_path_chosen}", err=True
                )
                return

            # Show backup info
            original_server_name = backup_data.get("server_info", {}).get(
                "name", "Unknown"
            )
            backup_timestamp = backup_data.get("timestamp", "Unknown")
            stats = backup_data.get("stats", {})

            click.echo(f"\n📁 Backup Info:")
            click.echo(f"   File: {backup_path_chosen}")
            click.echo(f"   Original Server: {original_server_name}")
            click.echo(f"   Backup Date: {backup_timestamp}")
            click.echo(f"   Messages: {stats.get('total_messages', 0):,}")
            click.echo(f"   Channels: {stats.get('total_channels', 0)}")
            click.echo(f"   Media Files: {stats.get('media_files', 0)}")

            # Interactive mode - let user choose target server
            if interactive:
                server_id_chosen = await choose_target_server_interactive(
                    client, original_server_name
                )
                if not server_id_chosen:
                    click.echo("No target server selected. Exiting.")
                    return
            else:
                server_id_chosen = server_id

            server = client.get_guild(int(server_id_chosen))
            if not server:
                click.echo(
                    f"Error: Cannot access target server {server_id_chosen}", err=True
                )
                return

            click.echo(f"\n🏗️  Recreating server structure from backup...")
            click.echo(f"Target server: {server.name}")

            if dry_run:
                click.echo("🔍 DRY RUN MODE - No changes will be made")
                preview = await recreator.preview_recreation(backup_data, server)

                click.echo(f"\n📋 Preview of changes:")

                # Show what would be removed
                if preview["channels_to_remove"]:
                    click.echo(
                        f"🗑️  Channels to remove ({len(preview['channels_to_remove'])}):"
                    )
                    for channel in preview["channels_to_remove"][:10]:  # Show first 10
                        click.echo(f"  - {channel}")
                    if len(preview["channels_to_remove"]) > 10:
                        click.echo(
                            f"  ... and {len(preview['channels_to_remove']) - 10} more"
                        )

                if preview["roles_to_remove"]:
                    click.echo(
                        f"🗑️  Roles to remove ({len(preview['roles_to_remove'])}):"
                    )
                    for role in preview["roles_to_remove"][:10]:  # Show first 10
                        click.echo(f"  - {role}")
                    if len(preview["roles_to_remove"]) > 10:
                        click.echo(
                            f"  ... and {len(preview['roles_to_remove']) - 10} more"
                        )

                # Show what would be created
                if preview["channels_to_create"]:
                    click.echo(
                        f"➕ Channels to create ({len(preview['channels_to_create'])}):"
                    )
                    for channel in preview["channels_to_create"][:10]:  # Show first 10
                        click.echo(f"  - {channel}")
                    if len(preview["channels_to_create"]) > 10:
                        click.echo(
                            f"  ... and {len(preview['channels_to_create']) - 10} more"
                        )

                if preview["roles_to_create"]:
                    click.echo(
                        f"➕ Roles to create ({len(preview['roles_to_create'])}):"
                    )
                    for role in preview["roles_to_create"][:10]:  # Show first 10
                        click.echo(f"  - {role}")
                    if len(preview["roles_to_create"]) > 10:
                        click.echo(
                            f"  ... and {len(preview['roles_to_create']) - 10} more"
                        )

                # Show server name change
                server_info = preview["server_info"]
                if server_info.get("name") and server_info["name"] != server.name:
                    click.echo(
                        f"📝 Server would be renamed from '{server.name}' to '{server_info['name']}'"
                    )

                if preview["warnings"]:
                    click.echo(f"⚠️  Warnings ({len(preview['warnings'])}):")
                    for warning in preview["warnings"][:5]:  # Show first 5
                        click.echo(f"  - {warning}")
                    if len(preview["warnings"]) > 5:
                        click.echo(f"  ... and {len(preview['warnings']) - 5} more")
            else:
                result = await recreator.recreate_server(
                    backup_data, server, skip_media=skip_media
                )

                click.echo(f"\n✅ Recreation completed!")
                click.echo(f"Channels removed: {result['channels_removed']}")
                click.echo(f"Roles removed: {result['roles_removed']}")
                click.echo(f"Channels created: {result['channels_created']}")
                click.echo(f"Roles created: {result['roles_created']}")
                click.echo(
                    f"Server renamed: {'Yes' if result['server_renamed'] else 'No'}"
                )
                click.echo(f"Messages restored: {result['messages_restored']}")

                if result["errors"]:
                    click.echo(f"⚠️  Errors encountered: {len(result['errors'])}")
                    for error in result["errors"][:5]:  # Show first 5 errors
                        click.echo(f"  - {error}")
                    if len(result["errors"]) > 5:
                        click.echo(f"  ... and {len(result['errors']) - 5} more errors")

        except Exception as e:
            click.echo(f"Recreation failed: {e}", err=True)
        finally:
            # Cancel the start task and close the client
            if start_task:
                start_task.cancel()
            await client.close()

    asyncio.run(run_recreation())


@cli.command()
@click.option("--backup-path", "-b", required=True, help="Path to backup file")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["html", "json", "csv"]),
    default="html",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path")
@click.option("--template", "-t", help="Custom template file for HTML export")
@click.pass_context
def export(ctx, backup_path, format, output, template):
    """Export backup data to various formats"""
    config = ctx.obj["config"]

    try:
        exporter = DataExporter(config)

        # Load backup data
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            server_name = backup_data.get("server_info", {}).get("name", "unknown")
            output = f"{server_name}_{timestamp}.{format}"

        click.echo(f"Exporting backup to {format.upper()} format...")

        if format == "html":
            exporter.export_to_html(backup_data, output, template)
        elif format == "json":
            exporter.export_to_json(backup_data, output)
        elif format == "csv":
            exporter.export_to_csv(backup_data, output)

        click.echo(f"Export completed: {output}")

    except Exception as e:
        click.echo(f"Export failed: {e}", err=True)


@cli.command()
@click.option("--backup-path", "-b", required=True, help="Path to backup file")
@click.pass_context
def analyze(ctx, backup_path):
    """Analyze backup data and show statistics"""
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        stats = backup_data.get("stats", {})
        server_info = backup_data.get("server_info", {})

        click.echo("=== Backup Analysis ===")
        click.echo(f"Server: {server_info.get('name', 'Unknown')}")
        click.echo(f"Backup Date: {backup_data.get('timestamp', 'Unknown')}")
        click.echo(f"Total Messages: {stats.get('total_messages', 0):,}")
        click.echo(f"Total Channels: {stats.get('total_channels', 0)}")
        click.echo(f"Total Users: {stats.get('total_users', 0)}")
        click.echo(f"Media Files: {stats.get('media_files', 0)}")
        click.echo(f"Backup Size: {stats.get('backup_size_mb', 0):.2f} MB")

        # Channel breakdown
        channels = backup_data.get("channels", {})
        click.echo("\n=== Channel Breakdown ===")
        for channel_id, channel_data in channels.items():
            channel_name = channel_data.get("name", "Unknown")
            message_count = len(channel_data.get("messages", []))
            click.echo(f"#{channel_name}: {message_count:,} messages")

    except Exception as e:
        click.echo(f"Analysis failed: {e}", err=True)


@cli.command()
@click.pass_context
def list_guilds(ctx):
    """List all guilds/servers the bot is a member of"""
    config = ctx.obj["config"]

    async def run_list_guilds():
        client = DiscordYoinkClient(config)
        start_task = None

        try:
            # Start the client in the background
            start_task = asyncio.create_task(client.start())

            # Wait for the client to be ready
            await client.wait_until_ready()

            guilds = client.guilds

            if not guilds:
                click.echo("Bot is not a member of any guilds.")
                return

            click.echo(f"Bot is a member of {len(guilds)} guild(s):")
            click.echo("=" * 60)

            for guild in guilds:
                member_count = guild.member_count or "Unknown"
                click.echo(f"📋 Server: {guild.name}")
                click.echo(f"   ID: {guild.id}")
                click.echo(f"   Members: {member_count}")
                click.echo(f"   Channels: {len(guild.channels)}")
                click.echo(f"   Owner: {guild.owner}")
                click.echo("-" * 40)

        except Exception as e:
            click.echo(f"Failed to list guilds: {e}", err=True)
        finally:
            # Cancel the start task and close the client
            if start_task:
                start_task.cancel()
            await client.close()

    asyncio.run(run_list_guilds())


if __name__ == "__main__":
    cli()
