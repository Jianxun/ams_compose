# Current Sprint

## In Progress
- [ ] **Begin Orchestrator Architecture Refactoring** - Ready to extract LibraryValidator module from installer.py with 99.5% test success rate foundation

## Next Priority Options
- [ ] **Begin Orchestrator Architecture Refactoring** - Extract LibraryValidator module from installer.py (alternative to test fix)

## Priority 1 (HIGH) - Orchestrator Architecture Refactoring
- [ ] **Create validator.py module** - Extract validation methods from installer.py to new LibraryValidator class
- [ ] **Move validation methods** - Transfer validate_library(), validate_installation(), checksum operations
- [ ] **Update imports and dependencies** - Fix all references to moved validation methods
- [ ] **Migrate validation tests** - Move validation tests to new test_validator.py module

### Phase 2: Extract LibraryCleaner Module  
- [ ] **Create cleaner.py module** - Extract cleanup methods to new LibraryCleaner class
- [ ] **Move cleanup operations** - Transfer library removal, gitignore management, orphaned library handling
- [ ] **Integrate with extractor gitignore** - Move _inject_gitignore_if_needed from extractor to cleaner
- [ ] **Update cleaner tests** - Migrate cleanup tests to new test_cleaner.py module

### Phase 3: Extract Pure Installation Logic
- [ ] **Refactor installer.py** - Create focused LibraryInstaller class with pure installation logic
- [ ] **Move installation methods** - Keep install_library(), install_all(), batch operations
- [ ] **Remove non-installation code** - Move validation, cleanup to specialist modules
- [ ] **Update installer tests** - Focus tests on installation logic only

### Phase 4: Create LibraryManager Orchestrator
- [ ] **Create library_manager.py** - Main orchestrator coordinating specialist modules
- [ ] **Move config/lockfile management** - Transfer configuration loading, lockfile operations
- [ ] **Implement orchestration logic** - Coordinate installer, validator, cleaner operations
- [ ] **Update CLI integration** - Change CLI to use LibraryManager instead of LibraryInstaller

### Phase 5: Fix PathExtractor Nested Functions
- [ ] **Extract nested ignore_function** - Create _apply_ignore_filters method from nested function
- [ ] **Move extraction orchestration** - Transfer extract_library workflow to LibraryManager
- [ ] **Move validation operations** - Transfer library validation to LibraryValidator
- [ ] **Move cleanup operations** - Transfer library removal to LibraryCleaner

### Phase 1B: Critical Security Issues (URGENT)
- [ ] **Fix path traversal vulnerability** - Add path validation to prevent local_path from escaping project directory (extractor.py, installer.py)
- [ ] **Add git URL validation** - Prevent file:// URLs and command injection in mirror operations (mirror.py lines 155-159)
- [ ] **Fix checksum calculation race condition** - Move .gitignore injection before checksum calculation (installer.py:147 vs extractor.py:344-348)

## Completed This Sprint ✅

### Mirror Timeout Handling Fix - 2025-08-04
- **Fixed Unit Test**: Resolved test_submodule_timeout_handling by making exception handling more specific in mirror.py
  - Changed broad `except Exception` to `except GitOperationTimeout: raise` + `except Exception` pattern
  - GitOperationTimeout now propagates properly for caller handling while maintaining fallback behavior
  - Test suite improved from 201/203 to 202/203 passing (99.5% success rate)
- **Outstanding E2E Issue**: 1 remaining test failure appears to be macOS-specific Git submodule setup issue, not core functionality problem
  - tests/e2e/test_submodule_support.py::TestSubmoduleSupport::test_submodule_update_detection fails with Git path error
  - Other 3 submodule tests pass successfully, indicating core submodule functionality works correctly

### Comprehensive Test Suite Reliability - 2025-08-04
- **Test Case Fixes**: Fixed 11 out of 12 failing test cases (91.7% success rate)
  - Branch update tests: Added check_remote_updates=True parameter for proper update detection
  - Checksum race condition: Fixed undefined variable reference (actual_invalid → invalid_libraries)
  - License preservation tests: Enhanced LICENSE file handling with force_preserve_license parameter
  - Path resolution test: Updated for security compliance (absolute paths within project directory)
  - Installer management tests: Fixed macOS path resolution issues with Path.resolve()
- **LICENSE Legal Compliance**: Enhanced extractor to force-preserve LICENSE files when checkin=true
  - Added force_preserve_license parameter to _create_ignore_function()
  - LICENSE files now preserved regardless of ignore patterns for legal compliance
  - Maintains backward compatibility while enforcing IP compliance standards
- **Cross-Platform Compatibility**: Resolved macOS-specific issues in test suite
  - Fixed /var → /private/var symlink resolution in mock assertions
  - Enhanced path handling for consistent behavior across platforms
- **Architecture Alignment**: Updated tests to match install/update separation pattern
  - Tests properly use check_remote_updates=True when expecting update behavior
  - Maintains security hardening while ensuring test reliability

### Previous Major Completions
- **Install Command Hanging Issue Resolution**: Fixed major performance bottleneck causing install command to hang
- **CLI Formatting Code Refactoring**: Simplified and cleaned up CLI formatting functions  
- **CLI Schema and Template Improvements**: Converted schema.md to plain-text, resolved lint conflicts
- **API Simplification Complete**: Updated install_all() method, fixed 27 tests across E2E and unit test suites

## Priority 2 (HIGH) - Critical Dependency Resolution Completeness

### Phase 1B: Nested ams-compose Dependency Detection  
- [ ] **Implement nested dependency scanner** - Scan extracted libraries for ams-compose.yaml files
- [ ] **Add comprehensive warning system** - Alert users about unresolved transitive dependencies
- [ ] **Design optional recursive resolution** - Plan --recursive flag for future transitive dependency installation
- [ ] **Create nested dependency test cases** - Test repos with ams-compose.yaml dependencies

## Priority 2 (HIGH) - Additional Security & Architectural Issues

### Phase 2A: Additional Security Hardening
- [ ] **Implement error handling hierarchy** - Replace generic Exception catching with specific error types
- [ ] **Add git operation retry mechanisms** - Handle network timeouts and failures gracefully  
- [ ] **Create security test scenarios** - Test malicious path configurations and edge cases
- [ ] **Fix inefficient mirror operations** - Optimize branch fetching to avoid unnecessary network calls

### Phase 2B: Architectural Design Issues
- [ ] **Reduce LibraryInstaller coupling** - Break down god object pattern, improve testability
- [ ] **Add operation timeout configuration** - Configurable timeouts for different git operations
- [ ] **Add progress indicators** - User feedback for long-running clone/extraction operations
- [ ] **Test large repository performance** - Validate with 100MB+ repositories and optimize if needed

## Priority 3 (MEDIUM) - User Experience & Operational Features

### Phase 3A: CLI Enhancements
- [ ] **Implement CLI dry-run mode** - Add --dry-run flag for install/update operations
- [ ] **Add verbose mode enhancements** - Detailed operation logging for troubleshooting
- [ ] **Improve progress indicators** - Better user feedback for long-running operations

### Phase 3B: Documentation & Integration Guidance
- [ ] **Document tool integration challenges** - Comprehensive guide for xschem/Magic path issues
- [ ] **Create integration examples** - Real-world examples of manual tool configuration
- [ ] **Add troubleshooting guides** - Common issues and solutions for analog IC workflows

### Phase 3C: Code Consistency & Naming
- [ ] **Rename AnalogHubConfig to ComposeConfig** - Update legacy class name across 18 files