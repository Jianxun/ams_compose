Core Concepts
=============

Project Context
---------------

Analog IC design workflows face the challenge of fragmented IP libraries distributed across multiple repositories, 
each containing extensive boilerplate code alongside the actual IP components. Traditional approaches require copying 
entire repositories to access specific libraries, cluttering projects with unnecessary files and complicating 
dependency management.

ams-compose solves this by enabling selective extraction of specific paths from any repository, combined with supply 
chain management features like license tracking and version control integration. Unlike git submodules which integrate 
entire repositories, ams-compose extracts only the needed components while maintaining full provenance and update 
capabilities.

The tool targets analog IC designers using open-source toolchains who need curated IP libraries without git complexity, 
providing a dependency management approach similar to package managers but optimized for analog design workflows.

Mirror System
-------------

ams-compose maintains local repository mirrors in the `.mirror/` directory, using SHA256 hashes of repository URLs 
as directory names for deduplication. The mirror system performs smart update detection by comparing local commit 
hashes against remote repository state, fetching only when updates are available. Full git submodule support ensures 
complex dependencies with nested repositories are properly resolved during mirroring operations.

Selective Extraction
--------------------

The extraction system copies specific paths from mirrors while automatically filtering version control directories 
(`.git`, `.svn`), development artifacts (`__pycache__`, `.ipynb_checkpoints`), and OS files (`.DS_Store`). A three-tier 
filtering approach combines built-in patterns, global `.ams-compose-ignore` files, and per-library ignore patterns 
using gitignore-style syntax. For libraries marked `checkin=true`, LICENSE files are automatically preserved regardless 
of filtering rules to maintain IP compliance.

Lock Files
----------

The `.ams-compose.lock` file serves as the single source of truth for dependency state, tracking repository URLs, 
resolved commit hashes, local paths, and content checksums for each installed library. Lock entries include installation 
timestamps, license information, and validation status to support provenance tracking and compliance auditing. This 
centralized state enables reproducible builds and dependency validation across different environments.

Smart Install Logic
-------------------

Installation operations skip libraries that are already at the correct version by comparing configuration specifications 
against lock file entries and verifying remote repository state. Updates are triggered when repository URLs, references, 
or source paths change in configuration, when local library files are missing, or when remote repositories contain newer 
commits. Force mode bypasses all smart detection to unconditionally reinstall all specified libraries.

IP Integrity Validation
------------------------

SHA256 checksums detect unauthorized modifications to installed libraries by comparing current library state against 
checksums stored in the lock file. The validation system identifies libraries with local changes, missing files, or 
checksum mismatches, protecting against accidental modifications and ensuring reproducible builds. This integrity 
checking supports supply chain security by detecting tampering with imported IP components.