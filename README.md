# analog-hub

Dependency management tool for analog IC design repositories that enables selective import of IP libraries without copying entire repository structures.

## Overview

analog-hub solves the problem of fragmented analog IP libraries by allowing selective import of specific libraries from repositories without copying unwanted boilerplate code.

### Key Features

- **Selective Library Import**: Extract only the IP libraries you need
- **Version Control**: Pin to specific branches, tags, or commits
- **License Tracking**: Monitor license compliance across imported libraries
- **Immutable Updates**: Clean, deterministic library updates

### Target Environment

Designed for open source IC toolchains, specifically the IIC-OSIC-TOOLS Docker container environment.

## Installation

```bash
pip install analog-hub
```

## Quick Start

1. Create an `analog-hub.yaml` configuration file:

```yaml
analog-hub-root: designs/libs
imports:
  standard_cells:
    repo: https://github.com/example/pdk-stdcells
    ref: v1.2.0
exports:
  my_amplifier:
    path: ./designs/amplifiers/ota
    type: design
```

2. Install libraries:

```bash
analog-hub install
```

## Commands

- `analog-hub install` - Install all imported libraries
- `analog-hub update [library]` - Update libraries to latest versions
- `analog-hub list` - Show installed libraries and license information
- `analog-hub validate` - Validate configuration file

## License

MIT License