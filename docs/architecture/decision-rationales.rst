Architectural Decision Rationales
==================================

This document consolidates the key architectural decisions made during ams-compose development, providing the problems, solutions, trade-offs, and benefits for efficient retrieval by developers.

.. contents:: Table of Contents
   :local:
   :depth: 2

Mirror-Based Repository Strategy
--------------------------------

**Decision**: Use full repository mirroring with selective extraction instead of direct partial clone operations.

**Problem**: Analog IC designers need specific paths from repositories containing extensive boilerplate (documentation, examples, test suites) that clutters their projects.

**Solution**: Mirror complete repositories in ``.mirror/`` using SHA256-hashed directory names, then selectively extract needed paths to project directories.

**Trade-offs**:

- **Cost**: Higher disk usage for complete repository mirrors
- **Benefit**: Enables offline operations, faster subsequent extractions, and git submodule support
- **Benefit**: Eliminates repeated network operations for the same repository

**Rationale**: Analog design workflows often involve iterative exploration of IP libraries. Full mirroring optimizes for repeated access patterns common in design iteration, while SHA256 naming prevents repository URL conflicts and enables deduplication across projects.

Single Lock File Consolidation
-------------------------------

**Decision**: Consolidate all dependency state into a single ``.ams-compose.lock`` file instead of per-library metadata files.

**Problem**: Multiple metadata files scattered across library directories create consistency issues and complicate state management.

**Solution**: Centralize all library state (commit hashes, checksums, timestamps, validation status) in one lock file with Pydantic validation.

**Trade-offs**:

- **Cost**: Single point of failure for dependency state
- **Benefit**: Atomic state updates, simplified validation, clear dependency provenance
- **Benefit**: Enables reproducible builds through centralized version control

**Rationale**: Single source of truth principle eliminates state inconsistencies that plagued earlier dual-metadata approaches. Critical for analog design where IP provenance and reproducibility are essential for design verification and manufacturing.

Three-Tier Filtering Architecture
----------------------------------

**Decision**: Implement filtering through built-in patterns, global ``.ams-compose-ignore``, and per-library ``ignore_patterns`` fields.

**Problem**: Need flexible file filtering that balances automation with user control for diverse analog design repository structures.

**Solution**: 
1. **Built-in tier**: Hardcoded patterns for VCS directories (``.git``, ``.svn``), development tools (``__pycache__``, ``.ipynb_checkpoints``), and OS files (``.DS_Store``)
2. **Global tier**: Project-wide ``.ams-compose-ignore`` file using gitignore syntax
3. **Per-library tier**: Library-specific ``ignore_patterns`` in ``ams-compose.yaml``

**Trade-offs**:

- **Cost**: Increased complexity in filtering logic implementation
- **Benefit**: Granular control without overwhelming users with configuration
- **Benefit**: Sensible defaults reduce configuration burden for common cases

**Rationale**: Analog IC repositories have diverse structures (netlists, schematics, documentation, examples). Three-tier approach provides automation for common patterns while enabling precise control for specialized analog design file types.

Supply Chain Management Design
-------------------------------

**Decision**: Implement two-tier dependency model with ``checkin`` field controlling version control inclusion and automatic license preservation.

**Problem**: Analog IC design involves both trusted internal IP (should be version-controlled) and external IP (may have licensing restrictions preventing check-in).

**Solution**: 
- **checkin=true**: Extract libraries to version control, automatically preserve LICENSE files regardless of filtering
- **checkin=false**: Extract libraries to ``.gitignore``-excluded directories, skip in CI/build processes

**Trade-offs**:

- **Cost**: Complexity in handling two dependency classes
- **Benefit**: Supports both open-source and commercial analog IP workflows
- **Benefit**: Automatic license compliance reduces legal risk

**Rationale**: Analog design often mixes open-source PDKs (suitable for version control) with commercial IP blocks (licensing restrictions). Two-tier model supports both use cases while maintaining legal compliance through automatic license preservation.

Pydantic Configuration Validation
----------------------------------

**Decision**: Use Pydantic models for all configuration and state validation instead of manual YAML parsing.

**Problem**: Configuration errors in analog design workflows can lead to incorrect IP integration and costly design errors.

**Solution**: Define strict Pydantic models (``ComposeConfig``, ``LockEntry``, ``ImportSpec``) with type validation, field constraints, and descriptive error messages.

**Trade-offs**:

- **Cost**: Additional dependency and slightly more verbose configuration definition
- **Benefit**: Early error detection, clear validation messages, automatic serialization
- **Benefit**: IDE support with type hints for configuration editing

**Rationale**: Analog IC designers often lack extensive software development experience. Pydantic provides clear, immediate feedback for configuration errors, reducing debugging time and preventing incorrect IP integration.

Checksum-Based Integrity Validation
------------------------------------

**Decision**: Use SHA256 checksums for library content validation instead of git commit verification alone.

**Problem**: Need to detect unauthorized modifications to imported analog IP that could affect design verification or introduce licensing issues.

**Solution**: Calculate SHA256 checksums of extracted library content during installation, store in lock file, and validate against current content during operations.

**Trade-offs**:

- **Cost**: Additional computation and storage for checksum calculation
- **Benefit**: Detects any content modification regardless of git repository state
- **Benefit**: Supports supply chain security for imported analog IP

**Rationale**: Analog IC design requires high confidence in IP integrity for design verification and legal compliance. File-level checksums provide stronger guarantees than git-level validation, especially for IP that may be modified outside git workflows.

Orchestrator Pattern Implementation
-----------------------------------

**Decision**: Implement ``LibraryInstaller`` as an orchestrator that coordinates ``RepositoryMirror``, ``PathExtractor``, and utility components.

**Problem**: Complex installation workflow involves multiple operations (mirroring, extraction, validation) that need coordination and error handling.

**Solution**: Single orchestrator class that manages component lifecycle, handles errors gracefully, and provides atomic installation operations.

**Trade-offs**:

- **Cost**: Additional abstraction layer increases initial complexity
- **Benefit**: Clean separation of concerns, testable components, atomic error handling
- **Benefit**: Enables independent testing and reuse of mirror/extraction logic

**Rationale**: Analog design workflows require reliable, atomic operations. Orchestrator pattern ensures that partial failures are handled gracefully and that the system remains in a consistent state, critical for design environment stability.