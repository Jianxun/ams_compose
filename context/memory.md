# Project Memory

## Current Status
- **Project**: analog-hub - Dependency management tool for analog IC design repositories
- **Stage**: MVP Complete, Test Suite Refactored
- **Last Updated**: 2025-07-26

## Recent Major Changes (Last 2-3 Sessions Only)

### Core Unit Test Breakdown - 2025-07-26
- **Problem**: Monolithic test files (test_extractor.py, test_installer.py) with breaking changes from metadata refactor
- **Solution**: Split into focused modules by responsibility - path resolution, extraction, validation, config, batch ops
- **Status**: In Progress - Files split, but breaking changes need fixing
- **Benefits**: Easier debugging, focused testing, cleaner git diffs

### Metadata Architecture Consolidation - 2025-07-26
- **Problem**: Dual metadata system creates file clutter (.analog-hub-meta*.yaml files)
- **Solution**: Single lockfile architecture with lightweight return types (MirrorState, ExtractionState)
- **Status**: Complete
- **Benefits**: Clean workspace, single source of truth, simplified validation

### Test Suite Refactor - 2025-07-26
- **Problem**: Flat test structure after metadata refactor, unclear organization
- **Solution**: Implemented 3-tier hierarchy (unit/integration/e2e) with logical module organization
- **Status**: Complete - All tests moved to new structure
- **Benefits**: Clear separation by speed/scope, improved TDD workflow, organized by functionality

## Key Architecture Decisions (Stable Decisions Only)
- **Mirror-based approach**: Full clone to .mirror/ directory with SHA256 naming
- **Smart install logic**: Skip libraries that don't need updates
- **Single lockfile**: All state in .analog-hub.lock, no metadata files
- **3-tier test structure**: unit/ (fast, mocked), integration/ (real deps), e2e/ (full workflows)
- **Technology stack**: Python + Click + GitPython + Pydantic

## Active Issues & Next Steps
- **Current Priority**: Fix breaking changes in split test modules
- **Blockers**: LibraryMetadata/MirrorMetadata classes removed, need to update to lightweight State classes
- **Next Session Goals**: Fix individual test modules one-by-one, then validate all tests pass

## Test Modules Created (Need Breaking Change Fixes)
- **test_extractor_path_resolution.py** - Path resolution logic (basic imports work)
- **test_extractor_checksum.py** - Checksum calculation methods
- **test_extractor_extraction.py** - File/directory extraction operations  
- **test_extractor_validation.py** - Library validation and management
- **test_installer_config.py** - Configuration and lockfile operations
- **test_installer_single.py** - Single library installation
- **test_installer_batch.py** - Batch installation operations
- **test_installer_management.py** - Library management operations