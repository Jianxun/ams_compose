# LibraryInstaller Refactoring Plan - 4 Focused Modules

## Current State
The `installer.py` file has grown to 565 lines with multiple responsibilities that need to be separated for better maintainability and testability.

## Proposed Module Structure

### 1. **Library Manager** (`library_manager.py` - ~120 lines)
Main orchestrator class responsible for coordination:
- `LibraryManager` class (renamed from `LibraryInstaller`)
- Configuration/lockfile loading and saving
- Public API coordination: delegates to specialists
- Component initialization and dependency injection
- High-level workflow orchestration

### 2. **Installer** (`installer.py` - ~200 lines)
Pure installation operations:
- `LibraryInstaller` class
- `install_library()` - Single library installation with mirroring
- `install_all()` - Batch installation with smart skip logic
- `_resolve_target_libraries()` - Target resolution from config
- `_determine_libraries_needing_work()` - Smart skip logic
- License change tracking and install status management

### 3. **Validator** (`validator.py` - ~120 lines)
Validation and state checking:
- `LibraryValidator` class  
- `validate_library()` - Single library validation
- `validate_installation()` - Full installation validation
- `list_installed_libraries()` - Current state listing
- Orphaned library detection and missing library handling

### 4. **Cleaner** (`cleaner.py` - ~100 lines)
Maintenance and cleanup operations:
- `LibraryCleaner` class
- `clean_unused_mirrors()` - Remove unused repository mirrors
- `clean_orphaned_libraries()` - Remove libraries not in config
- `update_gitignore_for_library()` - Manage .gitignore files
- General workspace cleanup utilities

## Module Dependencies
```
CLI Commands → LibraryManager → {Installer, Validator, Cleaner}
                            ↓
                      {Mirror, Extractor, License Utils}
```

## Benefits
1. **Clear Separation**: Each module has a single, well-defined responsibility
2. **Focused Testing**: Easier to write comprehensive unit tests for each component
3. **Independent Development**: Teams can work on different aspects without conflicts
4. **Logical Naming**: Module names clearly indicate their purpose
5. **Scalable Architecture**: Easy to add new capabilities (e.g., dependency resolver)

## Migration Strategy
1. **Extract specialists** while keeping `LibraryManager` API compatible
2. **Update imports** in CLI and existing code
3. **Migrate tests** to new structure
4. **Verify functionality** with existing workflows

This structure aligns with domain-driven design principles and makes the codebase much more maintainable.

## Implementation Plan

### Phase 1: Extract Validator Module
- Move validation methods from `installer.py` to new `validator.py`
- Create `LibraryValidator` class
- Update imports and dependencies

### Phase 2: Extract Cleaner Module  
- Move cleanup methods to new `cleaner.py`
- Create `LibraryCleaner` class
- Update gitignore management logic

### Phase 3: Extract Installation Logic
- Move pure installation logic to refactored `installer.py`
- Create focused `LibraryInstaller` class
- Keep batch logic and smart skip functionality

### Phase 4: Create Library Manager Orchestrator
- Create new `library_manager.py` as main coordinator
- Move config/lockfile management to orchestrator
- Update CLI to use `LibraryManager` instead of `LibraryInstaller`

### Phase 5: Update Tests and Documentation
- Migrate existing tests to new module structure
- Update documentation to reflect new architecture
- Verify all functionality works as expected