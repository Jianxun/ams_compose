# Architecture Review - 2026-03-16

## Scope
- Reviewed repository structure, core modules, CLI, utilities, and representative unit/e2e tests.
- Ran full test suite to assess current baseline health.

## Codebase Snapshot
- Project is a Python CLI dependency manager for analog/mixed-signal IC libraries.
- Main package: `ams_compose/` with subpackages `core/`, `cli/`, and `utils/`.
- Test layout: `tests/unit/` and `tests/e2e/` with broad scenario coverage.
- Primary stack: Click, Pydantic, GitPython, PyYAML, pathspec.

## Repository Structure
- Core modules:
  - `ams_compose/core/installer.py` (653 LOC)
  - `ams_compose/core/extractor.py` (582 LOC)
  - `ams_compose/core/mirror.py` (449 LOC)
  - `ams_compose/core/config.py` (108 LOC)
- CLI:
  - `ams_compose/cli/main.py` (454 LOC)
- Utilities:
  - `ams_compose/utils/checksum.py` (109 LOC)
  - `ams_compose/utils/license.py` (221 LOC)
- Tests:
  - 28 Python test files total (19 unit, 9 e2e)
  - 202 collected tests in current suite

## Architectural Observations

### 1) Strong Functional Coverage, High Core Coupling
- `LibraryInstaller` in `ams_compose/core/installer.py` currently orchestrates many concerns:
  - config + lockfile IO
  - mirror sync/update decisions
  - extraction orchestration
  - validation workflows
  - cleanup workflows
- This centralization speeds iteration but increases coupling and change risk.

### 2) Extractor and Mirror Are Capable but Broad
- `PathExtractor` has solid filtering/security behavior, plus metadata and `.gitignore` policy injection.
- `RepositoryMirror` provides URL validation, timeout wrapping, clone/fetch/update, and submodule handling.
- Both classes are useful but include multiple policy and mechanism responsibilities.

### 3) CLI Is Feature-Rich but Monolithic
- All commands and formatting helpers remain in one file (`ams_compose/cli/main.py`).
- Current command UX and status formatting are good, but modularity is limited for future growth.

### 4) Security and Compliance Practices Are Good
- Path traversal protections are enforced in path resolution and lock-entry path usage.
- URL scheme and suspicious-pattern validation exists before git operations.
- License detection/warning logic is integrated and covered by dedicated tests.

## Test Health and Runtime Baseline

### Test Command
`./venv/bin/python -m pytest`

### Result
- **199 passed, 3 failed, 12 warnings** (out of 202 tests)

### Failing Tests
1. `tests/e2e/test_checksum_race_condition.py::TestChecksumRaceCondition::test_checksum_race_condition_with_checkin_true`
2. `tests/e2e/test_validation_bugs.py::TestValidationBugs::test_git_directory_filtering_fix`
3. `tests/unit/core/test_extractor_extraction.py::TestExtractionOperations::test_extract_library_ignores_git_directories`

### Failure Theme
- All 3 failures are related to `.gitignore` expectations in extracted library directories.
- Current behavior writes a library-local `.gitignore` for checkin policies, while some tests still expect `.gitignore` to be absent/ignored.
- This appears to be a behavior contract mismatch around extractor policy.

### Warnings
- 12 `PytestUnknownMarkWarning` warnings for `@pytest.mark.slow` (marker not registered in pytest config).

## Coverage Highlights (from pytest-cov output)
- Total coverage: **79%**
- Strong core coverage:
  - `ams_compose/core/extractor.py`: 95%
  - `ams_compose/core/installer.py`: 88%
  - `ams_compose/core/config.py`: 98%
- Lower coverage:
  - `ams_compose/core/mirror.py`: 68%
  - `ams_compose/cli/main.py`: 55%

## Risks and Technical Debt
- **Monolithic installer orchestration** slows safe refactors and broadens regression surface.
- **Behavior drift** between test expectations and `.gitignore`/metadata policy indicates unstable contract boundaries.
- **Mirror cleanup implementation** currently removes mirrors in a simplistic way and includes a raw `print()` fallback warning path.
- **CLI file size** and centralized command logic limit maintainability and focused testing.

## Recommended Next Steps
1. **Resolve `.gitignore` contract mismatch first**
   - Decide intended behavior for `checkin=true` and filtering semantics.
   - Align tests and implementation to a single explicit contract.

2. **Proceed with orchestrator refactor already planned in sprint context**
   - Extract validator responsibilities first.
   - Then cleaner responsibilities.
   - Keep installer focused on pure install/update operations.

3. **Register pytest slow marker**
   - Add `slow` marker configuration in `pyproject.toml` under pytest settings.

4. **Improve mirror cleanup logic**
   - Replace broad mirror deletion behavior with reference-aware cleanup.
   - Replace remaining `print()` with logging.

5. **Modularize CLI commands**
   - Split command handlers by feature into `ams_compose/cli/commands/` and keep `main.py` as thin wiring.

## Overall Assessment
- The project has strong momentum, broad test coverage, and useful security/compliance safeguards.
- Main architectural concern is concentration of responsibilities in `LibraryInstaller` and related policy mixing.
- Baseline is close to healthy; resolving the 3 `.gitignore`-contract failures will restore a stable foundation for the planned orchestrator refactor.
