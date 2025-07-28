# Project Memory

## Current Status
- **Project**: analog-hub - Dependency management tool for analog IC design repositories
- **Stage**: MVP Complete, Supply Chain Management Features In Development
- **Last Updated**: 2025-07-28

## Recent Major Changes (Last 2-3 Sessions Only)

### Checkin Control Field Implementation - 2025-07-28
- **Problem**: Need two-tier dependency management - stable environment dependencies vs critical design dependencies for version control
- **Solution**: Added `checkin: bool = True` field to ImportSpec and LockEntry classes with full TDD implementation
- **Status**: Complete - Config models, installer propagation, test coverage, backward compatibility validated
- **Benefits**: Per-library version control configuration, foundation for .gitignore injection, clean supply chain management

### Enhanced Filtering System for Real Repositories - 2025-07-27
- **Problem**: Real repository testing revealed .ipynb_checkpoints causing extraction timeouts, plus .git directory copying security issue
- **Solution**: Comprehensive filtering system covering VCS (.git, .svn), development tools (.ipynb_checkpoints, __pycache__), and OS files (.DS_Store)
- **Status**: Complete - Successfully tested with real GitHub repos, all extraction issues resolved, provisional hooks for future extensibility
- **Benefits**: Reliable real-world usage, clean workspaces, eliminated timeout errors, security improvements, .gitignore integration ready for future

### E2E Test Failures Completely Fixed - 2025-07-27
- **Problem**: 2 remaining E2E test failures after branch update detection fix
- **Solution**: Fixed timestamp handling bug and metadata architecture mismatch
- **Status**: Complete - E2E tests improved from 10/12 → 12/12 (100% pass rate)
- **Benefits**: All E2E workflows validated, system fully stable, ready for production use

### Critical Branch Update Detection Bug Fix - 2025-07-27  
- **Problem**: Smart install logic only checked local state, never checked if remote branches had new commits
- **Solution**: Enhanced installer to fetch remote updates and compare commits; improved mirror checkout to ensure working directory matches target
- **Status**: Complete - Core branch update detection working perfectly
- **Benefits**: Branch update detection working, libraries properly re-extract updated content, smart install logic detects remote updates

### Extractor Test Coverage Improvement - 2025-07-27
- **Problem**: extractor.py had 73% test coverage with 22 missing lines, mostly error handling paths
- **Solution**: Added comprehensive tests for all uncovered code paths including exception handling, cleanup scenarios, and edge cases
- **Status**: Complete - Coverage improved from 73% to 99% (22 missing lines → 1 missing line)
- **Benefits**: Robust error handling validation, comprehensive edge case coverage, improved code reliability

### Test Strategy Optimization - 2025-07-27
- **Problem**: Integration tests used real GitHub repos causing network dependencies, slow execution, brittleness
- **Solution**: Removed integration tests entirely, rely on comprehensive E2E tests with mock repos
- **Status**: Complete - Integration tests removed, test coverage report generated (83% overall)
- **Benefits**: Faster, more reliable test suite; E2E tests provide superior workflow coverage

### Core Unit Test Breaking Changes Fixed - 2025-07-27
- **Problem**: 8 split core unit test modules had breaking changes from metadata refactor (field name changes, method signature changes)
- **Solution**: Updated all test modules to use new LockEntry field names, fixed installer.py validate_installation method to use lightweight architecture
- **Status**: Complete - All 35 core unit tests passing, no metadata file dependencies remaining
- **Benefits**: Clean lightweight architecture, all core tests stable, ready for development
- **Problem**: Monolithic test files (test_extractor.py, test_installer.py) with breaking changes from metadata refactor
- **Solution**: Split into focused modules by responsibility - path resolution, extraction, validation, config, batch ops
- **Status**: Complete - All files split and fixed
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
- **Comprehensive filtering**: Automatic filtering of VCS (.git, .svn), development tools (.ipynb_checkpoints, __pycache__), and OS files (.DS_Store) with provisional hooks
- **2-tier test structure**: unit/ (fast, mocked), e2e/ (full workflows with mock repos)
- **Technology stack**: Python + Click + GitPython + Pydantic

## Recent Design Decisions - 2025-07-28

### Checkin Control Strategy - Library Supply Chain Management
- **Problem**: Need to distinguish between stable environment dependencies vs critical design dependencies for version control
- **Solution**: Add `checkin: bool = True` field to ImportSpec, with automatic .gitignore injection for checkin=false libraries
- **Rationale**: Two-tier dependency model - stable/battle-tested libs (don't commit) vs critical/custom IP (commit to repo)
- **Implementation**: Per-library configuration via analog-hub.yaml, default checkin=true for safety

### User-Configurable Extraction Filtering
- **Problem**: Hardcoded ignore patterns too rigid for real repositories with large files (venv, simulation results, caches)
- **Solution**: Three-tier filtering system using pathspec library for gitignore-style patterns
- **Architecture**: Built-in defaults (VCS/OS) + Global .analog-hub-ignore + Per-library ignore_patterns
- **Benefits**: Performance improvements, familiar syntax, flexible per-use-case control

### License Compliance and Tracking
- **Problem**: Need automatic license detection and compliance checking when copying/redistributing IP
- **Solution**: Automatic license detection from source repos + manual override, with lockfile snapshots
- **Implementation**: Add license field to ImportSpec/LockEntry, detect LICENSE files, display in install/list commands
- **Compliance**: Warn on license changes during updates, require --allow-license-change flag for safety

### Project Rename Strategy - 2025-07-28
- **Decision**: Rename `analog-hub` → `ams-compose` for broader market positioning
- **Rationale**: AMS (Analog/Mixed-Signal) covers entire IC ecosystem, docker-compose pattern familiar to developers
- **Scope**: Package name, config files (analog-hub.yaml → ams-compose.yaml), CLI commands, documentation
- **Timing**: Post-MVP rename after core functionality (checkin, filtering, license features) is complete and stable

## Active Issues & Next Steps
- **Current Priority**: Implement .gitignore injection logic for checkin=false libraries
- **Blockers**: None - checkin field implementation complete, ready for gitignore functionality
- **Next Session Goals**: Complete .gitignore injection, start three-tier filtering system
- **Development Focus**: Automatic version control exclusion based on checkin field
- **Test Strategy**: Unit tests (mocked) → E2E tests (mock repos) → Real repository validation
- **E2E Status**: 12 passed, 0 failed (100% pass rate) ✅ - System fully validated
- **Real Repository Status**: Successfully tested with peterkinget/gf180mcu_fd_sc_mcu9t5v0_symbols and mosbiuschip/switch_matrix_gf180mcu_9t5v0 ✅
- **Coverage Status**: extractor.py 51% (enhanced filtering system), installer.py 76%, mirror.py 20% (needs unit tests)

## Backlog & Future Enhancements
- **Low Priority**: Advanced filtering features (regex patterns, file size limits, content-based filtering)
- **Future**: Integration with foundry PDKs and standard cell libraries for analog design flows

## Test Modules Status (All Core Tests Working - 43/43 passing)
- **test_extractor_path_resolution.py** - ✅ 3 tests - Path resolution logic
- **test_extractor_checksum.py** - ✅ 3 tests - Checksum calculation methods  
- **test_extractor_extraction.py** - ✅ 13 tests - File/directory extraction operations (comprehensive filtering: VCS + development tools)
- **test_extractor_validation.py** - ✅ 8 tests - Library validation and management
- **test_installer_config.py** - ✅ 6 tests - Configuration and lockfile operations
- **test_installer_single.py** - ✅ 2 tests - Single library installation
- **test_installer_batch.py** - ✅ 4 tests - Batch installation operations
- **test_installer_management.py** - ✅ 4 tests - Library management (validate_installation fixed)