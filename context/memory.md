# Project Memory

## Current Status
- **Project**: ams-compose (renamed from analog-hub)
- **Stage**: CLI Interface Improvements Complete
- **Last Updated**: 2025-08-04

## Recent Major Changes (Last 2-3 Sessions Only)

### CLI Logging System Enhancement - 2025-08-04
- **Problem**: Verbose logging was always enabled with -v flag, no granular control over log levels, INFO messages shown by default
- **Solution**: Implemented three-tier logging system - default WARNING (quiet), --verbose for INFO, --debug for DEBUG levels
- **Status**: Complete - Updated _setup_logging() function, added --debug option, modified CLI help text
- **Benefits**: Cleaner default output, granular logging control for troubleshooting, follows standard CLI patterns

### Install Command Hanging Issue Resolution - 2025-08-04
- **Problem**: `ams-compose install` was hanging because it checked remote repositories for updates on every run via network-dependent git fetch operations
- **Solution**: Separated concerns by implementing install vs update command pattern - install only handles missing libraries (fast, no network), added dedicated `update` command for remote checks
- **Status**: Complete - Install command now completes in ~5ms, added comprehensive logging system, all CLI tests passing
- **Benefits**: Fixed hanging issue, dramatically improved performance, cleaner UX following industry standards (npm/pip pattern), better network resilience

### CLI Formatting Refactoring - 2025-08-04  
- **Problem**: CLI formatting functions were long (133 lines), had duplicated status logic appearing 3 times, unused detailed parameter
- **Solution**: Extracted helper functions (_get_entry_status, _show_license_warnings), simplified main functions, removed unused parameters
- **Status**: Complete - Reduced main function from 133 to 42 lines, eliminated code duplication, all tests passing
- **Benefits**: Much more maintainable code, easier to understand and modify, no functional changes to user experience

### CLI Schema and Template Improvements - 2025-08-04
- **Problem**: schema.md was verbose markdown format unsuitable for CLI display, template.yaml caused AWS SAM lint conflicts
- **Solution**: Converted schema.md to plain-text schema.txt, renamed template.yaml to config_template.yaml, extracted template from inline string
- **Status**: Complete - All CLI commands updated, consistent examples between schema and template, lint conflicts resolved
- **Benefits**: Clean CLI-friendly schema output, resolved IDE lint errors, better maintainability with external template file

### Metadata File Rename and Traceability Enhancement - 2025-08-03
- **Problem**: Metadata files named .ams-compose-provenance.yaml only generated for checkin=true libraries, limiting traceability
- **Solution**: Renamed to .ams-compose-metadata.yaml and ensured generation for ALL libraries regardless of checkin setting
- **Status**: Complete - Updated README.md, renamed files in all code/tests/docs, fixed generation logic
- **Benefits**: Full traceability for all dependencies, clearer naming, better compliance tracking

### Install_all() API Simplification Complete - 2025-08-03
- **Problem**: install_all() returned brittle Tuple[Dict[str, LockEntry], Dict[str, LockEntry]] causing 23 E2E test failures
- **Solution**: Simplified to single Dict[str, LockEntry] using existing install_status field ("installed"/"updated"/"up_to_date")
- **Status**: Complete - All 27 tests fixed (18 E2E + 9 unit tests), comprehensive validation passed
- **Benefits**: Robust API, consistent with other methods, eliminates tuple unpacking failures

### Critical Security Vulnerabilities Fixed - 2025-08-03
- **Problem**: Path traversal and git URL injection vulnerabilities discovered during pre-release security review
- **Solution**: Comprehensive security hardening: path validation to prevent directory escape, git URL validation with scheme restrictions, 19 security tests
- **Status**: Complete - All critical vulnerabilities fixed, production-ready security posture
- **Benefits**: Safe for test user release, comprehensive security test coverage

### Interface Freeze Preparation Complete - 2025-08-03
- **Problem**: Need to clean up and stabilize CLI interface and configuration schema before releasing to test users
- **Solution**: Comprehensive interface cleanup: legacy naming removal, CLI simplification, schema standardization, self-documenting features
- **Status**: Complete - All interface improvements implemented and ready for freeze
- **Benefits**: Clean, consistent, self-documenting tool ready for stable interface commitment

### LICENSE File Enhancement Complete - 2025-08-03
- **Problem**: LICENSE files not preserved for partial IP reuse (subdirectory source_paths) + legal compliance gaps
- **Solution**: Always preserve LICENSE files during extraction + inject LICENSE from repository root for partial IP reuse
- **Status**: Complete - PR #9 created, real-world validation with tgate library Apache 2.0 LICENSE
- **Benefits**: Enables partial IP reuse while maintaining legal compliance

## Key Architecture Decisions
- **Mirror-based approach**: Full clone to .mirror/ directory with SHA256 naming
- **Smart install logic**: Skip libraries that don't need updates
- **Single lockfile**: All state in .ams-compose.lock, no metadata files
- **Comprehensive filtering**: Automatic filtering of VCS, development tools, and OS files
- **Technology stack**: Python + Click + GitPython + Pydantic
- **Two-tier dependency model**: checkin=true (commit to repo) vs checkin=false (environment only)

## Active Issues & Next Steps
- **Current Priority**: Install command hanging issue resolved - CLI performance and reliability improvements complete, ready for orchestrator refactoring
- **Implementation Status**: Install/update separation complete, logging system implemented, CLI formatting refactored, all tests passing
- **Recent Achievements**: Fixed major performance bottleneck (install hanging), improved code maintainability, enhanced user experience
- **Branch Status**: Main branch with completed performance improvements
- **Next Session**: Begin Phase 1 of orchestrator architecture refactoring (extract LibraryValidator module from installer.py)