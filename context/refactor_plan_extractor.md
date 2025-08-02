# PathExtractor Refactoring Plan - Orchestrator Architecture Integration

## Current State Analysis

The `PathExtractor` class (483 lines) has multiple responsibilities that need to be distributed across the new orchestrator architecture to align with the installer refactoring plan.

## Current Responsibilities Breakdown

### 1. **Filtering Logic** (Lines 30-192)
- Pattern definitions (VCS, dev tools, OS files)
- Global ignore file loading
- Three-tier filtering system with nested function
- License file preservation logic

### 2. **Metadata Generation** (Lines 194-276)  
- Provenance metadata generation
- Gitignore injection for checkin=false libraries

### 3. **Path Operations** (Lines 278-399)
- Local path resolution
- Library extraction workflow
- Error handling and cleanup

### 4. **Library Management** (Lines 400-483)
- Library validation and checksum calculation
- Library removal operations  
- Installed library discovery

## Refactoring Strategy - Orchestrator Integration

### **Keep in PathExtractor** (Core Extraction Engine - ~200 lines)
**Focus**: Pure file operations and filtering capabilities

```python
class PathExtractor:
    """Core file extraction engine with filtering capabilities."""
    
    # Pattern definitions and filtering logic
    VCS_IGNORE_PATTERNS = {...}
    DEV_TOOL_IGNORE_PATTERNS = {...} 
    OS_IGNORE_PATTERNS = {...}
    
    # Core filtering methods (Lines 79-192)
    def _load_global_ignore_patterns(self) -> List[str]
    def _create_ignore_function(self) -> Callable  # Fix nested function issue
    
    # Path resolution (Lines 278-298)
    def _resolve_local_path(self) -> Path
    
    # Pure extraction operations (Lines 346-367)
    def extract_files(self, source_path: Path, dest_path: Path, import_spec: ImportSpec) -> None
    
    # Library discovery (Lines 443-463)
    def list_installed_libraries(self) -> Dict[str, Path]
```

### **Move to LibraryManager (Orchestrator)** (~150 lines)
**Focus**: High-level workflow coordination and metadata management

- **Extraction orchestration** (Lines 326-399): Full `extract_library()` workflow
- **Metadata coordination** (Lines 368-377): Provenance generation calls
- **Error handling** (Lines 391-398): High-level exception management and cleanup
- **State management**: Lockfile updates and extraction result tracking

### **Move to LibraryValidator** (~80 lines)
**Focus**: Validation and state checking

- **Library validation** (Lines 400-418): `validate_library()` with checksum validation  
- **Checksum operations** (Lines 465-483): `calculate_library_checksum()`

### **Move to LibraryCleaner** (~100 lines)
**Focus**: Maintenance and cleanup operations

- **Library removal** (Lines 420-441): `remove_library()` operations
- **Gitignore management** (Lines 247-276): `_inject_gitignore_if_needed()`
- **Workspace cleanup**: Integration with existing cleaner responsibilities

## Critical Issues to Address

### 1. **Nested Function Problem** (Lines 142-192)
```python
def _create_ignore_function(self, ...):  # Method level
    def ignore_function(directory: str, filenames: list) -> list:  # 50-line nested function
        # Complex filtering logic that should be extracted
```

**Solution**: Extract nested function to separate method `_apply_ignore_filters()`

### 2. **Workflow Coordination**
Current `extract_library()` method handles too many concerns:
- Path resolution → Keep in PathExtractor
- File copying → Keep in PathExtractor  
- Metadata generation → Move to LibraryManager
- Gitignore injection → Move to LibraryCleaner
- Checksum calculation → Move to LibraryValidator

## Module Dependencies After Refactoring

```
CLI Commands → LibraryManager → {Installer, Validator, Cleaner}
                            ↓
                      {PathExtractor, Mirror, License Utils}
```

## Implementation Phases

### Phase 1: Fix Nested Function Issue
- Extract `ignore_function` from `_create_ignore_function()`
- Create `_apply_ignore_filters()` method
- Improve testability of filtering logic

### Phase 2: Extract Validator Components
- Move validation methods to `LibraryValidator`
- Move checksum calculation methods
- Update dependencies and imports

### Phase 3: Extract Cleaner Components  
- Move removal operations to `LibraryCleaner`
- Move gitignore management logic
- Integrate with existing cleaner responsibilities

### Phase 4: Create Orchestrator Integration
- Move high-level extraction workflow to `LibraryManager`
- Move metadata generation coordination
- Update CLI to use orchestrator pattern

### Phase 5: Refine PathExtractor
- Focus on pure file operations and filtering
- Clean up remaining responsibilities
- Optimize for performance and testability

## Benefits

1. **Clear Separation**: PathExtractor becomes focused file operation engine
2. **Orchestrator Coordination**: LibraryManager handles complex workflows  
3. **Specialist Components**: Validator and Cleaner handle specific concerns
4. **Improved Testability**: Each component can be tested independently
5. **Maintainable Architecture**: Easy to extend and modify individual components
6. **Fixed Nested Functions**: Better code organization and testability

## Success Criteria

- PathExtractor focused on file operations and filtering only
- No nested function definitions (extract `ignore_function`)
- Clear workflow coordination through LibraryManager
- All existing functionality preserved
- 100% test coverage maintained across all new modules
- Integration with existing installer refactoring plan