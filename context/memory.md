# Project Memory

## Current Status
- **Project**: ams-compose (renamed from analog-hub)
- **Stage**: API Simplification Complete
- **Last Updated**: 2025-08-03

## Recent Major Changes (Last 2-3 Sessions Only)

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
- **Current Priority**: API Simplification Complete - Ready for orchestrator architecture refactoring
- **Implementation Status**: All install_all() API changes complete - 27 tests fixed across E2E and unit test suites
- **Test Coverage**: 18 E2E tests passing (test_branch_updates.py, test_gitignore_injection.py, test_local_modifications.py), 9 unit tests passing
- **Next Session**: Begin Phase 1 of orchestrator architecture refactoring (extract LibraryValidator module)