# Changelog

All notable changes to Discord Yoink will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2025-07-18

### Added
- **🔄 Incremental Backup Implementation**: Complete incremental backup functionality
  - Fully implemented incremental backup logic for `--incremental` flag
  - Automatic detection of previous backup timestamps
  - Smart message filtering to only backup new content since last backup
  - Fallback to full backup when no previous backup is found
  - 1-minute buffer time to ensure no messages are missed during incremental updates

### Fixed
- Incremental backup feature now fully functional (previously only flagged but not implemented)
- Improved backup timestamp detection and message filtering logic

### Technical
- Added `_find_last_backup_timestamp()` method for backup history detection
- Added `_should_backup_message()` method for incremental filtering logic
- Enhanced logging for incremental backup operations
- Code formatting updated to black standards

## [1.1.0] - 2025-07-18

### Added
- **🚀 Unlimited Restore Features**: Complete bypass of Discord limitations
  - `--no-limits` flag to bypass all Discord restrictions with one command
  - `--max-messages` option for unlimited message restoration (0 = unlimited)
  - `--ignore-emoji-limit` to continue creating emojis past Discord's limit
  - `--ignore-sticker-limit` to continue creating stickers past Discord's limit
  - `--fast-mode` for reduced rate limiting and faster recreation
- **🎯 Interactive Mode Enhancements**: User-friendly guided workflows
  - Interactive backup file selection with detailed statistics
  - Interactive server selection with member counts and creation dates
  - Interactive options menu for unlimited restore settings
  - Visual backup information display (size, messages, channels, media)
  - One-click "No Limits" mode activation in interactive flow
  - Granular control options with clear explanations
- **⚡ Performance Improvements**: Configurable rate limiting and optimization
  - Configurable rate limiting delays via `rate_limit_delay` setting
  - Smart rate limiting that adapts based on operation type
  - Bypass options for Discord's emoji and sticker limits
  - Optimized message restoration for large channels
- **📚 Enhanced Documentation**: Comprehensive guides and examples
  - New documentation: `docs/unlimited_restore.md` with complete usage guide
  - Updated README.md with interactive mode examples
  - Performance expectations and best practices
  - Troubleshooting guide for rate limits and permissions
  - Visual demo examples and usage scenarios

### Changed
- Enhanced `recreate` command with 5 new bypass options
- Improved interactive flow with options selection step
- Modified ServerRecreator to respect new bypass settings
- Updated CLI help text with detailed option descriptions
- Enhanced backup file discovery with validation and statistics

### Fixed
- CI/CD pipeline issues with deprecated GitHub Actions
- Security vulnerabilities in dependencies (aiohttp, requests, pillow, jinja2, tqdm)
- Unicode encoding issues in setup scripts
- Markdown linting configuration and compliance
- Python code formatting and type checking issues

### Security
- Updated aiohttp from 3.9.1 to 3.10.11 (CVE fixes)
- Updated requests from 2.31.0 to 2.32.3 (security patches)
- Updated pillow from 10.1.0 to 10.4.0 (vulnerability fixes)
- Updated jinja2 from 3.1.2 to 3.1.6 (security improvements)
- Updated tqdm from 4.66.1 to 4.66.5 (minor security fixes)
- Added .safety-policy.yml for security scanning configuration

### Documentation
- Added unlimited restore feature documentation
- Enhanced README with interactive examples
- Added performance expectations and troubleshooting guides
- Updated CLI help text for better user experience

## [1.0.0] - 2025-07-18

### Added
- Complete Discord server backup functionality
- Message backup with full content, attachments, and metadata
- Media file downloading (images, videos, audio, attachments)
- Voice message backup support
- Server structure backup (channels, categories, roles, permissions)
- Custom emoji and sticker backup
- Member information and role backup
- Server recreation from backup data
- Multiple export formats (HTML, JSON, CSV)
- Beautiful HTML viewer with Discord-like interface
- Comprehensive configuration system
- Rate limiting and error handling
- Incremental backup support
- Channel and user filtering
- Date range filtering
- Privileged intents support
- Cross-platform setup scripts (Windows/Linux/macOS)
- Comprehensive documentation and examples
- Network diagnostics tool
- CLI interface with multiple commands

### Security
- Proper token handling and validation
- Gitignore for sensitive files
- Configuration template system
- Discord API rate limiting compliance

### Documentation
- Complete setup and usage guides
- Bot configuration documentation
- API documentation and examples
- Contributing guidelines
- Legal and ethical usage guidelines

## [Unreleased]

### Planned Features
- **Enhanced Webhook Support**: Better message recreation with original timestamps
- **GUI Interface**: Desktop application with visual backup/restore management
- **Automated Scheduling**: Scheduled backups with cron-like functionality
- **Advanced Filtering**: Time-based, user-based, and content-based filters
- **Bulk Operations**: Multi-server backup and restoration workflows
- **Cloud Storage**: Integration with cloud providers for backup storage
- **Real-time Monitoring**: Live backup progress and recreation status
- **Template System**: Reusable server templates and configurations
- **Migration Tools**: Direct server-to-server migration without intermediate files
- **Performance Analytics**: Detailed statistics and optimization recommendations

---

## Release Notes Format

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security-related changes
