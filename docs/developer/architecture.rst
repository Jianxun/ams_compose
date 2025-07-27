Architecture Overview
=====================

analog-hub is designed around a modular architecture optimized for analog IC design workflows.

System Overview
---------------

.. code-block:: text

   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
   │   CLI Layer     │    │  Configuration  │    │   Lockfile      │
   │                 │    │  (YAML)         │    │  (.lock)        │
   └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
   ┌─────────────────────────────────┼─────────────────────────────────┐
   │                    Core Layer   │                                 │
   │  ┌─────────────┐  ┌─────────────┼─────────────┐  ┌─────────────┐  │
   │  │  Installer  │  │  Extractor  │  Mirror     │  │   Config    │  │
   │  │             │  │             │  Manager    │  │   Parser    │  │
   │  └─────────────┘  └─────────────┼─────────────┘  └─────────────┘  │
   └─────────────────────────────────┼─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────┼─────────────────────────────────┐
   │                 Utils Layer     │                                 │
   │  ┌─────────────┐  ┌─────────────┼─────────────┐  ┌─────────────┐  │
   │  │  Checksum   │  │  Git Ops    │  File Ops   │  │  Validation │  │
   │  │  Calculator │  │             │             │  │             │  │
   │  └─────────────┘  └─────────────┼─────────────┘  └─────────────┘  │
   └─────────────────────────────────┼─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────┼─────────────────────────────────┐
   │               File System       │                                 │
   │                                 │                                 │
   │  .mirror/          designs/libs/           .analog-hub.lock       │
   │  ├── repo1/        ├── lib1/               (lockfile)             │
   │  └── repo2/        └── lib2/                                      │
   └─────────────────────────────────┼─────────────────────────────────┘

Core Components
---------------

Config Parser (analog_hub.core.config)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Parse and validate ``analog-hub.yaml`` configuration files.

**Key Classes**:

* ``AnalogHubConfig``: Main configuration model
* ``LibraryConfig``: Individual library configuration
* ``LockEntry``: Lockfile entry model

**Responsibilities**:

* YAML parsing and validation
* Pydantic model validation
* Configuration merging and defaults
* Environment variable substitution

Mirror Manager (analog_hub.core.mirror)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Manage Git repository mirrors in the ``.mirror/`` directory.

**Key Classes**:

* ``MirrorManager``: Main mirror management class
* ``MirrorState``: Mirror status information

**Responsibilities**:

* Git clone and fetch operations
* Branch/tag/commit resolution
* Mirror directory management
* Repository state tracking

**Mirror Directory Structure**:

.. code-block:: text

   .mirror/
   ├── 1a2b3c4d5e6f/  # SHA256 hash of repository URL
   │   ├── .git/
   │   └── [repository files]
   └── 7f8e9d0c1b2a/
       ├── .git/
       └── [repository files]

Extractor (analog_hub.core.extractor)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Extract specific paths from mirrored repositories to library directories.

**Key Classes**:

* ``LibraryExtractor``: Main extraction logic
* ``ExtractionState``: Extraction result information

**Responsibilities**:

* Sparse path extraction from Git repositories
* File copying with metadata preservation
* Checksum calculation for integrity
* Library directory management

**Extraction Process**:

1. Checkout specific Git reference in mirror
2. Copy specified paths to target directory
3. Calculate checksums for extracted files
4. Preserve file permissions and timestamps

Installer (analog_hub.core.installer)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Orchestrate the complete installation process.

**Key Classes**:

* ``LibraryInstaller``: Main installation coordinator
* ``InstallationResult``: Installation outcome

**Responsibilities**:

* Configuration loading and validation
* Installation workflow coordination
* Smart update detection
* Lockfile management
* Error handling and reporting

**Installation Workflow**:

1. Load and validate configuration
2. Read existing lockfile
3. Determine which libraries need updates
4. Mirror repositories (if needed)
5. Extract library paths
6. Update lockfile
7. Report results

CLI Layer (analog_hub.cli)
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Provide command-line interface for all operations.

**Key Components**:

* ``main.py``: CLI entry point and command definitions
* Click-based command structure
* Error handling and user feedback
* Progress reporting

Data Models
-----------

Configuration Models
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class LibraryConfig(BaseModel):
       name: str
       url: str
       ref: str = "main"
       paths: List[str]

   class AnalogHubConfig(BaseModel):
       libraries: List[LibraryConfig]

State Models
~~~~~~~~~~~~

.. code-block:: python

   class MirrorState(NamedTuple):
       exists: bool
       current_ref: Optional[str]
       needs_update: bool

   class ExtractionState(NamedTuple):
       success: bool
       checksum: str
       extracted_files: List[Path]

   class LockEntry(BaseModel):
       name: str
       url: str
       ref: str
       commit_sha: str
       installed_at: datetime
       checksum: str

File System Layout
------------------

Project Structure
~~~~~~~~~~~~~~~~~

.. code-block:: text

   my-analog-project/
   ├── analog-hub.yaml          # Configuration file
   ├── .analog-hub.lock         # Lockfile (auto-generated)
   ├── .mirror/                 # Git mirrors (hidden)
   │   ├── 1a2b3c4d5e6f/       # Mirrored repository
   │   └── 7f8e9d0c1b2a/       # Another mirrored repository
   ├── designs/
   │   └── libs/                # Extracted libraries
   │       ├── core_analog/     # Library directory
   │       └── process_models/  # Another library
   └── [your design files]     # Project-specific files

Library Directory Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   designs/libs/core_analog/
   ├── amplifiers/
   │   ├── ota_5t/
   │   │   ├── ota_5t.sch
   │   │   ├── ota_5t.sym
   │   │   └── ota_5t.spice
   │   └── diffamp/
   │       ├── diffamp.sch
   │       └── diffamp.sym
   └── filters/
       └── rc_filter/
           ├── rc_filter.sch
           └── rc_filter.spice

Algorithm Details
-----------------

Smart Update Detection
~~~~~~~~~~~~~~~~~~~~~~

The installer uses a smart algorithm to minimize unnecessary operations:

1. **Mirror Check**: Compare local mirror commit with remote HEAD
2. **Lockfile Check**: Compare current configuration with lockfile
3. **Checksum Check**: Verify extracted files haven't been modified
4. **Decision Matrix**: Determine update necessity

.. code-block:: python

   def needs_update(self, library: LibraryConfig) -> bool:
       # Check if mirror needs updating
       if self.mirror_manager.needs_update(library.url, library.ref):
           return True
       
       # Check if library configuration changed
       lock_entry = self.get_lock_entry(library.name)
       if not lock_entry or lock_entry.ref != library.ref:
           return True
       
       # Check if extracted files are intact
       if not self.extractor.validate_checksum(library.name, lock_entry.checksum):
           return True
       
       return False

Checksum Calculation
~~~~~~~~~~~~~~~~~~~~

File integrity is ensured through SHA256 checksums:

.. code-block:: python

   def calculate_library_checksum(self, library_path: Path) -> str:
       """Calculate checksum for all files in a library directory."""
       file_hashes = []
       for file_path in sorted(library_path.rglob("*")):
           if file_path.is_file():
               with open(file_path, "rb") as f:
                   file_hash = hashlib.sha256(f.read()).hexdigest()
                   rel_path = file_path.relative_to(library_path)
                   file_hashes.append(f"{rel_path}:{file_hash}")
       
       combined = "\n".join(file_hashes)
       return hashlib.sha256(combined.encode()).hexdigest()

Error Handling Strategy
-----------------------

Hierarchical Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **CLI Layer**: User-friendly messages and exit codes
2. **Core Layer**: Specific exceptions with context
3. **Utils Layer**: Low-level operation errors

Error Categories
~~~~~~~~~~~~~~~~

* **ConfigurationError**: Invalid configuration files
* **GitError**: Git operation failures
* **FileSystemError**: File operation failures
* **ValidationError**: Data validation failures

Example Error Flow:

.. code-block:: python

   try:
       installer.install_library(library_config)
   except GitError as e:
       click.echo(f"Git operation failed: {e.message}")
       click.echo(f"Suggestion: {e.suggestion}")
       sys.exit(3)
   except FileSystemError as e:
       click.echo(f"File operation failed: {e.message}")
       sys.exit(4)

Performance Considerations
--------------------------

Git Operations
~~~~~~~~~~~~~~

* **Shallow Clones**: Use ``--depth=1`` for faster initial clones
* **Sparse Checkout**: Extract only required paths
* **Mirror Reuse**: Reuse mirrors across multiple extractions
* **Parallel Operations**: Future enhancement for concurrent library processing

File Operations
~~~~~~~~~~~~~~~

* **Incremental Copying**: Copy only changed files
* **Checksum Caching**: Cache checksums to avoid recalculation
* **Permission Preservation**: Maintain file metadata during copy

Memory Usage
~~~~~~~~~~~~

* **Streaming Operations**: Process large files in chunks
* **Cleanup**: Automatic cleanup of temporary files
* **Resource Management**: Proper context management for file handles

Testing Architecture
---------------------

Two-Tier Testing Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

**Unit Tests** (``tests/unit/``):

* Fast execution (< 1 second each)
* Mocked external dependencies
* Focused on individual functions/methods
* High coverage requirements (>90%)

**E2E Tests** (``tests/e2e/``):

* Complete workflow testing
* Mock repositories with realistic structures
* User scenario validation
* Integration between components

Test Organization
~~~~~~~~~~~~~~~~~

.. code-block:: text

   tests/
   ├── unit/
   │   ├── core/
   │   │   ├── test_extractor_*.py    # Extractor unit tests
   │   │   ├── test_installer_*.py    # Installer unit tests
   │   │   └── test_mirror_*.py       # Mirror unit tests
   │   └── utils/
   │       └── test_checksum.py       # Utility tests
   └── e2e/
       ├── test_branch_updates.py     # Branch update scenarios
       ├── test_local_modifications.py # Local modification detection
       └── test_version_pinning.py    # Version pinning workflows

This architecture provides a solid foundation for analog IC design library management while maintaining flexibility for future enhancements.