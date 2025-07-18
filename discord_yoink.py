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
import discord

from src.discord_client import DiscordYoinkClient
from src.backup_manager import BackupManager
from src.server_recreator import ServerRecreator
from src.exporter import DataExporter
from src.config import Config
from src.utils import setup_logging, validate_permissions
from src.backup_chain import BackupChain, choose_backup_chain_interactive

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
                    backup_time = data.get("backup_info", {}).get(
                        "timestamp"
                    ) or data.get("timestamp", mod_time.isoformat())
                    is_incremental = data.get("backup_info", {}).get(
                        "incremental", False
                    )

                    valid_backups.append(
                        {
                            "path": file_path,
                            "server_name": server_name,
                            "backup_time": backup_time,
                            "is_incremental": is_incremental,
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
        backup_type = "🔄 INCREMENTAL" if backup["is_incremental"] else "📦 FULL"
        click.echo(f"{i:2}. 💾 {backup['server_name']} ({backup_type})")
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
@click.option(
    "--auto-merge",
    is_flag=True,
    help="Automatically detect and merge backup chains for complete restoration",
)
@click.option(
    "--backup-chains",
    "-bc",
    is_flag=True,
    help="Interactive mode - choose from available backup chains",
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
    auto_merge,
    backup_chains,
):
    """Recreate a Discord server from backup (supports automatic backup chain merging)"""
    config = ctx.obj["config"]

    # Validate input combinations
    if interactive or backup_chains:
        if backup_path or server_id:
            click.echo(
                "Error: Cannot use --backup-path or --server-id with --interactive or --backup-chains",
                err=True,
            )
            return
    else:
        if not backup_path:
            click.echo(
                "Error: Must specify --backup-path, use --interactive, or use --backup-chains mode",
                err=True,
            )
            return
        if not server_id:
            click.echo(
                "Error: Must specify --server-id, use --interactive, or use --backup-chains mode",
                err=True,
            )
            return

    async def run_recreation():
        # Apply bypass options to config
        # Create a temporary settings dict for modifications
        temp_settings = {}

        if no_limits:
            # Enable all bypass options when --no-limits is used
            temp_settings["restore_max_messages"] = 0  # 0 = unlimited
            temp_settings["ignore_emoji_limit"] = True
            temp_settings["ignore_sticker_limit"] = True
            temp_settings["rate_limit_delay"] = 0.1  # Fast mode
            click.echo("🚀 No limits mode enabled - bypassing all Discord limits")
        else:
            # Apply individual bypass options
            if max_messages is not None:
                temp_settings["restore_max_messages"] = max_messages
                if max_messages == 0:
                    click.echo("📝 Unlimited message restoration enabled")
                else:
                    click.echo(f"📝 Message limit set to {max_messages} per channel")

            if ignore_emoji_limit:
                temp_settings["ignore_emoji_limit"] = True
                click.echo("😀 Emoji limit bypass enabled")

            if ignore_sticker_limit:
                temp_settings["ignore_sticker_limit"] = True
                click.echo("🎯 Sticker limit bypass enabled")

            if fast_mode:
                temp_settings["rate_limit_delay"] = 0.1
                click.echo("⚡ Fast mode enabled - reduced rate limiting")

        # Apply temporary settings to config
        for key, value in temp_settings.items():
            config.set(key, value)

        client = DiscordYoinkClient(config)
        recreator = ServerRecreator(config)
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
                        config.set("restore_max_messages", 0)  # Unlimited
                        config.set("ignore_emoji_limit", True)
                        config.set("ignore_sticker_limit", True)
                        config.set("rate_limit_delay", 0.1)  # Fast mode
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
                            config.set("restore_max_messages", 0)
                            click.echo("📝 Unlimited message restoration enabled")

                        ignore_limits = click.confirm(
                            "🚫 Ignore Discord emoji/sticker limits?", default=False
                        )
                        if ignore_limits:
                            config.set("ignore_emoji_limit", True)
                            config.set("ignore_sticker_limit", True)
                            click.echo("🚫 Emoji and sticker limit bypass enabled")

                        use_fast_mode = click.confirm(
                            "⚡ Use fast mode? (Faster but may hit rate limits)",
                            default=False,
                        )
                        if use_fast_mode:
                            config.set("rate_limit_delay", 0.1)
                            click.echo("⚡ Fast mode enabled - reduced rate limiting")

                # Recreate the client and recreator with updated config
                await client.close()
                client = DiscordYoinkClient(config)
                recreator = ServerRecreator(config)

                # Restart the client task
                if start_task:
                    start_task.cancel()
                start_task = asyncio.create_task(client.start())
                await client.wait_until_ready()
            elif backup_chains:
                # Backup chain mode - let user choose from available chains
                backup_path_chosen = choose_backup_chain_interactive("./backups")
                if not backup_path_chosen:
                    click.echo("No backup chain selected. Exiting.")
                    return
            else:
                backup_path_chosen = backup_path

                # Auto-merge backup chains if requested
                if auto_merge:
                    click.echo("🔗 Checking for backup chains...")
                    chain_manager = BackupChain("./backups")
                    merge_result = chain_manager.auto_merge_for_backup(
                        backup_path_chosen
                    )

                    if merge_result:
                        merged_data, merged_path = merge_result
                        click.echo(f"✅ Auto-merged backup chain: {merged_path}")
                        backup_path_chosen = merged_path
                    else:
                        click.echo(
                            "ℹ️  No backup chain found or backup is already complete"
                        )

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
            backup_timestamp = backup_data.get("backup_info", {}).get(
                "timestamp"
            ) or backup_data.get("timestamp", "Unknown")
            is_incremental = backup_data.get("backup_info", {}).get(
                "incremental", False
            )
            backup_type = "INCREMENTAL" if is_incremental else "FULL"
            stats = backup_data.get("stats", {})

            click.echo(f"\n📁 Backup Info:")
            click.echo(f"   File: {backup_path_chosen}")
            click.echo(f"   Original Server: {original_server_name}")
            click.echo(f"   Backup Type: {backup_type}")
            click.echo(f"   Backup Date: {backup_timestamp}")
            click.echo(f"   Messages: {stats.get('total_messages', 0):,}")
            click.echo(f"   Channels: {stats.get('total_channels', 0)}")
            click.echo(f"   Media Files: {stats.get('media_files', 0)}")

            # Add warning for incremental backups
            if is_incremental:
                click.echo(f"   ⚠️  WARNING: This is an incremental backup!")
                click.echo(
                    f"   ⚠️  It contains only NEW messages since the last backup."
                )
                click.echo(
                    f"   ⚠️  The server will be restored with ONLY the incremental data."
                )
                click.echo(
                    f"   ⚠️  You may want to use a FULL backup for complete restoration."
                )

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


@cli.command()
@click.option(
    "--backup-dir", "-d", default="./backups", help="Backup directory to scan"
)
@click.option("--merge-all", is_flag=True, help="Merge all discovered backup chains")
@click.option("--output-dir", "-o", help="Output directory for merged backups")
@click.pass_context
def chains(ctx, backup_dir, merge_all, output_dir):
    """Manage backup chains - view, merge, and organize backup sequences"""

    try:
        chain_manager = BackupChain(backup_dir)
        chains = chain_manager.get_chains()

        if not chains:
            click.echo("❌ No backup chains found")
            return

        click.echo(f"🔗 Found {len(chains)} backup chain(s):")
        click.echo("=" * 80)

        for i, (chain_name, chain) in enumerate(chains.items(), 1):
            chain_info = chain_manager.get_chain_info(chain)

            click.echo(f"{i}. 🔗 {chain_info['server_name']}")
            click.echo(
                f"   📦 Full backup: {chain_info['full_backup']['timestamp'][:19]}"
            )
            click.echo(f"      Path: {chain_info['full_backup']['path']}")
            click.echo(f"      Messages: {chain_info['full_backup']['messages']:,}")

            if chain_info["incremental_backups"]:
                click.echo(
                    f"   🔄 Incremental backups: {len(chain_info['incremental_backups'])}"
                )
                for j, inc_backup in enumerate(chain_info["incremental_backups"], 1):
                    click.echo(
                        f"      {j}. {inc_backup['timestamp'][:19]} - {inc_backup['messages']:,} messages"
                    )

            click.echo(f"   📊 Total messages: {chain_info['total_messages']:,}")
            click.echo(f"   📂 Total media files: {chain_info['total_media_files']:,}")
            click.echo(
                f"   📅 Date range: {chain_info['date_range']['start'][:10]} to {chain_info['date_range']['end'][:10]}"
            )
            click.echo("-" * 60)

        if merge_all:
            click.echo(f"\n🔄 Merging all {len(chains)} backup chains...")

            merged_count = 0
            for chain_name, chain in chains.items():
                try:
                    if len(chain) > 1:  # Only merge if there are incremental backups
                        merged_data = chain_manager.merge_chain(chain)

                        if output_dir:
                            backup_name = merged_data["backup_info"]["backup_name"]
                            output_path = f"{output_dir}/{backup_name}.json"
                        else:
                            output_path = None

                        saved_path = chain_manager.save_merged_backup(
                            merged_data, output_path
                        )
                        click.echo(f"✅ Merged chain: {chain_name} -> {saved_path}")
                        merged_count += 1
                    else:
                        click.echo(f"⏭️  Skipped (no incremental backups): {chain_name}")
                except Exception as e:
                    click.echo(f"❌ Failed to merge {chain_name}: {e}")

            click.echo(f"\n🎉 Merged {merged_count} backup chains successfully!")

    except Exception as e:
        click.echo(f"Failed to manage backup chains: {e}", err=True)


@cli.command()
@click.option("--server-id", "-s", help="Discord server ID")
@click.option("--user-id", "-u", help="User ID to make admin")
@click.option(
    "--role-name", "-r", default="Emergency Admin", help="Name for the admin role"
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode - choose server and user from lists",
)
@click.pass_context
def make_admin(ctx, server_id, user_id, role_name, interactive):
    """Make a user admin in a Discord server for emergency access"""
    config = ctx.obj["config"]

    # Validate parameters
    if not interactive and (not server_id or not user_id):
        click.echo(
            "❌ Error: Either use --interactive mode or provide both --server-id and --user-id",
            err=True,
        )
        return

    async def run_make_admin():
        client = DiscordYoinkClient(config)
        start_task = None

        try:
            # Start the client in the background
            start_task = asyncio.create_task(client.start())
            await client.wait_until_ready()

            # Interactive mode - let user choose server and user
            if interactive:
                server_id_chosen = await choose_server_interactive(client)
                if not server_id_chosen:
                    click.echo("No server selected. Exiting.")
                    return

                server = client.get_guild(int(server_id_chosen))
                if not server:
                    click.echo(
                        f"Error: Cannot access server {server_id_chosen}", err=True
                    )
                    return

                # Show server members for selection
                members = server.members
                if not members:
                    click.echo("❌ No members found in server.")
                    return

                click.echo(f"\n👥 Members in {server.name}:")
                click.echo("=" * 60)

                for i, member in enumerate(members[:20], 1):  # Show first 20 members
                    status = "🟢" if member.status == discord.Status.online else "⚪"
                    click.echo(f"{i:2}. {status} {member.display_name} ({member.name})")
                    click.echo(f"     ID: {member.id}")
                    click.echo("-" * 40)

                if len(members) > 20:
                    click.echo(f"... and {len(members) - 20} more members")

                # Get user choice
                while True:
                    try:
                        choice = click.prompt(
                            f"\nSelect a member to make admin (1-{min(len(members), 20)}, or 0 to cancel, or enter user ID directly)",
                            type=str,
                        )

                        if choice == "0":
                            click.echo("Operation cancelled.")
                            return

                        # Check if it's a direct user ID
                        if choice.isdigit() and len(choice) >= 10:
                            user_id_chosen = choice
                            break
                        # Check if it's a member selection
                        elif choice.isdigit():
                            choice_num = int(choice)
                            if 1 <= choice_num <= min(len(members), 20):
                                user_id_chosen = str(members[choice_num - 1].id)
                                break

                        click.echo(
                            "❌ Invalid choice. Please enter a number or user ID."
                        )
                    except (ValueError, click.Abort):
                        click.echo("\n❌ Operation cancelled.")
                        return

                # Ask for role name
                role_name_chosen = click.prompt(
                    "Enter admin role name", default="Emergency Admin", type=str
                )

            else:
                server_id_chosen = server_id
                user_id_chosen = user_id
                # Use the role_name from the parameter
                role_name_chosen = role_name
                server = client.get_guild(int(server_id_chosen))
                if not server:
                    click.echo(
                        f"Error: Cannot access server {server_id_chosen}", err=True
                    )
                    return

            # Create ServerRecreator instance
            recreator = ServerRecreator(config)

            # Confirm the action
            member = server.get_member(int(user_id_chosen))
            if member:
                display_name = member.display_name
            else:
                display_name = f"User ID {user_id_chosen}"

            click.echo(f"\n🔧 Making user admin:")
            click.echo(f"Server: {server.name}")
            click.echo(f"User: {display_name}")
            click.echo(f"Role: {role_name_chosen}")

            if not click.confirm("\nProceed with making this user admin?"):
                click.echo("Operation cancelled.")
                return

            # Make user admin
            click.echo(f"\n🔄 Creating admin role and assigning to user...")
            result = await recreator.make_user_admin(
                server, user_id_chosen, role_name_chosen
            )

            if result["success"]:
                click.echo(f"\n✅ Successfully made user admin!")
                if result["role_created"]:
                    click.echo(f"✅ Created new admin role: {role_name_chosen}")
                else:
                    click.echo(f"ℹ️  Used existing admin role: {role_name_chosen}")

                if result["user_added"]:
                    click.echo(f"✅ Added admin role to user: {display_name}")

                click.echo(f"🆔 Role ID: {result['role_id']}")
                click.echo(f"\n⚠️  IMPORTANT: This user now has full admin permissions!")
                click.echo(
                    f"Use 'discord_yoink.py remove-admin' to revoke access when no longer needed."
                )
            else:
                click.echo(f"\n❌ Failed to make user admin!")
                for error in result["errors"]:
                    click.echo(f"  - {error}")

        except Exception as e:
            click.echo(f"Operation failed: {e}", err=True)
        finally:
            if start_task:
                start_task.cancel()
            await client.close()

    asyncio.run(run_make_admin())


@cli.command()
@click.option("--server-id", "-s", help="Discord server ID")
@click.option("--user-id", "-u", help="User ID to remove admin from")
@click.option(
    "--role-name",
    "-r",
    default="Emergency Admin",
    help="Name of the admin role to remove",
)
@click.option(
    "--delete-role",
    "-d",
    is_flag=True,
    help="Delete the admin role if no one else has it",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode - choose server and user from lists",
)
@click.pass_context
def remove_admin(ctx, server_id, user_id, role_name, delete_role, interactive):
    """Remove emergency admin access from a user"""
    config = ctx.obj["config"]

    # Validate parameters
    if not interactive and (not server_id or not user_id):
        click.echo(
            "❌ Error: Either use --interactive mode or provide both --server-id and --user-id",
            err=True,
        )
        return

    async def run_remove_admin():
        client = DiscordYoinkClient(config)
        start_task = None

        try:
            # Start the client in the background
            start_task = asyncio.create_task(client.start())
            await client.wait_until_ready()

            # Interactive mode - let user choose server and user
            if interactive:
                server_id_chosen = await choose_server_interactive(client)
                if not server_id_chosen:
                    click.echo("No server selected. Exiting.")
                    return

                server = client.get_guild(int(server_id_chosen))
                if not server:
                    click.echo(
                        f"Error: Cannot access server {server_id_chosen}", err=True
                    )
                    return

                # Find admin role
                admin_role = discord.utils.get(server.roles, name=role_name)
                if not admin_role:
                    click.echo(f"❌ Admin role '{role_name}' not found in server.")
                    return

                # Show members with admin role
                members_with_role = [m for m in server.members if admin_role in m.roles]
                if not members_with_role:
                    click.echo(f"❌ No members found with admin role '{role_name}'.")
                    return

                click.echo(f"\n👥 Members with admin role '{role_name}':")
                click.echo("=" * 60)

                for i, member in enumerate(members_with_role, 1):
                    status = "🟢" if member.status == discord.Status.online else "⚪"
                    click.echo(f"{i:2}. {status} {member.display_name} ({member.name})")
                    click.echo(f"     ID: {member.id}")
                    click.echo("-" * 40)

                # Get user choice
                while True:
                    try:
                        choice = click.prompt(
                            f"\nSelect a member to remove admin from (1-{len(members_with_role)}, or 0 to cancel, or enter user ID directly)",
                            type=str,
                        )

                        if choice == "0":
                            click.echo("Operation cancelled.")
                            return

                        # Check if it's a direct user ID
                        if choice.isdigit() and len(choice) >= 10:
                            user_id_chosen = choice
                            break
                        # Check if it's a member selection
                        elif choice.isdigit():
                            choice_num = int(choice)
                            if 1 <= choice_num <= len(members_with_role):
                                user_id_chosen = str(
                                    members_with_role[choice_num - 1].id
                                )
                                break

                        click.echo(
                            "❌ Invalid choice. Please enter a number or user ID."
                        )
                    except (ValueError, click.Abort):
                        click.echo("\n❌ Operation cancelled.")
                        return

                # Ask about deleting role
                delete_role_chosen = click.confirm(
                    f"Delete admin role '{role_name}' if no one else has it?",
                    default=False,
                )

            else:
                server_id_chosen = server_id
                user_id_chosen = user_id
                delete_role_chosen = delete_role
                server = client.get_guild(int(server_id_chosen))
                if not server:
                    click.echo(
                        f"Error: Cannot access server {server_id_chosen}", err=True
                    )
                    return

            # Create ServerRecreator instance
            recreator = ServerRecreator(config)

            # Confirm the action
            member = server.get_member(int(user_id_chosen))
            if member:
                display_name = member.display_name
            else:
                display_name = f"User ID {user_id_chosen}"

            click.echo(f"\n🔧 Removing admin access:")
            click.echo(f"Server: {server.name}")
            click.echo(f"User: {display_name}")
            click.echo(f"Role: {role_name}")
            if delete_role_chosen:
                click.echo(f"⚠️  Will delete role if no one else has it")

            if not click.confirm("\nProceed with removing admin access?"):
                click.echo("Operation cancelled.")
                return

            # Remove admin access
            click.echo(f"\n🔄 Removing admin role from user...")
            result = await recreator.remove_emergency_admin(
                server, user_id_chosen, role_name, delete_role_chosen
            )

            if result["success"]:
                click.echo(f"\n✅ Successfully removed admin access!")
                if result["role_removed"]:
                    click.echo(f"✅ Removed admin role from user: {display_name}")

                if result["role_deleted"]:
                    click.echo(f"✅ Deleted admin role: {role_name}")
                elif delete_role_chosen:
                    click.echo(f"ℹ️  Admin role kept (other members still have it)")

            else:
                click.echo(f"\n❌ Failed to remove admin access!")
                for error in result["errors"]:
                    click.echo(f"  - {error}")

        except Exception as e:
            click.echo(f"Operation failed: {e}", err=True)
        finally:
            if start_task:
                start_task.cancel()
            await client.close()

    asyncio.run(run_remove_admin())


if __name__ == "__main__":
    cli()
