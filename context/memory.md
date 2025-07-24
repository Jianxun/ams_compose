# Project Memory

## Current Status
- Project: analog-hub  
- Stage: Git sparse checkout prototype validated ✅
- Last Updated: 2025-07-24

## Project Overview
**analog-hub** is a dependency management tool for analog IC design repositories that enables selective import of IP libraries without copying entire repository structures.

### Core Problems Solved
- Lack of standardized structure in analog design projects
- Fragmentation of analog IP libraries across repositories  
- Git submodules copy unwanted boilerplate when only specific libraries are needed
- No easy way to include standard cell libraries, behavioral models, example designs

### Solution Approach
- **IP Provider Side**: `.analog-hub.yaml` configuration files declare exportable libraries and paths
- **Consumer Side**: Specify which IPs to import from which repos with version control
- **Selective Fetching**: Extract only specified library components, not full repositories

## Key Decisions
- Using `.analog-hub.yaml` as the configuration file format (tentative)
- Support for branch/tag/release version pinning
- Shallow copying approach for efficiency
- Context-based project state management

## Architecture Notes
### Two-sided system:
1. **IP Repositories**: Contains `.analog-hub.yaml` defining exportable libraries
2. **Consumer Projects**: Configuration specifying required IPs and versions
3. **Core Tool**: Handles fetching, version management, dependency resolution

### Key Features Needed:
- Selective library extraction
- Version management (branches, tags, commits)
- Dependency resolution
- Update mechanisms
- Conflict resolution

## Configuration Format
**File**: `analog-hub.yaml` (confirmed)

### Structure:
```yaml
imports:
  library_name:
    repo: url_to_repo
    ref: branch_tag_or_commit
exports:
  library_name:
    path: relative_path_from_root
    type: library_category (flexible, not predefined)
```

### Key Design Decisions:
- **Target Environment**: Open source IC toolchains (IIC-OSIC-TOOLS Docker container)
- **Discovery**: Manual for MVP (IP registry on backlog)
- **Library Types**: Neutral approach - no predefined types, user-defined categories
- **Version Control**: Git refs (branch/tag/commit) for flexibility

## Workflow Details

### IP Provider Workflow:
1. Add `analog-hub.yaml` to repository root
2. Define `exports` section with library paths and types
3. Library consumers reference this repo in their `imports`

### Consumer Workflow:
1. Add `analog-hub.yaml` with `imports` section
2. Run `analog-hub install` (proposed command)
3. Tool fetches only specified library paths from source repos
4. Libraries placed in local project structure

## Design Decisions - Finalized

### **Directory Structure**
- `analog-hub-root` field specifies import destination (e.g., `designs/libs`)
- Libraries imported as: `{analog-hub-root}/{library_name}/`

### **Dependency Resolution**
- **No transitive dependencies** - user manages explicitly
- All required libraries must be listed in `imports` section
- Prevents dependency ambiguity that could impact chip functionality
- Simple, predictable behavior for MVP

### **Update Mechanism**
- **Immutable libraries** - imported libraries are read-only
- `analog-hub update` always overwrites local copies
- User modifications require forking upstream repos
- Clean, deterministic updates with no merge conflicts

### **CLI Interface**
- `analog-hub install` - fetch all imports to analog-hub-root
- `analog-hub update [library]` - sync with upstream (overwrites)
- `analog-hub list` - show current imports/exports  
- `analog-hub validate` - check config validity

## Technology Stack - Finalized

### **Core Stack**
- **Language**: Python (PyPI distribution)
- **Configuration**: Pydantic BaseModels for YAML parsing/validation
- **CLI Framework**: Click for command-line interface
- **Version Management**: TBD - evaluating options

### **Git Operation Candidates**

#### **Option 1: GitPython + Sparse Checkout**
```python
import git
# Clone with sparse checkout to get only specific paths
repo.git.sparse_checkout('set', 'path/to/library')
```
- Pros: Full git integration, handles refs naturally
- Cons: Still downloads full repo initially

#### **Option 2: Custom Git Commands via subprocess**
```python
import subprocess
# Use git archive to extract specific paths at ref
subprocess.run(['git', 'archive', '--remote=repo_url', 'ref', 'path/'])
```
- Pros: True selective fetch, minimal bandwidth
- Cons: Requires git server support for archive

#### **Option 3: PyGit2 (libgit2 bindings)**
```python
import pygit2
# Lower-level git operations, selective cloning
```
- Pros: Efficient, precise control
- Cons: More complex, additional dependencies

#### **Option 4: GitHub API + Archive Downloads**
```python
import requests
# Download specific subdirectories as ZIP
```
- Pros: Platform-specific optimization
- Cons: Limited to GitHub/GitLab, not generic git

### **Recommended Approach**: GitPython + Sparse Checkout
- Mature, well-maintained library
- Handles all git ref types (branch/tag/commit)
- Good balance of simplicity and functionality

### **Update Strategy - Finalized**
- **Fresh clone every update** - prioritizes reliability over bandwidth
- **Lockfile tracking** (.analog-hub.lock) with resolved commit hashes
- **Immutable overwrites** - complete replacement of library directories
- **State validation** - checksum verification of installed libraries

### **Core Dependencies**
```
GitPython>=3.1.40
pydantic>=2.0.0  
click>=8.1.0
PyYAML>=6.0.0
```

## Core Architecture - Finalized

### **Module Structure**
```
analog-hub/
├── analog_hub/
│   ├── cli/                    # CLI interface (Click)
│   │   ├── main.py            # Main CLI entry point
│   │   └── commands/          # Individual commands
│   ├── core/                   # Business logic
│   │   ├── config.py          # Pydantic models
│   │   ├── git_ops.py         # Git sparse checkout operations
│   │   ├── installer.py       # Library installation logic
│   │   └── lockfile.py        # State tracking (.analog-hub.lock)
│   └── utils/                  # Utilities
│       ├── filesystem.py      # File operations
│       └── validation.py      # Config validation
├── pyproject.toml
└── README.md
```

### **CLI Commands**
- `analog-hub install [library]` - Install libraries
- `analog-hub update [library]` - Update libraries (fresh clone)
- `analog-hub list [--licenses]` - Show installed libraries with license info
- `analog-hub validate` - Validate configuration

### **Key Data Models**
- **AnalogHubConfig**: analog-hub.yaml structure
- **ImportSpec**: Library import specification
- **ExportSpec**: Library export specification (+ license metadata)
- **LockEntry**: Installed library state tracking (+ license snapshots)

## Implementation Status
- **Planning Phase**: Complete ✅
- **Architecture Design**: Complete ✅  
- **Security Setup**: Complete ✅
- **Namespace Protection**: Complete ✅
- **Git Sparse Checkout Prototype**: Complete ✅
- **Ready for Core Implementation**: Next session

## Git Sparse Checkout Prototype Results

### Test Summary ✅
- **Target Repository**: https://github.com/peterkinget/testing-project-template
- **Branch**: PK_PLL_modeling
- **Library Extracted**: `designs/libs/model_pll` (PLL modeling components)
- **Files Extracted**: 10 files (xschem schematics and symbols)
- **Success**: Complete extraction with proper file validation

### Performance Metrics
- **Sparse Checkout Time**: 28.84 seconds
- **Full Clone Time**: 31.64 seconds  
- **Time Efficiency**: 91.2% of full clone (8.8% faster)
- **Sparse Checkout Size**: 167,002,850 bytes
- **Full Clone Size**: 217,796,477 bytes
- **Size Efficiency**: 76.7% of full clone (23.3% reduction)

### Technical Validation
- **GitPython Integration**: Working with git config and sparse checkout
- **Branch Handling**: Successfully switched to non-main branch
- **Path Extraction**: Correctly extracted nested library path
- **File Integrity**: All analog design files (schematics/symbols) intact
- **Cleanup**: Temporary directories properly removed

### Key Implementation Notes
- **Approach**: Clone first, then enable sparse checkout (vs clone with config)
- **Git Commands**: `repo.git.config('core.sparseCheckout', 'true')` works reliably
- **File Structure**: Sparse checkout maintains original directory structure
- **Error Handling**: Graceful handling of missing paths and git errors

### Prototype Conclusions
1. **Technical Feasibility**: ✅ GitPython sparse checkout approach is viable
2. **Performance**: Modest improvements in size/time, significant for large repos
3. **Reliability**: Handles real-world analog design repositories correctly
4. **Production Ready**: Core function ready for integration into main codebase

## ChatGPT Design Review Analysis

### **Strong Agreements** ✅
1. **Open-source focus**: GitHub-centric approach aligns perfectly with IIC-OSIC-TOOLS target
2. **Immutable imports**: Fresh clone + overwrite strategy matches our reliability-first approach
3. **Lockfile tracking**: SHA pinning, checksums, license snapshots - excellent for reproducibility
4. **CLI interface**: Commands align well with our planned interface

### **Valuable Additions to Consider** 🤔
1. **License tracking**: Adding license metadata to exports and lockfile tracking
2. **GitHub optimizations**: Tarball API could be more efficient than sparse checkout
3. **Environment validation**: `analog-hub doctor` for PDK/toolchain compatibility
4. **Configuration separation**: `.analog-hub/` directory structure vs single file

### **Final Design Decisions** ✅
1. **Sparse checkout approach**: Universal git compatibility over GitHub optimization
2. **License tracking**: Added to MVP - critical for analog IP compliance
3. **Single file config**: Start with `analog-hub.yaml`, plan transition to multi-file
4. **Multi-config transition**: Support both formats during migration period

### **Implementation Strategy**
- **Phase 1**: Single file config (`analog-hub.yaml`) with license tracking
- **Phase 2**: Multi-file config support (`.analog-hub/` directory) 
- **Transition**: Both config formats supported simultaneously
- **Git approach**: Sparse checkout for universal compatibility

## Security & Deployment Status

### Repository Security ✅
- **GitHub Repository**: https://github.com/Jianxun/analog-hub
- **Visibility**: Public repository established
- **Initial Commit**: Project structure and documentation

### PyPI Namespace Protection ✅
- **Package Name**: `analog-hub` secured on PyPI
- **Version**: v0.0.0 placeholder uploaded
- **URL**: https://pypi.org/project/analog-hub/0.0.0/
- **Purpose**: Namespace protection against squatting
- **CLI**: Minimal placeholder commands with "Coming soon!" messages

### Package Structure Created ✅
```
analog-hub/
├── analog_hub/              # Python package
│   ├── __init__.py         # v0.0.0 metadata
│   ├── cli/                # CLI interface
│   │   ├── main.py        # Placeholder commands
│   │   └── commands/      # Future command modules
│   ├── core/              # Business logic
│   │   └── config.py      # Pydantic models (partial)
│   └── utils/             # Utilities
├── pyproject.toml         # Package configuration
└── README.md             # Project documentation
```

## Session Summary
Completed comprehensive planning and security setup for analog-hub:
- **Planning**: Defined scope, requirements, and architecture
- **Configuration**: Designed analog-hub.yaml format  
- **Technology**: Chose Python stack (Pydantic, Click, GitPython)
- **Security**: Secured GitHub repo and PyPI namespace with v0.0.0 placeholder
- **Structure**: Created package directory structure
- **Next**: Core implementation of git operations and library management