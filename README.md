# ams-compose

Dependency management tool for analog IC design repositories that enables selective import of IP libraries without copying entire repository structures.

## Overview

ams-compose solves the problem of fragmented analog IP libraries by allowing selective import of specific libraries from repositories without copying unwanted boilerplate code.

### Key Features

- **Selective Library Import**: Extract only the IP libraries you need from any path within a repository
- **Version Control**: Pin to specific branches, tags, or commits
- **Smart Install Logic**: Skip libraries that don't need updates
- **Clean Workspaces**: Automatically filter out VCS directories, development files, and OS artifacts
- **License Tracking**: Monitor license compliance across imported libraries

### Target Environment

Designed for open source IC toolchains, specifically the IIC-OSIC-TOOLS Docker container environment.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/Jianxun/ams_compose.git
```

Or install from source for development:

```bash
git clone https://github.com/Jianxun/ams_compose.git
cd ams_compose
pip install -e .
```

## Quick Start

1. Initialize a new project:

```bash
ams-compose init
```

2. Edit the generated `ams-compose.yaml` configuration file:

```yaml
# Default directory where libraries will be installed
library-root: designs/libs

# Library imports - add your dependencies here
imports:
  gf180mcu_fd_sc_mcu9t5v0_symbols:
    repo: https://github.com/peterkinget/gf180mcu_fd_sc_mcu9t5v0_symbols
    ref: main
    source_path: .
    
  designinit:
    repo: https://github.com/Jianxun/iic-osic-tools-project-template
    ref: main
    source_path: designs/.designinit
    local_path: designs/.designinit  # optional: override library-root location
```

3. Install libraries:

```bash
ams-compose install
```

## Commands

- `ams-compose init` - Initialize a new ams-compose project
- `ams-compose install [LIBRARIES...]` - Install libraries from ams-compose.yaml
  - `--force` - Force reinstall all libraries (ignore up-to-date check)
  - `--auto-gitignore` - Automatically add .mirror/ to .gitignore (default: enabled)
- `ams-compose list` - List installed libraries
  - `--detailed` - Show detailed library information
- `ams-compose validate` - Validate ams-compose.yaml configuration and installation state
- `ams-compose clean` - Clean unused mirrors, orphaned libraries, and validate installation

## Configuration

The `ams-compose.yaml` file supports the following structure:

```yaml
library-root: designs/libs  # Default installation directory

imports:
  library_name:
    repo: https://github.com/user/repo  # Git repository URL
    ref: main                           # Branch, tag, or commit SHA
    source_path: path/in/repo          # Path within the repository to extract
    local_path: custom/path            # Optional: override library-root location
    license: MIT                       # Optional: license information
```

## License

MIT License