Architecture Overview
====================

System Components
-----------------

ams-compose follows a layered architecture with three distinct layers. The **core layer** contains business logic modules: 
`LibraryInstaller` orchestrates the entire installation workflow, `RepositoryMirror` handles git operations and local 
caching, `PathExtractor` manages selective file copying with filtering, and `config` provides Pydantic models for 
type-safe configuration and state management.

The **CLI layer** provides a Click-based command interface that acts as a thin facade over the core components, handling 
user input validation and error presentation. The **utils layer** contains shared functionality: `ChecksumCalculator` 
for SHA256-based integrity checking and `LicenseDetector` for automatic IP compliance tracking.

For detailed technical implementation, see:

- :doc:`mirror-system` - Git operations, caching strategies, and performance optimization
- :doc:`extraction-engine` - Three-tier filtering, checksum calculation, and license detection  
- :doc:`component-interactions` - Interface contracts and error propagation patterns

Data Flow
---------

The primary data flow follows a linear pipeline during installation operations. Configuration starts from 
`ams-compose.yaml` parsed into `ComposeConfig` models, which drive mirror updates through `RepositoryMirror` to 
ensure local caches reflect remote repository state. Path extraction then copies selective content via `PathExtractor` 
while applying three-tier filtering rules, followed by lock file updates to persist the new dependency state.

State management maintains consistency across three representations: configuration files define desired state, 
the lock file tracks actual installed state with checksums and metadata, and the file system contains extracted 
libraries. Validation operations reverse this flow by comparing current file checksums against lock file records 
to detect modifications or corruption.

Design Principles
-----------------

The architecture emphasizes **separation of concerns** with distinct modules for mirroring, extraction, and installation 
orchestration, enabling independent testing and reuse. A **single source of truth** principle centralizes all dependency 
state in the lock file, avoiding data inconsistencies and enabling reproducible builds across environments.

**Fail-safe operations** ensure atomic behavior through cleanup mechanisms that remove partial installations on failure, 
while **stateless components** allow each module to function independently without shared mutable state, simplifying 
testing and reducing coupling between components.

For the rationale behind these and other architectural decisions, see :doc:`decision-rationales`.

Module Dependencies
-------------------

`LibraryInstaller` serves as the primary orchestrator, depending on `RepositoryMirror` for git operations, 
`PathExtractor` for file operations, and both utility modules for checksums and license detection. `RepositoryMirror` 
uses `ChecksumCalculator` for SHA256-based repository hashing, while `PathExtractor` integrates both 
`LicenseDetector` for IP compliance and `ChecksumCalculator` for content validation. The CLI layer maintains a clean 
facade pattern by depending only on `LibraryInstaller`, keeping the command interface decoupled from internal 
implementation details.