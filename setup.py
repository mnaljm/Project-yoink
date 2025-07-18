#!/usr/bin/env python3
"""
Setup script for Discord Yoink
Run this script to set up the project for first use
"""

import json
import os
import sys
from pathlib import Path


def create_config_file():
    """Create config.json from template"""
    config_path = Path("config.json")
    example_path = Path("config.example.json")

    if config_path.exists():
        print("[OK] config.json already exists")
        return

    if not example_path.exists():
        print("[ERROR] config.example.json not found")
        return

    # Copy example to config
    with open(example_path, "r") as f:
        config_data = json.load(f)

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)

    print("[OK] Created config.json from template")
    print("  -> Please edit config.json and add your Discord bot token")


def create_directories():
    """Create necessary directories"""
    directories = ["backups", "media", "logs", "exports", "temp"]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"[OK] Created directory: {directory}")


def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("[ERROR] Python 3.8 or higher is required")
        print(f"  Current version: {sys.version}")
        return False

    print(f"[OK] Python version: {sys.version.split()[0]}")
    return True


def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")

    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("[OK] Dependencies installed successfully")
            return True
        else:
            print("[ERROR] Failed to install dependencies")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"[ERROR] Error installing dependencies: {e}")
        return False


def test_imports():
    """Test if required modules can be imported"""
    required_modules = ["discord", "aiohttp", "aiofiles", "click", "tqdm", "jinja2"]

    failed_imports = []

    for module in required_modules:
        try:
            __import__(module)
            print(f"[OK] {module}")
        except ImportError:
            print(f"[ERROR] {module}")
            failed_imports.append(module)

    if failed_imports:
        print(f"\nFailed to import: {', '.join(failed_imports)}")
        print("Please run: pip install -r requirements.txt")
        return False

    return True


def show_next_steps():
    """Show what to do next"""
    print("\n" + "=" * 50)
    print("SETUP COMPLETE!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Edit config.json and add your Discord bot token")
    print("2. Create a Discord application and bot at:")
    print("   https://discord.com/developers/applications")
    print("3. Copy the bot token to config.json")
    print("4. Invite the bot to your server with these permissions:")
    print("   - Read Messages/View Channels")
    print("   - Read Message History")
    print("   - Manage Channels (for recreation)")
    print("   - Manage Roles (for recreation)")
    print("   - Manage Emojis (for recreation)")
    print()
    print("Usage examples:")
    print("  python discord_yoink.py backup --server-id YOUR_SERVER_ID")
    print("  python discord_yoink.py export --backup-path ./backups/backup.json")
    print(
        "  python discord_yoink.py recreate --backup-path ./backups/backup.json --server-id NEW_SERVER_ID"
    )
    print()


def main():
    """Main setup function"""
    print("Discord Yoink Setup")
    print("==================")
    print()

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Create directories
    print("\nCreating directories...")
    create_directories()

    # Create config file
    print("\nSetting up configuration...")
    create_config_file()

    # Install dependencies
    print("\nChecking dependencies...")
    if not install_dependencies():
        print("\nTrying to check imports anyway...")

    # Test imports
    print("\nTesting imports...")
    if not test_imports():
        print("\nSome modules failed to import. Please install dependencies manually:")
        print("pip install -r requirements.txt")

    # Show next steps
    show_next_steps()


if __name__ == "__main__":
    main()
