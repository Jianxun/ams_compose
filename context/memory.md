# Project Memory

## Current Status
- **Project**: ams-compose (renamed from analog-hub)
- **Stage**: Orchestrator Architecture Refactoring Planning Phase
- **Last Updated**: 2025-08-02

## Critical Bugs Identified - License File Feature Branch
- **Bug 1**: Checksum calculated before .gitignore injection causing validation failures
- **Bug 2**: LICENSE files not preserved with real repositories  
- **Bug 3**: E2E tests expect main .gitignore modification but implementation uses library-specific .gitignore files
- need to grab the PyPI namespace ASAP [DONE]
- tag the repo with proper versions.
- Build documentation with sphinx
- include examples 
- disclaimer that `ams-compose` is a dependency management tool, the repo owner is solely responsible to be meet all license compliance with the IPs checked into their repos.

## Recent Major Changes (Last 2-3 Sessions Only)

### Orchestrator Architecture Refactoring Planning - 2025-08-02
- **Problem**: Both installer.py (565 lines) and extractor.py (483 lines) have grown too large with multiple responsibilities
- **Solution**: Comprehensive refactoring plan for 4-module orchestrator architecture: LibraryManager (orchestrator), Installer, Validator, Cleaner
- **Status**: Planning Complete - Detailed refactoring plans created for both installer and extractor modules
- **Benefits**: Clear separation of concerns, improved testability, maintainable architecture, elimination of nested function issues

## Recent Major Changes (Previous Sessions)

### Unified CLI Formatting Implementation (TDD Cycles 1-5) - 2025-08-02
- **Problem**: CLI/core separation violations with inconsistent data contracts - validate_installation() returned tuple, install had print statements, validate/install/list used different return types
- **Solution**: Complete TDD implementation with 5 cycles: unified data structures, removed all print statements from core, implemented tabular formatting across all CLI commands
- **Status**: Cycles 1-5 Complete - All CLI commands (list/validate/install) now use consistent tabular format with proper column alignment, status display, and license warnings
- **Benefits**: Clean tabular output, perfect CLI consistency, eliminated core/CLI violations, up-to-date libraries properly displayed, unified warning system

### CLI/Core Separation Analysis & Unified LockEntry Architecture Design - 2025-08-02
- **Problem**: Inconsistent data contracts across CLI commands - list uses Dict[str, LockEntry], validate uses Tuple[List[str], List[str]], install mixes print statements
- **Solution**: Proposed unified LockEntry architecture where all operations return Dict[str, LockEntry] with validation_status field, single-library validation methods, orchestration-level iteration
- **Status**: Analysis Complete - Identified clean separation violations, designed unified approach with validate_library() taking single LockEntry parameter
- **Benefits**: Perfect consistency across commands, rich error context, better composability, simpler CLI formatting, extensible validation framework

### Comprehensive Architectural Review & Security Analysis - 2025-08-02
- **Problem**: Need thorough architectural assessment to identify design issues, security vulnerabilities, and production readiness gaps
- **Solution**: Complete architectural review covering component interactions, business logic assumptions, security vulnerabilities, and performance issues
- **Status**: Complete - 10 major categories of issues identified with prioritized recommendations, documented in context/architecture-review.md
- **Benefits**: Clear understanding of critical security vulnerabilities, architectural debt, and roadmap for production hardening

### Documentation System Development - 2025-08-02
- **Problem**: Need comprehensive documentation for both human users and AI agents to efficiently understand project concepts
- **Solution**: Built structured Sphinx documentation starting with core concepts and architecture overview
- **Status**: Complete - Core concepts and architecture overview written with concise, focused content
- **Benefits**: Clear project context, technical implementation details, optimized for readability and AI consumption

### Git Submodule Support Implementation - 2025-08-01
- **Problem**: Critical architectural gap - repositories with git submodules had empty submodule directories after extraction, leading to incomplete library installations
- **Solution**: Complete TDD implementation of submodule support with recurse_submodules=True in clone operations, _update_submodules() method, and comprehensive test coverage
- **Status**: Complete - 5 unit tests + 4 E2E tests implemented, feature committed to feature/submodule-support branch
- **Benefits**: End-to-end submodule extraction working, analog IC libraries with dependencies now fully functional, major dependency resolution gap closed

### ChatGPT Design Review Analysis & Architectural Assessment - 2025-08-01
- **Problem**: External code review identified strengths, weaknesses, and critical architectural gaps in dependency resolution
- **Solution**: Comprehensive analysis of ChatGPT review findings, identification of submodule and nested dependency issues, strategic roadmap for production robustness
- **Status**: Analysis Complete - Strategic direction established for next development sprint
- **Benefits**: Clear understanding of production-readiness gaps, prioritized roadmap for dependency resolution completeness, security and robustness improvements

### Architectural Gaps Discovery - Deep Dependency Resolution - 2025-08-01
- **Problem**: Current mirror system missing submodule support and nested ams-compose dependency resolution, creating incomplete library installations
- **Solution**: Identified two critical gaps: (1) git clone without --recurse-submodules leaves submodule directories empty, (2) nested ams-compose.yaml files never processed for transitive dependencies
- **Status**: Analysis Complete - Implementation strategy defined for submodule support and nested dependency detection
- **Benefits**: Understanding of complete dependency resolution requirements, clear separation of submodule vs nested ams-compose handling, foundation for robust analog IC workflows

### Value Proposition Analysis - ams-compose vs Git Submodules - 2025-08-01
- **Problem**: Need to clearly understand competitive advantages over native git submodules for analog IC design workflows
- **Solution**: Comprehensive analysis showing ams-compose advantages: selective path extraction, supply chain management, intelligent filtering, cross-repository flexibility, analog-specific features
- **Status**: Complete - Strategic positioning clarified for analog IC design market
- **Benefits**: Clear differentiation from git submodules, focus on selective IP extraction and curation rather than full repository integration

### License File Inclusion & Provenance Metadata Implementation - 2025-07-29
- **Problem**: Need automatic LICENSE file preservation and IP compliance tracking for checkin=true libraries in analog IC design workflows
- **Solution**: Enhanced PathExtractor with license file preservation, automatic provenance metadata generation, and comprehensive IP traceability
- **Status**: Complete - Session 1 implemented with 8 unit tests + 4 E2E tests, all tests passing, feature committed
- **Benefits**: IP compliance for checked-in libraries, automatic license preservation, detailed provenance metadata with source traceability, legal audit support

### Critical Bug Fixes: Enhanced .gitignore Injection & Strict Validation - 2025-07-29
- **Problem**: Two user-reported issues: (1) YAML typos silently ignored, (2) .gitignore injection modifying main .gitignore + user request for directory visibility
- **Solution**: Fixed Pydantic validation extra="allow" → extra="forbid", redesigned .gitignore injection with self-referential placeholders for directory visibility
- **Status**: Complete - Both issues fully resolved, PR #4 created and ready for merge
- **Benefits**: Clear error messages for config typos, directory visibility with informative .gitignore files, no user conflicts, self-documenting approach

### Project Package Distribution & Installation - 2025-07-29
- **Problem**: Need to rename project from analog-hub to ams-compose for broader AMS IC market positioning
- **Solution**: Systematic 6-phase rename approach starting with core Python module structure
- **Status**: Phase 1 Complete - Core Python module renamed (analog_hub/ → ams_compose/), all imports updated (21 files, 41 import statements)
- **Benefits**: Clean foundation for comprehensive rename, maintained functionality, ready for configuration updates

### Supply Chain Management Features Complete - 2025-07-29
- **Problem**: Need comprehensive supply chain management for analog IC dependency tracking
- **Solution**: Complete implementation of checkin control, .gitignore injection, three-tier filtering, and license detection
- **Status**: Complete - PR #2 merged to main, all 99/100 unit tests + 29/29 E2E tests passing
- **Benefits**: Production-ready supply chain management, IP compliance tracking, two-tier dependency model

### License Detection and Tracking Implementation - 2025-07-28
- **Problem**: Need automatic license detection and compliance checking for supply chain management and IP tracking
- **Solution**: Comprehensive license detection system with auto-detection, user overrides, and compatibility warnings
- **Status**: Complete - Full license detection engine, CLI integration, 20 unit tests with 93% coverage, all E2E tests passing
- **Benefits**: Automatic IP compliance tracking, supply chain visibility, early warning for license conflicts, foundation for advanced IP management

### Three-Tier Filtering System Implementation - 2025-07-28
- **Problem**: Need user-configurable extraction filtering for performance optimization and flexible per-use-case control
- **Solution**: Implemented three-tier filtering: built-in defaults + global .analog-hub-ignore + per-library ignore_patterns using pathspec library
- **Status**: Complete - Clean maintainable built-in rules, gitignore-style pattern matching, comprehensive test coverage (unit + E2E)
- **Benefits**: Easy addition/removal of built-in rules, familiar gitignore syntax, global + per-library configuration, performance improvements

### .gitignore Injection Implementation - 2025-07-28
- **Problem**: Need automatic version control exclusion for checkin=false libraries without manual .gitignore maintenance
- **Solution**: Implemented automatic .gitignore management with dynamic library entry addition/removal based on checkin field
- **Status**: Complete - Full TDD implementation, comprehensive E2E test coverage, IP repository .gitignore filtering validated
- **Benefits**: Seamless two-tier dependency management, automatic version control exclusion, clean project workspace, preserved existing .gitignore content

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
- **Current Priority**: Execute orchestrator architecture refactoring - Start with Phase 1 (installer.py validator extraction)
- **Recent Achievement**: Comprehensive refactoring plans completed for both installer and extractor modules
- **Architectural Status**: Ready to implement 4-module architecture: LibraryManager (orchestrator), Installer, Validator, Cleaner
- **Planning Complete**: Detailed phase-by-phase implementation strategy defined
- **Critical Issues Identified**: Nested function in extractor.py, monolithic installer.py responsibilities, coupling issues
- **Next Session**: Begin Phase 1 - Extract LibraryValidator from installer.py

## Tool Integration Complexity Analysis - 2025-08-01
- **Problem**: Beyond file copying, analog tools (xschem, Magic, ngspice) require path rewriting and library registration for proper integration
- **Analysis**: Current ams-compose treats IP as passive file collections, but tools need active integration (path rewriting in .xschemrc, .magicrc, library registration)
- **Strategic Decision**: User responsible for tool integration complexity during MVP phase, potential future "schematic re-base tool" for automated path rewriting
- **Rationale**: Tool diversity, project specificity, user expertise, and risk management favor manual integration over automated path rewriting initially

## Backlog & Future Enhancements
- **Medium Priority**: Tool integration documentation (xschem/Magic path challenges), schematic re-base tool for automated path rewriting
- **Low Priority**: Advanced filtering features (regex patterns, file size limits, content-based filtering)
- **Future**: Integration with foundry PDKs and standard cell libraries for analog design flows

## Test Modules Status (All Core Tests Working - 64/64 passing)
- **test_extractor_path_resolution.py** - ✅ 3 tests - Path resolution logic
- **test_extractor_checksum.py** - ✅ 7 tests - Checksum calculation methods  
- **test_extractor_extraction.py** - ✅ 13 tests - File/directory extraction operations (comprehensive filtering: VCS + development tools)
- **test_extractor_validation.py** - ✅ 12 tests - Library validation and management
- **test_installer_config.py** - ✅ 11 tests - Configuration and lockfile operations (includes checkin field tests)
- **test_installer_gitignore.py** - ✅ 4 tests - .gitignore injection functionality (NEW)
- **test_installer_single.py** - ✅ 2 tests - Single library installation
- **test_installer_batch.py** - ✅ 4 tests - Batch installation operations
- **test_installer_management.py** - ✅ 4 tests - Library management (validate_installation fixed)

## E2E Test Modules Status (All E2E Tests Working - 24/24 passing)
- **test_branch_updates.py** - ✅ 4 tests - Branch update detection and smart install logic
- **test_local_modifications.py** - ✅ 4 tests - Local modification detection and checksum validation
- **test_validation_bugs.py** - ✅ 3 tests - Bug fixes and edge cases (orphaned libraries, checksum, git filtering)
- **test_version_pinning.py** - ✅ 4 tests - Version pinning and commit/tag tracking
- **test_gitignore_injection.py** - ✅ 10 tests - .gitignore injection functionality (NEW)