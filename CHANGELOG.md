# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-08-04

### Added
- **Core dependency management system** for analog/mixed-signal IC design repositories
- **Selective library import** - Extract only needed IP libraries from repositories
- **Smart mirror system** - Efficient repository caching with SHA256-based deduplication
- **Version control integration** - Pin to specific branches, tags, or commits
- **License preservation** - Automatic LICENSE file tracking for legal compliance
- **Security hardening** - Path validation and URL sanitization to prevent vulnerabilities
- **Clean workspace management** - Automatic filtering of VCS directories and development files
- **Gitignore integration** - Automatic .gitignore management for non-checkin libraries

### CLI Commands
- `ams-compose init` - Initialize new projects with configuration templates
- `ams-compose install` - Fast local-only installation of missing libraries
- `ams-compose update` - Check remote repositories for library updates
- `ams-compose list` - Display installed libraries with status information
- `ams-compose validate` - Validate configuration and installation integrity
- `ams-compose clean` - Remove unused mirrors and orphaned libraries
- `ams-compose schema` - Show complete configuration schema documentation

### Configuration Features
- **YAML-based configuration** - Simple, readable dependency specifications
- **Flexible path mapping** - Override default installation paths per library
- **Selective version control** - Control which dependencies are committed to repository
- **Ignore patterns** - Additional gitignore-style filtering during extraction
- **License override** - Manual license specification when auto-detection insufficient

### Advanced Features
- **SHA256 content verification** - Ensure library integrity after installation
- **Submodule support** - Handle repositories with git submodules
- **Cross-platform compatibility** - Tested on Linux, macOS, and Windows
- **Three-tier logging system** - WARNING (default), INFO (--verbose), DEBUG (--debug)
- **Comprehensive error handling** - User-friendly error messages for analog IC designers

### Technical Implementation
- **Python 3.8+ compatibility** - Modern Python with type hints and comprehensive testing
- **GitPython integration** - Robust git operations with proper error handling
- **Pydantic validation** - Strong configuration validation and error reporting
- **Click CLI framework** - Professional command-line interface with help system
- **202 comprehensive tests** - Unit, integration, and E2E test coverage
- **Security-first design** - Built-in protection against path traversal and injection attacks

### Target Environment
- Designed for **IIC-OSIC-TOOLS Docker container** environment
- Optimized for **open source IC toolchains**
- Supports **analog/mixed-signal design workflows**

### Dependencies
- GitPython >=3.1.40 - Git repository operations
- Pydantic >=2.0.0 - Configuration validation
- Click >=8.1.0 - Command-line interface
- PyYAML >=6.0.0 - YAML configuration parsing
- pathspec >=0.11.0 - Gitignore pattern matching

[0.1.0]: https://github.com/Jianxun/ams-compose/releases/tag/v0.1.0