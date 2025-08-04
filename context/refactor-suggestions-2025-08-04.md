Breaking the large CLI and core modules into smaller, more maintainable units is a great next step, especially since you’re committed to preserving the existing user interface. Here are some pragmatic guidelines for approaching the refactor:

1. **Identify cohesive sub‑responsibilities.**

   * In `ams_compose/cli/main.py`, distinct concerns include logging configuration, library listing/formatting, and individual command handlers for `install`, `update`, `list`, `validate`, `init`, `clean` and `schema`. You can start by extracting:

     * **Output formatting** functions (e.g., `_format_libraries_tabular`, `_format_libraries_detailed`) into a dedicated module like `cli/formatters.py` so they can be reused by other CLIs or tests.
     * **Error handling and logging setup** into `cli/utils.py` or `cli/logging.py`, encapsulating `_setup_logging` and `_handle_installation_error`.
     * Each Click command can be moved to its own file under `cli/commands/` (e.g., `install.py`, `update.py`). The top‑level `main.py` would import these commands and register them with the Click group, preserving the same CLI surface.

2. **Separate business logic from orchestration.**
   In `installer.py`, `mirror.py` and `extractor.py`, different layers of responsibility are already evident:

   * **Repository mirroring** (cloning, updating, cleanup) is well encapsulated in `RepositoryMirror`. If the file feels too long, you could move URL validation and timeout helpers into a `mirror.utils` submodule and keep high‑level `RepositoryMirror` methods focused on operations.
   * **Path extraction** handles ignore patterns, metadata, license injection and copying. You could further separate:

     * ignore‐pattern logic and helpers into `extractor/ignore_rules.py`,
     * license/provenance injection into `extractor/license_injection.py`,
     * and keep `PathExtractor` focused on coordinating these helpers.
   * **Installer** orchestrates mirror + extraction and maintains lockfile state. Consider a `install/decision.py` module for skip/update logic (`_resolve_target_libraries` and `_determine_libraries_needing_work`) and a `install/lockfile.py` helper for reading/writing the lockfile. The core `LibraryInstaller` class can then delegate to these helpers.

3. **Introduce clearer domain objects.**
   Pydantic models already define `ImportSpec`, `LockEntry`, etc. To keep backwards compatibility, you can leave their interfaces untouched but reorganize them into a package structure like `ams_compose/models` or `ams_compose/schema`. The import path (`from ams_compose.core.config import ImportSpec`) would continue to work if you re-export the models in `core/config.py`.

4. **Use explicit public APIs to preserve backwards compatibility.**
   Even if internal modules move, maintain the same public import paths by re-exporting classes and functions. For example, after moving `_format_libraries_tabular` into a new module, keep `ams_compose/cli/main.py` exporting it so existing code continues to work:

   ```python
   # ams_compose/cli/main.py
   from .formatters import format_libraries_tabular as _format_libraries_tabular
   ```

   This allows internal restructuring without breaking user scripts that import from these modules.

5. **Write integration tests to ensure parity.**
   Since you want to honor the v0.1.0 interface, tests should assert that the CLI commands behave identically before and after refactoring. End‑to‑end CLI tests using Click’s testing runner can capture output and exit codes for common workflows. Unit tests for your new helpers can focus on smaller, easier‑to‑test functionality, and they will help you avoid accidental regressions.

6. **Iterative refactoring.**
   Refactor incrementally: move one concern at a time and verify that the CLI still works. Use `git bisect` friendly commits to keep the history clear. Don’t try to perfect the entire architecture in one pass.

By decomposing based on cohesive responsibilities and re‑exporting public APIs, you can improve maintainability while keeping the user experience consistent.
