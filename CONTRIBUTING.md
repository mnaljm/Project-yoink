# Contributing to Discord Yoink

Thank you for your interest in contributing to Discord Yoink! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Issues

1. **Check existing issues** first to avoid duplicates
2. **Use descriptive titles** that clearly explain the problem
3. **Provide detailed information:**
   - Operating system and version
   - Python version
   - Discord.py version
   - Steps to reproduce the issue
   - Error messages (if any)
   - Expected vs actual behavior

### Suggesting Features

1. **Check if the feature already exists** or is planned
2. **Explain the use case** and why it would be valuable
3. **Provide detailed specifications** if possible
4. **Consider implementation complexity** and Discord API limitations

### Pull Requests

1. **Fork the repository** and create a feature branch
2. **Follow the coding standards** (see below)
3. **Write tests** for new functionality when possible
4. **Update documentation** if needed
5. **Keep commits focused** and write clear commit messages
6. **Test thoroughly** before submitting

## 📝 Coding Standards

### Python Style

- **Follow PEP 8** with these exceptions:
  - Line length: 88 characters (Black formatter default)
  - Use double quotes for strings

- **Use type hints** for function parameters and return values
- **Write docstrings** for all public functions and classes
- **Use descriptive variable names**

### Code Organization

- **Keep functions focused** on a single responsibility
- **Use async/await** properly for Discord API calls
- **Handle exceptions** gracefully with proper error messages
- **Add logging** for important operations

### Example:
```python
async def backup_channel_messages(
    self, 
    channel: discord.TextChannel, 
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Backup all messages from a Discord channel.
    
    Args:
        channel: The Discord channel to backup
        limit: Maximum number of messages to backup (None for all)
        
    Returns:
        List of message data dictionaries
        
    Raises:
        discord.Forbidden: If bot lacks permission to read channel
        discord.HTTPException: If Discord API request fails
    """
    logger.info(f"Starting backup of #{channel.name}")
    # Implementation here...
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src

# Run specific test file
python -m pytest tests/test_backup_manager.py
```

### Writing Tests

- **Test both success and failure cases**
- **Mock Discord API calls** to avoid rate limits
- **Use fixtures** for common test data
- **Test edge cases** and error conditions

## 📚 Documentation

### Code Documentation

- **Write clear docstrings** for all public functions
- **Include parameter types** and descriptions
- **Document exceptions** that can be raised
- **Provide usage examples** for complex functions

### User Documentation

- **Update README.md** for user-facing changes
- **Add examples** to the examples/ directory
- **Update configuration docs** if adding new settings
- **Keep quick start guide current**

## 🚀 Release Process

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with new features and fixes
3. **Test thoroughly** on multiple platforms
4. **Create release notes** with highlights
5. **Tag the release** with semantic versioning

## 🔒 Security Considerations

### Discord Tokens

- **Never commit tokens** to the repository
- **Use environment variables** or config files (gitignored)
- **Validate token format** before using
- **Handle token errors** gracefully

### API Rate Limits

- **Respect Discord's rate limits**
- **Implement backoff strategies**
- **Allow configurable delays**
- **Log rate limit warnings**

### User Privacy

- **Follow data minimization principles**
- **Respect user privacy settings**
- **Provide opt-out mechanisms**
- **Clear data retention policies**

## 📋 Checklist for Contributors

Before submitting a pull request:

- [ ] Code follows the style guidelines
- [ ] Changes are tested and working
- [ ] Documentation is updated
- [ ] No sensitive data is committed
- [ ] Commit messages are clear
- [ ] Branch is up to date with main
- [ ] Tests pass locally

## 🆘 Getting Help

- **Check the documentation** first
- **Search existing issues** for similar problems
- **Ask questions** in GitHub Discussions
- **Be patient and respectful** when asking for help

## 📜 Code of Conduct

### Our Standards

- **Be respectful** and inclusive
- **Provide constructive feedback**
- **Focus on the code, not the person**
- **Help others learn and grow**
- **Follow Discord's Terms of Service**

### Unacceptable Behavior

- Harassment or discrimination
- Sharing of private information
- Spam or promotional content
- Violating Discord's ToS
- Encouraging misuse of the tool

## 📄 License

By contributing to Discord Yoink, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Discord Yoink! 🎉
