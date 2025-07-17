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

__version__ = "1.0.0"

@click.group()
@click.version_option(version=__version__)
@click.option('--config', '-c', default='config.json', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """Discord Server Yoink - Complete server backup and recreation tool"""
    ctx.ensure_object(dict)
    
    # Setup logging
    setup_logging(verbose)
    
    # Load configuration
    try:
        ctx.obj['config'] = Config(config)
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--server-id', '-s', required=True, help='Discord server ID to backup')
@click.option('--output', '-o', default='./backups', help='Output directory for backup')
@click.option('--incremental', '-i', is_flag=True, help='Perform incremental backup')
@click.option('--channels', '-ch', multiple=True, help='Specific channels to backup (IDs)')
@click.pass_context
def backup(ctx, server_id, output, incremental, channels):
    """Backup a Discord server completely"""
    config = ctx.obj['config']
    
    async def run_backup():
        client = DiscordYoinkClient(config)
        start_task = None
        
        try:
            # Start the client in the background
            start_task = asyncio.create_task(client.start())
            
            # Wait for the client to be ready
            await client.wait_until_ready()
            
            # Validate permissions
            server = client.get_guild(int(server_id))
            if not server:
                click.echo(f"Error: Cannot access server {server_id}. Check permissions.", err=True)
                return
            
            if not await validate_permissions(server, client.user):
                click.echo("Warning: Bot may not have sufficient permissions for complete backup", err=True)
            
            click.echo(f"Starting backup of server: {server.name}")
            click.echo(f"Channels: {len(server.channels)}, Members: {server.member_count}")
            
            # Perform backup with proper session management
            async with BackupManager(config, output) as backup_manager:
                backup_data = await backup_manager.backup_server(
                    server, 
                    client,
                    incremental=incremental,
                    channel_filter=list(channels) if channels else None
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
@click.option('--backup-path', '-b', required=True, help='Path to backup file')
@click.option('--server-id', '-s', required=True, help='Target server ID for recreation')
@click.option('--dry-run', '-d', is_flag=True, help='Preview changes without applying')
@click.option('--skip-media', is_flag=True, help='Skip media upload during recreation')
@click.pass_context
def recreate(ctx, backup_path, server_id, dry_run, skip_media):
    """Recreate a Discord server from backup"""
    config = ctx.obj['config']
    
    async def run_recreation():
        client = DiscordYoinkClient(config)
        recreator = ServerRecreator(config)
        
        try:
            await client.start()
            
            # Load backup data
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            server = client.get_guild(int(server_id))
            if not server:
                click.echo(f"Error: Cannot access target server {server_id}", err=True)
                return
            
            click.echo(f"Recreating server structure from backup...")
            click.echo(f"Target server: {server.name}")
            
            if dry_run:
                click.echo("DRY RUN MODE - No changes will be made")
                await recreator.preview_recreation(backup_data, server)
            else:
                result = await recreator.recreate_server(
                    backup_data, 
                    server, 
                    skip_media=skip_media
                )
                
                click.echo(f"Recreation completed!")
                click.echo(f"Channels created: {result['channels_created']}")
                click.echo(f"Roles created: {result['roles_created']}")
                click.echo(f"Messages restored: {result['messages_restored']}")
                
        except Exception as e:
            click.echo(f"Recreation failed: {e}", err=True)
        finally:
            await client.close()
    
    asyncio.run(run_recreation())

@cli.command()
@click.option('--backup-path', '-b', required=True, help='Path to backup file')
@click.option('--format', '-f', type=click.Choice(['html', 'json', 'csv']), default='html', help='Export format')
@click.option('--output', '-o', help='Output file path')
@click.option('--template', '-t', help='Custom template file for HTML export')
@click.pass_context
def export(ctx, backup_path, format, output, template):
    """Export backup data to various formats"""
    config = ctx.obj['config']
    
    try:
        exporter = DataExporter(config)
        
        # Load backup data
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            server_name = backup_data.get('server_info', {}).get('name', 'unknown')
            output = f"{server_name}_{timestamp}.{format}"
        
        click.echo(f"Exporting backup to {format.upper()} format...")
        
        if format == 'html':
            exporter.export_to_html(backup_data, output, template)
        elif format == 'json':
            exporter.export_to_json(backup_data, output)
        elif format == 'csv':
            exporter.export_to_csv(backup_data, output)
        
        click.echo(f"Export completed: {output}")
        
    except Exception as e:
        click.echo(f"Export failed: {e}", err=True)

@cli.command()
@click.option('--backup-path', '-b', required=True, help='Path to backup file')
@click.pass_context
def analyze(ctx, backup_path):
    """Analyze backup data and show statistics"""
    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        stats = backup_data.get('stats', {})
        server_info = backup_data.get('server_info', {})
        
        click.echo("=== Backup Analysis ===")
        click.echo(f"Server: {server_info.get('name', 'Unknown')}")
        click.echo(f"Backup Date: {backup_data.get('timestamp', 'Unknown')}")
        click.echo(f"Total Messages: {stats.get('total_messages', 0):,}")
        click.echo(f"Total Channels: {stats.get('total_channels', 0)}")
        click.echo(f"Total Users: {stats.get('total_users', 0)}")
        click.echo(f"Media Files: {stats.get('media_files', 0)}")
        click.echo(f"Backup Size: {stats.get('backup_size_mb', 0):.2f} MB")
        
        # Channel breakdown
        channels = backup_data.get('channels', {})
        click.echo("\n=== Channel Breakdown ===")
        for channel_id, channel_data in channels.items():
            channel_name = channel_data.get('name', 'Unknown')
            message_count = len(channel_data.get('messages', []))
            click.echo(f"#{channel_name}: {message_count:,} messages")
            
    except Exception as e:
        click.echo(f"Analysis failed: {e}", err=True)

if __name__ == '__main__':
    cli()
