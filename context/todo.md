# Current Sprint: Fix Core Unit Test Breaking Changes

## Sprint Goal
Fix breaking changes in split core unit test modules after metadata refactor.

## New Test Structure (Broken - Needs Fixes) 🔧
```
tests/
├── unit/                          # Fast isolated tests (~50ms each)
│   ├── core/
│   │   ├── test_extractor_path_resolution.py     # Path resolution logic 🔧
│   │   ├── test_extractor_checksum.py            # Checksum calculations 🔧  
│   │   ├── test_extractor_extraction.py          # File/dir extraction 🔧
│   │   ├── test_extractor_validation.py          # Validation & management 🔧
│   │   ├── test_installer_config.py              # Config & lockfile ops 🔧
│   │   ├── test_installer_single.py              # Single library install 🔧
│   │   ├── test_installer_batch.py               # Batch install ops 🔧
│   │   ├── test_installer_management.py          # Library management 🔧
│   │   └── test_config.py        # Configuration models - MISSING
│   │   └── test_mirror.py        # RepositoryMirror - MISSING
│   ├── utils/
│   │   └── test_checksum.py      # ChecksumCalculator ✅
│   └── cli/
│       └── test_init.py          # Init command ✅
└── integration/ & e2e/           # Working ✅
```

## In Progress  
- No active tasks

## Priority 1 (HIGH) - Next Development Phase
- [ ] **CLI Command Tests** - Create unit tests for install, update, list commands
- [ ] **Integration Test Updates** - Update integration tests for new architecture

## Priority 2 (MEDIUM) - Test Infrastructure  
- [ ] **Update Test Documentation** - Reflect new hierarchy in CLAUDE.md guidelines
- [ ] **Add CLI Command Tests** - Create unit tests for install, update, list commands

## Completed This Sprint ✅
- [x] **Test Structure Refactor** - Moved all tests to 3-tier hierarchy (unit/integration/e2e)
- [x] **Core Metadata Refactor** - Removed MirrorMetadata/LibraryMetadata classes
- [x] **Lightweight Return Types** - Implemented MirrorState/ExtractionState dataclasses  
- [x] **Single Lockfile Architecture** - Eliminated .analog-hub-meta*.yaml files
- [x] **Method Signature Updates** - Updated all core modules (mirror.py, extractor.py, installer.py)
- [x] **Fixed Core Unit Tests** - All 8 core test modules working (35/35 tests passing)
  - [x] test_extractor_path_resolution.py - 3 tests - Path resolution logic
  - [x] test_extractor_checksum.py - 3 tests - Checksum calculation methods
  - [x] test_extractor_extraction.py - 5 tests - File extraction operations
  - [x] test_extractor_validation.py - 8 tests - Library validation and management
  - [x] test_installer_config.py - 6 tests - Configuration and lockfile operations
  - [x] test_installer_single.py - 2 tests - Single library installation
  - [x] test_installer_batch.py - 4 tests - Batch installation operations
  - [x] test_installer_management.py - 4 tests - Library management (validate_installation fixed)

## Definition of Done
- [x] All tests pass with new architecture - ✅ 35/35 core unit tests passing
- [x] No metadata file references in codebase - ✅ validate_installation method fixed
- [x] Existing analog-hub.yaml configuration works correctly - ✅ Config tests passing
- [x] Test structure follows unit/integration/e2e hierarchy - ✅ Complete