# Current Sprint

## In Progress
- [ ] **Begin Orchestrator Architecture Refactoring** - Extract LibraryValidator module from installer.py

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
- **README.md Comprehensive Overhaul**: Updated entire README.md to reflect current ams-compose v0.0.0 state
  - Fixed configuration examples (library-root → library_root, added checkin/ignore_patterns fields)
  - Updated command documentation (added clean/schema commands, removed outdated options)
  - Enhanced feature descriptions (license tracking, mirror system, security hardening)
  - Improved installation instructions and Quick Start section
  - Added Advanced Features, Troubleshooting, and comprehensive documentation sections
- **Metadata File Rename and Traceability Enhancement**: Changed .ams-compose-provenance.yaml → .ams-compose-metadata.yaml
  - Updated all source files, tests, and documentation references
  - Fixed generation logic to create metadata for ALL libraries (checkin=true AND checkin=false)
  - Updated gitignore logic to preserve metadata files for non-checkin libraries
  - Enhanced traceability for complete dependency tracking
- **API Simplification Complete**: Updated install_all() method, CLI install command, fixed 27 tests across E2E and unit test suites
  - test_branch_updates.py (4 tests) - Fixed tuple/dict inconsistencies and up_to_date assertions
  - test_gitignore_injection.py (10 tests) - Fixed install_libs[0] patterns to expect dictionary
  - test_local_modifications.py (4 tests) - Fixed library presence and install_status checking
  - test_submodule_support.py - No tuple API issues (separate git infrastructure issue exists)
  - Unit tests - Fixed installer batch tests and CLI tests to expect dictionary returns
- **Branch Management**: Renamed feature/rename-analoghubconfig-to-composeconfig → feature/api-simplification-and-interface-cleanup
- **Context Documentation**: Updated memory.md and todo.md with completion status and next priorities

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