Mirror System Architecture
==========================

The ``RepositoryMirror`` class manages local repository caches with intelligent git operations, optimizing for analog IC design workflows where repositories are accessed repeatedly with different references.

.. contents:: Table of Contents
   :local:
   :depth: 2

Design Philosophy
-----------------

The mirror system is built around three core principles:

1. **Network Efficiency**: Minimize redundant network operations through intelligent caching
2. **Reference Flexibility**: Support branches, tags, and commit SHAs with optimized fetch strategies  
3. **Reliability**: Robust error handling with atomic operations and automatic cleanup

This approach optimizes for the analog IC design pattern where designers explore multiple versions of IP libraries during development iteration.

Mirror Directory Structure
--------------------------

**SHA256-Based Organization**:
Mirrors are stored in ``.mirror/`` using SHA256 hashes of repository URLs as directory names:

.. code-block:: text

   .mirror/
   ├── a1b2c3d4e5f6.../  # SHA256 of https://github.com/user/repo1
   │   ├── .git/
   │   └── [repository contents]
   ├── f6e5d4c3b2a1.../  # SHA256 of https://github.com/user/repo2
   │   ├── .git/
   │   └── [repository contents]
   └── ...

**Benefits of SHA256 Naming**:

- **Deduplication**: Identical repository URLs share the same mirror regardless of project
- **Conflict Prevention**: URL variations (trailing slashes, protocols) resolved to unique hashes
- **Security**: Prevents directory traversal attacks from malicious repository URLs
- **Predictability**: Deterministic mapping enables efficient existence checking

**Repository Hash Generation**:
The ``ChecksumCalculator.generate_repo_hash()`` function normalizes URLs before hashing:

1. Remove trailing slashes and ``#`` fragments
2. Normalize protocol specifications (``git+https`` → ``https``)
3. Apply SHA256 to normalized URL
4. Return first 16 characters for directory name balance between uniqueness and readability

Smart Git Operations
--------------------

**Fetch Optimization Strategy**:
The mirror system implements reference-aware fetching to minimize network operations:

**Commit SHA Handling**:
- Check local repository for commit existence using ``repo.commit(sha)``
- Skip fetch if commit already exists locally (immutable property of commits)
- Fall back to full fetch if commit not found

**Tag Handling**:
- Check local tag list before fetching
- Leverage git's tag immutability for optimization
- Support both lightweight and annotated tags

**Branch Handling**:
- Always fetch for branch references (mutable, may have updates)
- Use ``git fetch origin`` to update all branch references
- Checkout specific branch after fetch

**Reference Resolution**:
Smart reference resolution handles ambiguous references:

.. code-block:: python

   # Priority order for reference resolution:
   1. Exact commit SHA (40 characters, hexadecimal)
   2. Tag name match in local tag list
   3. Branch name (requires fetch for latest)
   4. Partial commit SHA (if unambiguous)

Timeout Management
------------------

**Configurable Timeouts**:
- Default 60-second timeout for all git operations
- Extended 300-second timeout for initial clones of large repositories
- Per-operation timeout override capability

**Signal-Based Implementation**:
Uses Unix signals (``SIGALRM``) for reliable timeout enforcement:

.. code-block:: python

   def _with_timeout(self, operation, timeout=None):
       old_handler = signal.signal(signal.SIGALRM, timeout_handler)
       signal.alarm(timeout)
       try:
           return operation()
       finally:
           signal.alarm(0)
           signal.signal(signal.SIGALRM, old_handler)

**Timeout Benefits**:
- Prevents hanging on network issues
- Graceful failure for unreachable repositories
- Configurable limits for different operation types

Atomic Operations and Error Recovery
-------------------------------------

**Atomic Mirror Creation**:
New mirrors are created atomically using temporary directories:

1. Clone to temporary directory with unique name
2. Validate clone success and checkout target reference
3. Move complete repository to final mirror location
4. Clean up temporary directory on success or failure

**Failure Recovery**:
- Partial mirror directories removed on any failure
- Original mirror preserved during updates until replacement confirmed
- Detailed error propagation with context for debugging

**Validation Integration**:
- Repository validity checked using GitPython's repository detection
- Corrupted mirrors automatically detected and recreated
- Graceful fallback to recreation for invalid mirrors

Git Submodule Support
----------------------

**Recursive Cloning**:
The mirror system supports repositories with git submodules through GitPython's built-in capabilities:

- Automatic submodule initialization during clone operations
- Recursive submodule updates for nested dependencies
- Submodule reference resolution using same optimization strategies

**Submodule Optimization**:
- Submodules inherit parent repository's fetch optimization
- Individual submodule mirrors maintained separately for deduplication
- Submodule commit SHAs validated same as parent repository commits

Performance Characteristics
----------------------------

**Network Optimization**:

- **Cache Hit Ratio**: High hit rates for repeated access to same repositories
- **Bandwidth Reduction**: Incremental fetches instead of full clones for updates
- **Concurrent Access**: Multiple projects can share mirrors safely

**Storage Optimization**:

- **Deduplication**: Single mirror per unique repository URL across all projects
- **Sparse Checkout**: Not implemented (extraction handles selectivity instead)
- **Git Object Compression**: Leverages git's built-in object compression

**Timing Characteristics**:

- **Initial Clone**: 10-60 seconds depending on repository size and network
- **Reference Update**: 1-5 seconds for local hits, 5-15 seconds for fetches
- **Mirror Validation**: <1 second for existence checking

**Monitoring Integration**:
Performance metrics available through:

- Clone operation timing in debug logs
- Cache hit/miss rates for different reference types
- Network operation success/failure rates

The mirror system provides a robust foundation for reliable, efficient repository access while optimizing for the specific access patterns common in analog IC design workflows.