Extraction Engine Architecture
==============================

The ``PathExtractor`` class manages selective file copying from repository mirrors to project directories, implementing a sophisticated three-tier filtering system with provenance tracking and integrity validation.

.. contents:: Table of Contents
   :local:
   :depth: 2

Core Design Pattern
-------------------

The extraction engine follows a pipeline pattern with distinct phases:

1. **Path Resolution**: Determine source paths in mirrors and target paths in project
2. **Filtering Setup**: Configure three-tier ignore patterns and special handling rules  
3. **Extraction**: Copy files using ``shutil.copytree`` with custom ignore function
4. **Post-processing**: Generate checksums, detect licenses, create provenance metadata

This design enables atomic operations with rollback capability and clear separation between filtering logic and file operations.

Path Resolution Logic
---------------------

**Source Path Resolution**:
The extractor resolves source paths within repository mirrors using the ``source_path`` field from ``ImportSpec``. Path resolution handles both absolute paths (interpreted relative to repository root) and relative paths.

**Target Path Resolution**:
Target paths follow a priority hierarchy:

1. **Explicit override**: ``local_path`` field in configuration completely overrides default behavior
2. **Default composition**: ``{library_root}/{library_name}`` where ``library_root`` defaults to ``libs``
3. **Absolute resolution**: All paths resolved relative to ``project_root`` for consistency

**Path Validation**:
The extractor validates that target paths don't escape the project directory and source paths exist within mirrors before beginning extraction operations.

Three-Tier Filtering Implementation  
------------------------------------

The filtering system combines three layers of ignore patterns, processed in order with later tiers taking precedence:

**Tier 1: Built-in Patterns**
Hardcoded pattern sets with exact filename matching:

- **VCS patterns**: ``.git``, ``.gitignore``, ``.gitmodules``, ``.svn``, ``.hg``, ``CVS``
- **Development patterns**: ``__pycache__``, ``.ipynb_checkpoints``, ``node_modules``, ``.vscode``
- **OS patterns**: ``.DS_Store``, ``Thumbs.db``, ``desktop.ini``

Built-in patterns use set intersection for O(1) lookup performance and are maintained as class constants for easy extension.

**Tier 2: Global Patterns**
Project-wide ``.ams-compose-ignore`` file using gitignore syntax:

- Loaded once per extraction operation for efficiency
- Supports gitignore patterns including wildcards, negation, and directory matching
- Graceful fallback to empty pattern list if file missing or unreadable

**Tier 3: Per-Library Patterns**
Library-specific ``ignore_patterns`` field in ``ams-compose.yaml``:

- Highest precedence in filtering hierarchy
- Enables library-specific customization without affecting global rules
- Combined with global patterns into single ``pathspec`` matcher for efficiency

**Pattern Matching Engine**:
Tiers 2 and 3 use the ``pathspec`` library for gitignore-compatible pattern matching. The system tests multiple path variants for robust matching:

- Direct filename (``filename``)
- Relative path (``./{filename}``)
- Directory with trailing slash (``filename/``, ``./{filename}/``)

This multi-variant approach handles edge cases in gitignore pattern behavior.

**License File Preservation**:
Special override logic preserves LICENSE files when ``checkin=true``, regardless of any filtering rules. This ensures IP compliance by maintaining license information in version-controlled libraries.

Checksum Calculation Strategy
-----------------------------

**Algorithm**: SHA256 hashing for cryptographic-grade integrity verification

**Scope**: Content-based checksums calculated after extraction, including:

- All file contents in extracted library directory
- Relative file paths to detect structural changes
- File modification times excluded to support reproducible builds

**Performance Optimization**:
- Checksums calculated incrementally during directory traversal
- Large files processed in chunks to manage memory usage
- Cached checksum results stored in lock file to avoid recalculation

**Validation Integration**:
Checksums enable three validation scenarios:

1. **Installation verification**: Immediate checksum after extraction
2. **Runtime validation**: Compare current content against lock file checksums
3. **Update detection**: Changed checksums trigger library updates

This approach provides stronger integrity guarantees than git commit verification alone, detecting any content modifications regardless of repository state.

License Detection Engine
------------------------

**Detection Strategy**:
The ``LicenseDetector`` utility scans repository mirrors for common license files using filename pattern matching:

- **Primary patterns**: ``LICENSE``, ``LICENSE.txt``, ``LICENSE.md``
- **Secondary patterns**: ``COPYING``, ``NOTICE``, ``COPYRIGHT``
- **Case-insensitive matching**: Handles ``license.txt``, ``License``, etc.

**Content Analysis**:
When license files are found, the detector attempts basic license type identification through pattern matching against common license text snippets (MIT, Apache, GPL, BSD).

**Integration Points**:

1. **Extraction**: Automatic license preservation for ``checkin=true`` libraries
2. **Provenance**: License information embedded in ``.ams-compose-meta.yaml`` files
3. **Lock file**: License metadata stored for compliance tracking

**Fallback Behavior**:
When automatic detection fails, the system falls back to user-specified ``license`` field in configuration, ensuring license information is always available for compliance purposes.

Provenance Metadata Generation
-------------------------------

**Purpose**: Generate ``.ams-compose-meta.yaml`` files for ``checkin=true`` libraries to maintain full supply chain provenance.

**Metadata Structure**:

.. code-block:: yaml

   ams_compose_version: "1.0.0"
   extraction_timestamp: "2024-01-15T10:30:00Z"
   library_name: "example_lib"
   source:
     repository: "https://github.com/example/repo"
     reference: "v1.2.3"
     commit: "abc123def456..."
     source_path: "libs/example"
   license:
     detected: "MIT"
     user_specified: null
     files: ["LICENSE", "COPYING"]

**Integration with Version Control**:
Provenance files are automatically included when ``checkin=true``, providing audit trail for imported IP without requiring external tools or databases.

Error Handling and Atomicity
-----------------------------

**Atomic Operations**:
Extraction operations are atomic through temporary directory staging:

1. Extract to temporary directory with unique name
2. Validate extraction success (checksum, required files)
3. Atomic move from temporary to final location
4. Clean up temporary directory on success or failure

**Failure Recovery**:
- Partial extractions cleaned up automatically
- Original library content preserved until new extraction confirmed
- Detailed error messages with context for debugging

**Validation Integration**:
Post-extraction validation ensures extracted content matches expectations before finalizing the operation, preventing corrupted installations.