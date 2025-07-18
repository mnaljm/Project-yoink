"""
Backup Chain Manager for Discord Yoink
Handles merging full backups with incremental backups to create complete restoration data
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import glob
import os

logger = logging.getLogger(__name__)


class BackupChain:
    """Manages backup chains (full + incremental backups)"""

    def __init__(self, backup_dir: str = "./backups"):
        self.backup_dir = Path(backup_dir)
        self.chains: Dict[str, List[Dict[str, Any]]] = {}
        self._discover_chains()

    def _discover_chains(self) -> None:
        """Discover all backup chains in the backup directory"""
        logger.info("Discovering backup chains...")

        # Find all backup files
        backup_files = []
        for pattern in ["**/*.json", "*.json"]:
            backup_files.extend(
                glob.glob(str(self.backup_dir / pattern), recursive=True)
            )

        # Group backups by server ID
        server_backups = {}

        for file_path in backup_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Check if it's a valid backup
                if "server_info" not in data:
                    continue

                server_id = data["server_info"]["id"]
                server_name = data["server_info"]["name"]
                backup_info = data.get("backup_info", {})
                is_incremental = backup_info.get("incremental", False)
                timestamp = backup_info.get("timestamp", data.get("timestamp"))

                if server_id not in server_backups:
                    server_backups[server_id] = []

                server_backups[server_id].append(
                    {
                        "path": file_path,
                        "server_name": server_name,
                        "timestamp": timestamp,
                        "is_incremental": is_incremental,
                        "backup_info": backup_info,
                        "stats": data.get("stats", {}),
                    }
                )

            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                continue

        # Create chains for each server
        for server_id, backups in server_backups.items():
            # Sort by timestamp
            backups.sort(key=lambda x: x["timestamp"])

            # Build chains
            chain = []
            current_full = None

            for backup in backups:
                if not backup["is_incremental"]:
                    # This is a full backup - start a new chain
                    if current_full and chain:
                        # Save the previous chain
                        chain_key = f"{current_full['server_name']}_{current_full['timestamp'][:19]}"
                        self.chains[chain_key] = chain.copy()

                    current_full = backup
                    chain = [backup]
                else:
                    # This is an incremental backup
                    if current_full:
                        chain.append(backup)

            # Save the final chain
            if current_full and chain:
                chain_key = (
                    f"{current_full['server_name']}_{current_full['timestamp'][:19]}"
                )
                self.chains[chain_key] = chain

        logger.info(f"Discovered {len(self.chains)} backup chains")

    def get_chains(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all discovered backup chains"""
        return self.chains

    def get_chain_for_backup(self, backup_path: str) -> Optional[List[Dict[str, Any]]]:
        """Get the chain that contains the specified backup"""
        backup_path = str(Path(backup_path).resolve())

        for chain in self.chains.values():
            for backup in chain:
                if str(Path(backup["path"]).resolve()) == backup_path:
                    return chain

        return None

    def merge_chain(self, chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a backup chain into a single complete backup"""
        if not chain:
            raise ValueError("Cannot merge empty chain")

        logger.info(f"Merging backup chain with {len(chain)} backups")

        # Start with the full backup
        full_backup = chain[0]
        if full_backup["is_incremental"]:
            raise ValueError("Chain must start with a full backup")

        # Load the full backup data
        with open(full_backup["path"], "r", encoding="utf-8") as f:
            merged_data = json.load(f)

        # Track merged statistics
        total_messages_added = 0
        total_media_added = 0

        # Apply incremental backups in order
        for incremental_backup in chain[1:]:
            if not incremental_backup["is_incremental"]:
                logger.warning(
                    f"Skipping non-incremental backup in chain: {incremental_backup['path']}"
                )
                continue

            logger.info(f"Merging incremental backup: {incremental_backup['path']}")

            # Load incremental data
            with open(incremental_backup["path"], "r", encoding="utf-8") as f:
                incremental_data = json.load(f)

            # Merge channels and messages
            incremental_channels = incremental_data.get("channels", {})

            for channel_id, channel_data in incremental_channels.items():
                if channel_id in merged_data.get("channels", {}):
                    # Channel exists - merge messages
                    existing_messages = merged_data["channels"][channel_id].get(
                        "messages", []
                    )
                    new_messages = channel_data.get("messages", [])

                    # Create a set of existing message IDs for deduplication
                    existing_msg_ids = {
                        msg.get("id") for msg in existing_messages if msg.get("id")
                    }

                    # Add new messages that don't already exist
                    messages_added = 0
                    for msg in new_messages:
                        if msg.get("id") and msg["id"] not in existing_msg_ids:
                            existing_messages.append(msg)
                            messages_added += 1

                    # Sort messages by timestamp
                    existing_messages.sort(key=lambda x: x.get("timestamp", ""))
                    merged_data["channels"][channel_id]["messages"] = existing_messages

                    total_messages_added += messages_added
                    logger.debug(
                        f"Added {messages_added} new messages to channel {channel_data.get('name', channel_id)}"
                    )
                else:
                    # New channel - add it entirely
                    if "channels" not in merged_data:
                        merged_data["channels"] = {}
                    merged_data["channels"][channel_id] = channel_data
                    total_messages_added += len(channel_data.get("messages", []))
                    logger.debug(
                        f"Added new channel: {channel_data.get('name', channel_id)}"
                    )

            # Merge other data (roles, emojis, etc.)
            for key in ["roles", "emojis", "stickers"]:
                if key in incremental_data:
                    if key not in merged_data:
                        merged_data[key] = {}
                    merged_data[key].update(incremental_data[key])

            # Update stats
            inc_stats = incremental_data.get("stats", {})
            total_media_added += inc_stats.get("media_files", 0)

        # Update merged backup info
        merged_data["backup_info"] = {
            "version": "1.1.1",
            "timestamp": datetime.now().isoformat(),
            "incremental": False,
            "backup_name": f"MERGED_{full_backup['server_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "chain_info": {
                "full_backup": full_backup["path"],
                "incremental_backups": [b["path"] for b in chain[1:]],
                "total_backups_merged": len(chain),
                "messages_added_from_incrementals": total_messages_added,
                "media_added_from_incrementals": total_media_added,
            },
        }

        # Update stats
        if "stats" not in merged_data:
            merged_data["stats"] = {}

        original_messages = merged_data["stats"].get("total_messages", 0)
        merged_data["stats"]["total_messages"] = (
            original_messages + total_messages_added
        )
        merged_data["stats"]["total_media_files"] = (
            merged_data["stats"].get("media_files", 0) + total_media_added
        )

        logger.info(
            f"Chain merge completed: {total_messages_added} messages added from {len(chain)-1} incremental backups"
        )

        return merged_data

    def save_merged_backup(
        self, merged_data: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """Save merged backup data to file"""
        if not output_path:
            backup_name = merged_data["backup_info"]["backup_name"]
            output_path = str(self.backup_dir / f"{backup_name}.json")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Merged backup saved to: {output_path}")
        return output_path

    def auto_merge_for_backup(
        self, backup_path: str
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        """
        Automatically merge the chain for a given backup.
        Returns (merged_data, output_path) or None if no chain found.
        """
        chain = self.get_chain_for_backup(backup_path)
        if not chain:
            logger.warning(f"No chain found for backup: {backup_path}")
            return None

        if len(chain) == 1:
            logger.info("Backup is already a complete full backup, no merge needed")
            return None

        logger.info(f"Auto-merging chain for backup: {backup_path}")
        merged_data = self.merge_chain(chain)
        output_path = self.save_merged_backup(merged_data)

        return merged_data, output_path

    def get_chain_info(self, chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get information about a backup chain"""
        if not chain:
            return {}

        full_backup = chain[0]
        incremental_backups = chain[1:]

        total_messages = sum(b["stats"].get("total_messages", 0) for b in chain)
        total_media = sum(b["stats"].get("media_files", 0) for b in chain)

        return {
            "server_name": full_backup["server_name"],
            "full_backup": {
                "path": full_backup["path"],
                "timestamp": full_backup["timestamp"],
                "messages": full_backup["stats"].get("total_messages", 0),
                "media_files": full_backup["stats"].get("media_files", 0),
            },
            "incremental_backups": [
                {
                    "path": b["path"],
                    "timestamp": b["timestamp"],
                    "messages": b["stats"].get("total_messages", 0),
                    "media_files": b["stats"].get("media_files", 0),
                }
                for b in incremental_backups
            ],
            "total_backups": len(chain),
            "total_messages": total_messages,
            "total_media_files": total_media,
            "date_range": {
                "start": full_backup["timestamp"],
                "end": chain[-1]["timestamp"],
            },
        }


def choose_backup_chain_interactive(backup_dir: str = "./backups") -> Optional[str]:
    """Interactive backup chain selection"""
    import click

    chain_manager = BackupChain(backup_dir)
    chains = chain_manager.get_chains()

    if not chains:
        click.echo("❌ No backup chains found in the backup directory")
        return None

    click.echo(f"\n🔗 Found {len(chains)} backup chain(s):")
    click.echo("=" * 80)

    chain_list = list(chains.items())

    # Display chains with numbers
    for i, (chain_name, chain) in enumerate(chain_list, 1):
        chain_info = chain_manager.get_chain_info(chain)

        click.echo(f"{i:2}. 🔗 {chain_info['server_name']}")
        click.echo(
            f"     📦 Full backup: {chain_info['full_backup']['timestamp'][:19]}"
        )
        click.echo(
            f"     🔄 Incremental backups: {len(chain_info['incremental_backups'])}"
        )
        click.echo(f"     📊 Total messages: {chain_info['total_messages']:,}")
        click.echo(f"     📂 Total media files: {chain_info['total_media_files']:,}")
        click.echo(
            f"     📅 Date range: {chain_info['date_range']['start'][:10]} to {chain_info['date_range']['end'][:10]}"
        )
        click.echo("-" * 60)

    # Get user choice
    while True:
        try:
            choice = click.prompt(
                f"\nSelect a backup chain to merge and restore (1-{len(chain_list)}, or 0 to cancel)",
                type=int,
            )

            if choice == 0:
                return None
            elif 1 <= choice <= len(chain_list):
                selected_chain_name, selected_chain = chain_list[choice - 1]
                chain_info = chain_manager.get_chain_info(selected_chain)

                click.echo(f"\n✅ Selected chain: {chain_info['server_name']}")
                click.echo(
                    f"   📦 Full backup + {len(chain_info['incremental_backups'])} incremental backups"
                )
                click.echo(f"   🔄 Will merge into complete backup for restoration")

                # Auto-merge the chain
                merge_result = chain_manager.auto_merge_for_backup(
                    selected_chain[0]["path"]
                )
                if merge_result:
                    merged_data, output_path = merge_result
                    click.echo(f"   ✅ Chain merged successfully: {output_path}")
                    return output_path
                else:
                    click.echo("   ❌ Failed to merge chain")
                    return None
            else:
                click.echo(
                    f"❌ Invalid choice. Please enter 1-{len(chain_list)} or 0 to cancel."
                )

        except (ValueError, click.Abort):
            click.echo("\n❌ Operation cancelled.")
            return None
