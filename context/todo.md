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

## Priority 1 (HIGH) - Fix Breaking Changes  
- [ ] **Fix test_extractor_path_resolution.py** - Update method calls and imports
- [ ] **Fix test_extractor_checksum.py** - Update to use ChecksumCalculator correctly
- [ ] **Fix test_extractor_extraction.py** - Update to ExtractionState return types
- [ ] **Fix test_extractor_validation.py** - Update validation methods
- [ ] **Fix test_installer_*.py modules** - Update to use LockEntry, remove LibraryMetadata

## Priority 2 (MEDIUM) - Test Infrastructure  
- [ ] **Update Test Documentation** - Reflect new hierarchy in CLAUDE.md guidelines
- [ ] **Add CLI Command Tests** - Create unit tests for install, update, list commands

## Completed This Sprint ✅
- [x] **Test Structure Refactor** - Moved all tests to 3-tier hierarchy (unit/integration/e2e)
- [x] **Core Metadata Refactor** - Removed MirrorMetadata/LibraryMetadata classes
- [x] **Lightweight Return Types** - Implemented MirrorState/ExtractionState dataclasses  
- [x] **Single Lockfile Architecture** - Eliminated .analog-hub-meta*.yaml files
- [x] **Method Signature Updates** - Updated all core modules (mirror.py, extractor.py, installer.py)

## Definition of Done
- [ ] All tests pass with new architecture
- [ ] No metadata file references in codebase
- [ ] Existing analog-hub.yaml configuration works correctly
- [ ] Test structure follows unit/integration/e2e hierarchy