#!/usr/bin/env python3
"""
Emergency Admin Access Example
Demonstrates how to use the emergency admin functionality programmatically
"""

import asyncio
from pathlib import Path
import sys

# Add the parent directory to the path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.discord_client import DiscordYoinkClient
from src.server_recreator import ServerRecreator
from src.config import Config


async def emergency_admin_example():
    """
    Example of how to use the emergency admin functionality programmatically
    """
    print("🚨 Emergency Admin Access Example")
    print("=" * 50)
    
    # Load configuration
    try:
        config = Config("config.json")
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print("Make sure config.json exists with a valid bot token")
        return
    
    # Initialize client and recreator
    client = DiscordYoinkClient(config)
    recreator = ServerRecreator(config)
    
    # Example server and user IDs (replace with actual values)
    SERVER_ID = "123456789012345678"  # Replace with actual server ID
    USER_ID = "987654321098765432"    # Replace with actual user ID
    ROLE_NAME = "Emergency Admin"
    
    print(f"\n📋 Example Configuration:")
    print(f"Server ID: {SERVER_ID}")
    print(f"User ID: {USER_ID}")
    print(f"Role Name: {ROLE_NAME}")
    print(f"\n⚠️  NOTE: This is just an example. Replace IDs with actual values.")
    
    try:
        # Start the client
        print(f"\n🔄 Starting Discord client...")
        start_task = asyncio.create_task(client.start())
        await client.wait_until_ready()
        print(f"✅ Client connected successfully")
        
        # Get the server
        guild = client.get_guild(int(SERVER_ID))
        if not guild:
            print(f"❌ Could not access server {SERVER_ID}")
            print("Make sure the bot is in the server and the ID is correct")
            return
            
        print(f"✅ Found server: {guild.name}")
        
        # Example 1: Make user admin
        print(f"\n🔧 Example 1: Making user admin...")
        print(f"⚠️  This is a dry run - no actual changes will be made")
        
        # In a real scenario, you would call:
        # result = await recreator.make_user_admin(guild, USER_ID, ROLE_NAME)
        
        print(f"📝 Would create admin role: {ROLE_NAME}")
        print(f"📝 Would assign role to user: {USER_ID}")
        print(f"📝 Role would have full admin permissions")
        
        # Example 2: Remove admin access
        print(f"\n🔧 Example 2: Removing admin access...")
        print(f"⚠️  This is a dry run - no actual changes will be made")
        
        # In a real scenario, you would call:
        # result = await recreator.remove_emergency_admin(guild, USER_ID, ROLE_NAME, delete_role=True)
        
        print(f"📝 Would remove admin role from user: {USER_ID}")
        print(f"📝 Would delete role if no one else has it")
        
        print(f"\n✅ Example completed successfully!")
        print(f"\n📚 To use this functionality:")
        print(f"1. Replace SERVER_ID and USER_ID with actual values")
        print(f"2. Use the make_user_admin() method for emergency access")
        print(f"3. Use remove_emergency_admin() to clean up when done")
        print(f"4. Or use the CLI commands: make-admin and remove-admin")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"This might be due to invalid IDs or bot permissions")
        
    finally:
        # Clean up
        if 'start_task' in locals():
            start_task.cancel()
        await client.close()
        print(f"\n🔄 Client disconnected")


if __name__ == "__main__":
    print("Emergency Admin Access Example")
    print("This example demonstrates the emergency admin functionality")
    print("No actual changes will be made - this is for demonstration only")
    
    try:
        asyncio.run(emergency_admin_example())
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
