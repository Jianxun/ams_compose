# ams-compose

Dependency management tool for analog/mixed-signal IC design repositories that enables selective import of IP libraries without copying entire repository structures.

## Overview

ams-compose solves the problem of fragmented analog IP libraries by allowing selective import of specific libraries from repositories without copying unwanted boilerplate code.

### Key Features

- **Selective Library Import**: Extract only the IP libraries you need from any path within a repository
- **Version Control Integration**: Pin to specific branches, tags, or commits with smart checkin controls
- **Smart Install Logic**: Skip libraries that don't need updates with intelligent caching
- **License Preservation**: Automatically track and preserve license files for legal compliance
- **Smart Mirror System**: Efficient repository caching with SHA256-based deduplication
- **Security Hardening**: Path validation and URL sanitization to prevent security vulnerabilities
- **Clean Workspaces**: Automatically filter out VCS directories, development files, and OS artifacts
- **Gitignore Integration**: Automatic .gitignore management for libraries marked as non-checkin

### Target Environment

Designed for open source IC toolchains, specifically the IIC-OSIC-TOOLS Docker container environment.

## Installation

### Requirements

- Python >=3.8
- Git (for repository operations)

### Install from GitHub

```bash
pip install git+https://github.com/Jianxun/ams-compose.git
```

### Install from Source (Development)

```bash
git clone https://github.com/Jianxun/ams-compose.git
cd ams-compose
pip install -e .
```

### Verify Installation

```bash
ams-compose --version
ams-compose --help
```

## CLI Options

All commands support global logging options:

- **`--verbose, -v`** - Enable verbose logging (INFO level) for detailed operation information
- **`--debug`** - Enable debug logging (DEBUG level) for troubleshooting and development
- **`--version`** - Show version information and exit
- **`--help`** - Show help message and exit

Example with verbose logging:
```bash
ams-compose --verbose install
ams-compose --debug validate
```

## Quick Start

1. Initialize a new project:

```bash
ams-compose init
```

2. Edit the generated `ams-compose.yaml` configuration file:

```yaml
# Default directory where libraries will be installed
library_root: designs/libs

# Library imports - add your dependencies here
imports:
  # Example library configurations (remove or modify as needed):
  
  analog_lib:
    repo: https://github.com/company/analog-ip.git
    ref: v1.2.0
    source_path: lib/analog
    checkin: true
    license: MIT
    
  design_tools:
    repo: https://github.com/tools/design-suite.git
    ref: main
    source_path: tools
    local_path: tools/design-suite
    checkin: false
    ignore_patterns:
      - "*.log"
      - "build/"
      - "*.tmp"
```

3. Install libraries:

```bash
ams-compose install
```

## Commands

### Core Operations

- **`ams-compose init`** - Initialize a new ams-compose project
  - Creates `ams-compose.yaml` configuration file
  - Sets up basic project structure

- **`ams-compose install [LIBRARIES...]`** - Install missing libraries from ams-compose.yaml
  - `LIBRARIES`: Optional list of specific libraries to install
  - `--force`: Force reinstall all libraries (ignore up-to-date check)
  - Only installs missing libraries or those with configuration changes
  - Does not check remote repositories for updates (fast, local-only operation)
  - Automatically manages .gitignore for non-checkin libraries

- **`ams-compose update [LIBRARIES...]`** - Update libraries by checking remote repositories for newer versions
  - `LIBRARIES`: Optional list of specific libraries to update
  - `--force`: Force reinstall all libraries (ignore up-to-date check)
  - Checks remote repositories for updates and installs newer versions
  - Use when you want to ensure you have the latest versions of dependencies

- **`ams-compose list`** - List installed libraries
  - Shows installation status and version information
  - Displays library paths and metadata

### Maintenance Operations

- **`ams-compose validate`** - Validate ams-compose.yaml configuration and installation state
  - Checks configuration file syntax
  - Verifies installed library integrity
  - Reports missing or corrupted libraries

- **`ams-compose clean`** - Clean unused mirrors and orphaned libraries
  - Removes unused repository mirrors from `.mirror/` directory
  - Cleans up orphaned library installations
  - Validates current installation state

### Documentation

- **`ams-compose schema`** - Show complete ams-compose.yaml configuration schema
  - Displays all available configuration options
  - Includes examples and field descriptions
  - Useful for advanced configuration

## Configuration

The `ams-compose.yaml` file supports the following structure:

```yaml
# Default installation directory for all libraries
library_root: designs/libs

imports:
  library_name:
    # REQUIRED FIELDS
    repo: https://github.com/user/repo    # Git repository URL
    ref: main                             # Branch, tag, or commit SHA
    source_path: path/in/repo             # Path within repo to extract
    
    # OPTIONAL FIELDS
    local_path: custom/path               # Override default path construction
    checkin: true                         # Include in version control (default: true)
    license: MIT                          # License override (auto-detected if not specified)
    ignore_patterns:                      # Additional files to ignore during extraction
      - "*.log"
      - "build/"
      - "*.tmp"
```

### Key Configuration Options

- **`library_root`**: Default directory where libraries are installed when `local_path` is not specified
- **`checkin`**: Controls whether the library is included in version control
  - `true` (default): Library files are committed to your repository
  - `false`: Library is excluded via .gitignore (useful for large or frequently changing dependencies)
- **`ignore_patterns`**: Additional gitignore-style patterns applied during extraction
- **`local_path`**: When specified, completely overrides the default `{library_root}/{library_name}` path

## Advanced Features

### License Compliance

ams-compose automatically tracks and preserves license files to ensure legal compliance:

- **Automatic License Detection**: Scans for LICENSE, COPYING, and similar files in repositories
- **License Preservation**: Always copies license files during library extraction
- **Partial IP License Injection**: For `source_path` extractions, injects the repository's root LICENSE file
- **License Override**: Manual license specification in configuration when auto-detection is insufficient
- **Legal Compliance**: Enables safe partial IP reuse while maintaining license obligations

### Smart Mirror System

Efficient repository management with intelligent caching:

- **SHA256 Deduplication**: Repository mirrors stored in `.mirror/` with content-based naming
- **Shallow Clones**: Optimized network usage for faster operations
- **Shared Mirrors**: Multiple libraries from same repository share a single mirror
- **Automatic Cleanup**: Unused mirrors removed during `ams-compose clean` operations
- **Disk Space Optimization**: Significantly reduces storage requirements for projects with multiple dependencies

### Security Features

Built-in security hardening to protect against common vulnerabilities:

- **Path Traversal Protection**: Validates all paths to prevent directory escape attacks
- **Git URL Validation**: Sanitizes repository URLs to prevent command injection
- **Scheme Restrictions**: Only allows safe URL schemes (https, ssh, file with validation)
- **Checksum Integrity**: SHA256 verification of extracted libraries
- **Safe File Operations**: Proper handling of symlinks and special files

### Version Control Integration

Smart gitignore management based on library configuration:

- **Automatic .gitignore**: Libraries with `checkin: false` automatically added to .gitignore
- **Mirror Exclusion**: `.mirror/` directory always excluded from version control
- **Selective Checkin**: Fine-grained control over which dependencies are committed
- **Clean Repository State**: Maintains clean git status while managing external dependencies

## Troubleshooting

### Common Issues

**Library not updating despite changes**
```bash
# Force reinstall to bypass cache
ams-compose install --force library_name
```

**Configuration validation errors**
```bash
# Check configuration syntax and structure
ams-compose validate
# Show complete configuration schema
ams-compose schema
```

**Mirror storage cleanup**
```bash
# Remove unused mirrors and orphaned libraries
ams-compose clean
```

**Path or permission issues**
- Ensure write permissions to `library_root` directory
- Verify git credentials for private repositories
- Check that `local_path` destinations are writable

### Getting Help

- Run `ams-compose --help` for command overview
- Use `ams-compose COMMAND --help` for specific command options
- Check `ams-compose schema` for configuration reference
- Report issues at [GitHub Issues](https://github.com/Jianxun/ams_compose/issues)

## License

MIT License