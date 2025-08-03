# ams-compose.yaml Configuration Schema

## Root Configuration

```yaml
# Default directory where libraries will be installed
library_root: designs/libs              # type: string, default: "designs/libs"
                                         # Description: Default root directory for imported libraries
                                         #              (used when local_path not specified)

# Library imports dictionary  
imports:                                 # type: dict, optional, default: {}
                                         # Description: Libraries to import
  library_name:                          # Unique identifier for the library
    # REQUIRED FIELDS
    repo: https://github.com/user/repo   # type: string, required
                                         # Description: Git repository URL
    
    ref: main                            # type: string, required  
                                         # Description: Git reference (branch, tag, or commit)
    
    source_path: lib/                    # type: string, required
                                         # Description: Path within repo to extract
    
    # OPTIONAL FIELDS
    local_path: custom/path              # type: string, optional, default: {library_root}/{library_name}
                                         # Description: Local path override (defaults to {library_root}/{import_key}).
                                         #              If specified, overrides library_root completely.
    
    checkin: true                        # type: boolean, optional, default: true
                                         # Description: Whether to include this library in version control
    
    ignore_patterns:                     # type: array of strings, optional, default: []
      - "*.log"                          # Description: Additional gitignore-style patterns to ignore during extraction
      - "build/"
    
    license: MIT                         # type: string, optional, default: auto-detected
                                         # Description: Override for library license (auto-detected if not specified)
```

## Complete Example

```yaml
# ams-compose configuration file
library_root: designs/libs

imports:
  # Production IP library (checked into version control)
  analog_lib:
    repo: https://github.com/company/analog-ip.git
    ref: v1.2.0
    source_path: lib/analog
    checkin: true
    license: MIT
    
  # Development tools (excluded from version control)  
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
    
  # PDK library (partial extraction with custom license)
  pdk:
    repo: https://github.com/foundry/pdk.git
    ref: stable
    source_path: models
    license: Proprietary
```

## Field Reference

### Root Level Fields
- **library_root**: Default installation directory for all libraries
  - Used when `local_path` is not specified for individual libraries
  - Creates path as: `{library_root}/{library_name}`

### Import Specification Fields  
- **repo**: Git repository URL (supports https, ssh, file protocols)
- **ref**: Any valid git reference (branch name, tag, commit SHA)
- **source_path**: Path within repository to extract (use "." for entire repo)
- **local_path**: Override default path construction (optional)
- **checkin**: Controls version control inclusion (affects .gitignore injection)
- **ignore_patterns**: Additional files/patterns to exclude during extraction
- **license**: Manual license override (useful for proprietary or complex licenses)

## Usage Commands
```bash
ams-compose init                         # Create new configuration file
ams-compose install                      # Install all libraries
ams-compose install library_name         # Install specific library
ams-compose list                         # Show installed libraries  
ams-compose validate                     # Validate configuration and installation
ams-compose clean                        # Clean unused mirrors and orphaned libraries
ams-compose schema                       # Show this schema documentation
```