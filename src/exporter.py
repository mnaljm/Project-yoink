"""
Data exporter for Discord backups
Exports backup data to various formats (HTML, JSON, CSV)
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from jinja2 import Template, Environment, FileSystemLoader

from .config import Config

logger = logging.getLogger(__name__)


class DataExporter:
    def __init__(self, config: Config):
        self.config = config
        self.templates_dir = Path(__file__).parent.parent / 'templates'
    
    def export_to_json(self, backup_data: Dict[str, Any], output_path: str) -> None:
        """Export backup data to JSON format"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported backup to JSON: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise
    
    def export_to_csv(self, backup_data: Dict[str, Any], output_path: str) -> None:
        """Export messages to CSV format"""
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Export messages for each channel
            channels = backup_data.get('channels', {})
            
            for channel_id, channel_data in channels.items():
                channel_name = channel_data.get('name', f'channel_{channel_id}')
                safe_name = self._sanitize_filename(channel_name)
                csv_file = output_dir / f"{safe_name}_messages.csv"
                
                messages = channel_data.get('messages', [])
                if not messages:
                    continue
                
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Write header
                    writer.writerow([
                        'Message ID', 'Timestamp', 'Author', 'Content', 
                        'Attachments', 'Reactions', 'Edited', 'Pinned'
                    ])
                    
                    # Write messages
                    for message in messages:
                        attachments = ', '.join([
                            att['filename'] for att in message.get('attachments', [])
                        ])
                        
                        reactions = ', '.join([
                            f"{r['emoji']['name']}:{r['count']}" 
                            for r in message.get('reactions', [])
                        ])
                        
                        writer.writerow([
                            message.get('id', ''),
                            message.get('timestamp', ''),
                            message.get('author', {}).get('username', ''),
                            message.get('content', ''),
                            attachments,
                            reactions,
                            'Yes' if message.get('edited_timestamp') else 'No',
                            'Yes' if message.get('pinned') else 'No'
                        ])
            
            # Export server info
            server_csv = output_dir / 'server_info.csv'
            with open(server_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                server_info = backup_data.get('server_info', {})
                
                writer.writerow(['Property', 'Value'])
                for key, value in server_info.items():
                    writer.writerow([key, str(value)])
            
            logger.info(f"Exported backup to CSV: {output_dir}")
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise
    
    def export_to_html(
        self, 
        backup_data: Dict[str, Any], 
        output_path: str, 
        template_path: Optional[str] = None
    ) -> None:
        """Export backup data to HTML format"""
        try:
            # Load template
            if template_path and Path(template_path).exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            else:
                template_content = self._get_default_html_template()
            
            # Prepare data for template
            template_data = self._prepare_template_data(backup_data)
            
            # Render template
            template = Template(template_content)
            html_content = template.render(**template_data)
            
            # Write HTML file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Copy media files if they exist
            self._copy_media_for_html(backup_data, output_path)
            
            logger.info(f"Exported backup to HTML: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export to HTML: {e}")
            raise
    
    def _prepare_template_data(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for HTML template rendering"""
        server_info = backup_data.get('server_info', {})
        channels = backup_data.get('channels', {})
        members = backup_data.get('members', {})
        stats = backup_data.get('stats', {})
        
        # Organize channels by category
        organized_channels = {
            'categories': {},
            'uncategorized': []
        }
        
        for channel_id, channel_data in channels.items():
            category_id = channel_data.get('category_id')
            if category_id and category_id in channels:
                category_name = channels[category_id].get('name', 'Unknown Category')
                if category_name not in organized_channels['categories']:
                    organized_channels['categories'][category_name] = []
                organized_channels['categories'][category_name].append(channel_data)
            else:
                organized_channels['uncategorized'].append(channel_data)
        
        # Process messages for better display
        for channel_id, channel_data in channels.items():
            messages = channel_data.get('messages', [])
            for message in messages:
                # Format timestamp
                timestamp = message.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        message['formatted_timestamp'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        message['formatted_timestamp'] = timestamp
                
                # Process attachments for display
                for attachment in message.get('attachments', []):
                    if attachment.get('local_path'):
                        # Make relative path for HTML
                        attachment['relative_path'] = os.path.relpath(
                            attachment['local_path'], 
                            Path(output_path).parent
                        ).replace('\\', '/')
        
        return {
            'server_info': server_info,
            'channels': organized_channels,
            'members': members,
            'stats': stats,
            'backup_timestamp': backup_data.get('backup_info', {}).get('timestamp', ''),
            'export_timestamp': datetime.now().isoformat()
        }
    
    def _get_default_html_template(self) -> str:
        """Get default HTML template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ server_info.name }} - Discord Backup</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #2f3136;
            color: #dcddde;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background-color: #36393f;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .server-icon {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            margin-bottom: 10px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-card {
            background-color: #36393f;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #7289da;
        }
        
        .channels {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }
        
        .channel-list {
            background-color: #36393f;
            padding: 20px;
            border-radius: 8px;
            height: fit-content;
        }
        
        .channel-item {
            padding: 8px 12px;
            margin: 2px 0;
            cursor: pointer;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        
        .channel-item:hover {
            background-color: #40444b;
        }
        
        .channel-item.active {
            background-color: #7289da;
        }
        
        .category {
            font-weight: bold;
            margin-top: 15px;
            margin-bottom: 5px;
            text-transform: uppercase;
            font-size: 0.8em;
            color: #8e9297;
        }
        
        .messages {
            background-color: #36393f;
            padding: 20px;
            border-radius: 8px;
            max-height: 800px;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-left: 3px solid #7289da;
            background-color: #40444b;
            border-radius: 0 8px 8px 0;
        }
        
        .message-header {
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }
        
        .author {
            font-weight: bold;
            margin-right: 10px;
            color: #ffffff;
        }
        
        .timestamp {
            font-size: 0.8em;
            color: #72767d;
        }
        
        .message-content {
            margin: 8px 0;
            line-height: 1.4;
        }
        
        .attachment {
            display: inline-block;
            margin: 5px;
            padding: 8px 12px;
            background-color: #2f3136;
            border-radius: 4px;
            text-decoration: none;
            color: #7289da;
        }
        
        .attachment:hover {
            background-color: #36393f;
        }
        
        .reactions {
            margin-top: 8px;
        }
        
        .reaction {
            display: inline-block;
            margin: 2px;
            padding: 4px 8px;
            background-color: #2f3136;
            border-radius: 12px;
            font-size: 0.9em;
        }
        
        #channel-content {
            display: none;
        }
        
        #channel-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            {% if server_info.local_icon_path %}
            <img src="{{ server_info.local_icon_path }}" alt="Server Icon" class="server-icon">
            {% endif %}
            <h1>{{ server_info.name }}</h1>
            <p>{{ server_info.description or "Discord Server Backup" }}</p>
            <p><small>Backup created: {{ backup_timestamp }}</small></p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_messages or 0 }}</div>
                <div>Messages</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_channels or 0 }}</div>
                <div>Channels</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_users or 0 }}</div>
                <div>Members</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.media_files or 0 }}</div>
                <div>Media Files</div>
            </div>
        </div>
        
        <div class="channels">
            <div class="channel-list">
                <h3>Channels</h3>
                
                {% for category_name, category_channels in channels.categories.items() %}
                <div class="category">{{ category_name }}</div>
                {% for channel in category_channels %}
                {% if channel.messages %}
                <div class="channel-item" onclick="showChannel('{{ channel.id }}')">
                    # {{ channel.name }}
                    <small>({{ channel.messages|length }} messages)</small>
                </div>
                {% endif %}
                {% endfor %}
                {% endfor %}
                
                {% if channels.uncategorized %}
                <div class="category">Uncategorized</div>
                {% for channel in channels.uncategorized %}
                {% if channel.messages %}
                <div class="channel-item" onclick="showChannel('{{ channel.id }}')">
                    # {{ channel.name }}
                    <small>({{ channel.messages|length }} messages)</small>
                </div>
                {% endif %}
                {% endfor %}
                {% endif %}
            </div>
            
            <div id="channel-content">
                {% for channel_id, channel_data in channels.items() %}
                {% if channel_data.messages %}
                <div id="channel-{{ channel_data.id }}" class="messages" style="display: none;">
                    <h3># {{ channel_data.name }}</h3>
                    {% if channel_data.topic %}
                    <p><em>{{ channel_data.topic }}</em></p>
                    {% endif %}
                    
                    {% for message in channel_data.messages %}
                    <div class="message">
                        <div class="message-header">
                            <span class="author">{{ message.author.username }}</span>
                            <span class="timestamp">{{ message.formatted_timestamp or message.timestamp }}</span>
                        </div>
                        
                        {% if message.content %}
                        <div class="message-content">{{ message.content }}</div>
                        {% endif %}
                        
                        {% if message.attachments %}
                        <div class="attachments">
                            {% for attachment in message.attachments %}
                            <a href="{{ attachment.relative_path or attachment.url }}" 
                               class="attachment" target="_blank">
                                📎 {{ attachment.filename }}
                            </a>
                            {% endfor %}
                        </div>
                        {% endif %}
                        
                        {% if message.reactions %}
                        <div class="reactions">
                            {% for reaction in message.reactions %}
                            <span class="reaction">{{ reaction.emoji.name }} {{ reaction.count }}</span>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                {% endfor %}
            </div>
        </div>
    </div>
    
    <script>
        function showChannel(channelId) {
            // Hide all channel contents
            const allChannels = document.querySelectorAll('.messages');
            allChannels.forEach(channel => channel.style.display = 'none');
            
            // Remove active class from all channel items
            const allItems = document.querySelectorAll('.channel-item');
            allItems.forEach(item => item.classList.remove('active'));
            
            // Show selected channel
            const selectedChannel = document.getElementById('channel-' + channelId);
            if (selectedChannel) {
                selectedChannel.style.display = 'block';
                document.getElementById('channel-content').classList.add('active');
            }
            
            // Add active class to clicked item
            event.target.classList.add('active');
        }
        
        // Show first channel by default
        const firstChannel = document.querySelector('.channel-item');
        if (firstChannel) {
            firstChannel.click();
        }
    </script>
</body>
</html>
        '''
    
    def _copy_media_for_html(self, backup_data: Dict[str, Any], output_path: str) -> None:
        """Copy media files relative to HTML output"""
        # This would copy media files to be accessible from the HTML
        # Implementation depends on the specific structure needed
        pass
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem storage"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
