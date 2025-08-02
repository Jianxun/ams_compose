Component Interactions
======================

This document details the interface contracts, error propagation patterns, and state management across ams-compose components, providing developers with dense technical details for understanding module communication.

.. contents:: Table of Contents
   :local:
   :depth: 2

Interface Architecture
----------------------

**Orchestrator Pattern**:
``LibraryInstaller`` serves as the primary orchestrator, coordinating all other components through well-defined interfaces. This pattern isolates complex workflows from individual component responsibilities.

**State Objects**:
Components communicate through lightweight state objects that carry operation results:

- ``MirrorState``: Contains resolved commit hash from mirror operations
- ``ExtractionState``: Contains local path and content checksum from extraction
- ``LockEntry``: Comprehensive state including all dependency metadata

**Error Boundaries**:
Each component maintains clear error boundaries with specific exception types, enabling precise error handling at the orchestrator level.

LibraryInstaller Orchestration Patterns
----------------------------------------

**Installation Workflow**:
The installer orchestrates a linear pipeline with error checkpoints:

.. code-block:: python

   # Simplified installation workflow
   1. config = self.load_config()                    # Pydantic validation
   2. lock_file = LockFile.from_yaml(self.lock_path) # State loading
   3. for library in config.imports:
        a. mirror_state = mirror_manager.update_mirror(repo, ref)
        b. extraction_state = extractor.extract_library(...)
        c. lock_entry = self._create_lock_entry(...)
        d. lock_file.libraries[name] = lock_entry
   4. lock_file.to_yaml(self.lock_path)             # Atomic state save

**Error Propagation Strategy**:
- Configuration errors halt before any operations begin
- Mirror failures isolated per-library with partial success support
- Extraction failures trigger mirror cleanup 
- Lock file corruption handled through backup/recovery

**State Synchronization**:
The installer ensures consistency across three state representations:

1. **Configuration State**: User-declared intent in ``ams-compose.yaml``
2. **Lock State**: Actual installed versions in ``.ams-compose.lock``
3. **Filesystem State**: Physical library files in project directories

Mirror-Installer Interface
--------------------------

**Contract Definition**:
``RepositoryMirror`` exposes a minimal interface focused on repository state management:

.. code-block:: python

   class RepositoryMirror:
       def get_mirror_path(self, repo_url: str) -> Path
       def mirror_exists(self, repo_url: str) -> bool  
       def create_mirror(self, repo_url: str, ref: str) -> MirrorState
       def update_mirror(self, repo_url: str, ref: str) -> MirrorState

**State Communication**:
``MirrorState`` provides the minimal information needed by downstream components:

- ``resolved_commit``: Actual commit SHA for lock file entries

**Error Interface**:
Mirror operations raise specific exceptions that the installer can handle appropriately:

- ``GitOperationTimeout``: Network/timeout issues (retry logic)
- ``git.GitCommandError``: Git operation failures (user feedback)
- ``OSError``: Filesystem issues (permissions, disk space)

**Performance Contract**:
Mirror operations are optimized for repeated access patterns:

- Reference checking: O(1) for local hits, O(network) for fetches
- Mirror creation: One-time cost per repository URL
- Update operations: Incremental for branches, cached for commits/tags

Extractor-Installer Interface
-----------------------------

**Contract Definition**:
``PathExtractor`` handles all file operations with filtering and validation:

.. code-block:: python

   class PathExtractor:
       def extract_library(
           self, 
           mirror_path: Path,
           source_path: str, 
           local_path: str,
           import_spec: ImportSpec
       ) -> ExtractionState

**State Communication**:
``ExtractionState`` provides extraction results for lock file creation:

- ``local_path``: Final installation path (may differ from requested)
- ``checksum``: SHA256 hash for integrity validation

**Filtering Interface**:
Three-tier filtering configuration passed through ``ImportSpec``:

- Built-in patterns: Handled internally by extractor
- Global patterns: Loaded from ``.ams-compose-ignore`` automatically  
- Library patterns: Passed via ``import_spec.ignore_patterns``

**Atomic Operations**:
Extraction operations are atomic with automatic cleanup:

- Temporary directory staging prevents partial installations
- Original content preserved until replacement confirmed
- Error recovery removes partial extractions automatically

Utility Component Integration
-----------------------------

**ChecksumCalculator Integration**:
Used by both mirror and extraction components for different purposes:

- **Mirror**: Repository URL hashing for directory naming
- **Extractor**: Content hashing for integrity validation
- **Installer**: Lock file validation and change detection

**LicenseDetector Integration**:
Integrated at extraction time with configurable behavior:

- **Automatic detection**: Scans mirror directories for license files
- **User override**: Respects ``license`` field in configuration
- **Compliance integration**: Preserves license files for ``checkin=true`` libraries

**Shared State**: License information flows from detection → extraction → lock file

Configuration State Flow
------------------------

**Pydantic Validation Pipeline**:
Configuration flows through strict validation layers:

.. code-block:: text

   YAML → Dict → AnalogHubConfig → ImportSpec → Component APIs

**Validation Boundaries**:
- **Parse-time**: YAML syntax and basic structure validation
- **Model-time**: Pydantic field validation and type checking
- **Runtime**: Path existence and git reference validation

**Error Context Propagation**:
Configuration errors include field-level context for user debugging:

- Field name and invalid value
- Constraint explanation (e.g., "repo must be valid URL")
- Suggestion for correction when possible

Lock File State Management
--------------------------

**Centralized State Pattern**:
All component state converges in the lock file for atomic updates:

.. code-block:: python

   LockEntry:
       repo: str              # From configuration
       ref: str               # From configuration  
       commit: str            # From MirrorState
       source_path: str       # From configuration
       local_path: str        # From ExtractionState  
       checksum: str          # From ExtractionState
       # + timestamps, validation, license metadata

**State Consistency Guarantees**:
- Lock file updates are atomic (write to temp file, then rename)
- All library state updated together or not at all
- Validation performed before any destructive operations

**Cross-Session State Recovery**:
Lock file enables stateless operation recovery:

- Component can reconstruct state from lock entries
- Validation operations compare current vs. recorded state
- Update detection based on configuration vs. lock file differences

Error Handling Architecture
---------------------------

**Exception Hierarchy**:
Component-specific exceptions enable precise error handling:

.. code-block:: text

   InstallationError           # Orchestrator-level failures
   ├── ConfigurationError      # Configuration validation
   ├── MirrorError            # Repository operations  
   │   ├── GitOperationTimeout
   │   └── GitCommandError
   └── ExtractionError        # File operations
       ├── PathValidationError
       └── ChecksumMismatchError

**Error Context Preservation**:
Errors maintain context as they propagate up the call stack:

- Original exception chained for debugging
- User-friendly message for display
- Component context (which library, which operation)

**Recovery Strategies**:
Different error types enable different recovery approaches:

- **Network errors**: Retry with exponential backoff
- **Configuration errors**: Halt with detailed user feedback  
- **Partial failures**: Continue with other libraries, report aggregate results

This component interaction design enables reliable, atomic operations while maintaining clear separation of concerns and comprehensive error handling throughout the system.