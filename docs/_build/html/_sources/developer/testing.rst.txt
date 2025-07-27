Testing Guide
=============

analog-hub uses a comprehensive testing strategy to ensure reliability and maintainability.

Testing Philosophy
------------------

Our testing approach follows these principles:

* **Test-Driven Development**: Write tests before implementation
* **High Coverage**: Maintain >90% test coverage
* **Fast Feedback**: Unit tests complete in seconds
* **Realistic Scenarios**: E2E tests use realistic analog design workflows
* **Maintainable**: Tests are easy to understand and modify

Test Structure
--------------

Two-Tier Architecture
~~~~~~~~~~~~~~~~~~~~~

**Unit Tests** (``tests/unit/``):
  Fast, isolated tests with mocked dependencies

**End-to-End Tests** (``tests/e2e/``):
  Complete workflow tests with mock repositories

.. code-block:: text

   tests/
   ├── unit/                        # Fast unit tests
   │   ├── core/                    # Core module tests
   │   │   ├── test_extractor_*.py  # Extractor component tests
   │   │   ├── test_installer_*.py  # Installer component tests
   │   │   └── test_mirror_*.py     # Mirror manager tests
   │   ├── cli/                     # CLI layer tests
   │   └── utils/                   # Utility function tests
   └── e2e/                         # End-to-end workflow tests
       ├── test_branch_updates.py   # Branch update scenarios
       ├── test_local_modifications.py # Local change detection
       └── test_version_pinning.py  # Version pinning workflows

Running Tests
-------------

Basic Test Execution
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage report
   pytest --cov=analog_hub --cov-report=term-missing

   # Run only unit tests
   pytest tests/unit/

   # Run only E2E tests
   pytest tests/e2e/

   # Run specific test file
   pytest tests/unit/core/test_extractor_validation.py

   # Run specific test function
   pytest tests/unit/core/test_extractor_validation.py::test_validate_library_success

Advanced Test Options
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run tests in parallel (requires pytest-xdist)
   pytest -n auto

   # Stop on first failure
   pytest -x

   # Show local variables on failure
   pytest -l

   # Verbose output
   pytest -v

   # Run tests matching pattern
   pytest -k "test_install"

Coverage Requirements
~~~~~~~~~~~~~~~~~~~~~

* **Overall Coverage**: ≥90%
* **New Code**: 100% coverage required
* **Critical Modules**: 95%+ coverage
* **CLI Commands**: ≥85% coverage

.. code-block:: bash

   # Generate HTML coverage report
   pytest --cov=analog_hub --cov-report=html
   open htmlcov/index.html

Unit Testing
------------

Unit Test Principles
~~~~~~~~~~~~~~~~~~~~

* **Isolation**: Mock all external dependencies
* **Speed**: Each test completes in milliseconds
* **Focus**: Test one specific behavior
* **Clarity**: Descriptive names and clear assertions

Example Unit Test
~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   from unittest.mock import Mock, patch
   from pathlib import Path
   
   from analog_hub.core.extractor import LibraryExtractor
   from analog_hub.core.config import LibraryConfig
   
   
   @pytest.fixture
   def mock_extractor():
       """Create a LibraryExtractor with mocked dependencies."""
       with patch('analog_hub.core.extractor.GitPython') as mock_git:
           extractor = LibraryExtractor()
           extractor.git = mock_git
           return extractor
   
   
   def test_extract_library_creates_target_directory(mock_extractor, tmp_path):
       """Test that extract_library creates the target directory."""
       # Arrange
       library_config = LibraryConfig(
           name="test_lib",
           url="https://github.com/example/repo.git",
           paths=["lib/analog"]
       )
       target_path = tmp_path / "libs" / "test_lib"
       
       # Act
       result = mock_extractor.extract_library(library_config, target_path)
       
       # Assert
       assert result.success
       assert target_path.exists()
       assert target_path.is_dir()

Mock Strategies
~~~~~~~~~~~~~~~

**Git Operations**:

.. code-block:: python

   @patch('analog_hub.core.mirror.git.Repo')
   def test_mirror_clone(mock_repo):
       mock_repo.clone_from.return_value = Mock()
       # Test mirror cloning logic

**File System Operations**:

.. code-block:: python

   @patch('analog_hub.core.extractor.shutil.copytree')
   def test_extract_paths(mock_copytree, tmp_path):
       mock_copytree.return_value = None
       # Test path extraction logic

**Network Operations**:

.. code-block:: python

   @patch('requests.get')
   def test_remote_validation(mock_get):
       mock_get.return_value.status_code = 200
       # Test remote repository validation

Test Fixtures
~~~~~~~~~~~~~

Common fixtures for consistent test setup:

.. code-block:: python

   @pytest.fixture
   def sample_config():
       """Sample analog-hub configuration."""
       return AnalogHubConfig(
           libraries=[
               LibraryConfig(
                   name="core_analog",
                   url="https://github.com/example/core.git",
                   ref="v1.0.0",
                   paths=["lib/amplifiers", "lib/filters"]
               )
           ]
       )
   
   @pytest.fixture
   def mock_lockfile(tmp_path):
       """Create a mock lockfile."""
       lockfile_path = tmp_path / ".analog-hub.lock"
       lockfile_data = {
           "libraries": {
               "core_analog": {
                   "name": "core_analog",
                   "url": "https://github.com/example/core.git",
                   "ref": "v1.0.0",
                   "commit_sha": "abc123def456",
                   "installed_at": "2025-01-15T10:30:00Z",
                   "checksum": "sha256:1234567890abcdef"
               }
           }
       }
       with open(lockfile_path, 'w') as f:
           yaml.dump(lockfile_data, f)
       return lockfile_path

End-to-End Testing
------------------

E2E Test Philosophy
~~~~~~~~~~~~~~~~~~~

* **User Scenarios**: Test complete user workflows
* **Realistic Data**: Use mock repositories with analog design files
* **Integration**: Verify component interactions
* **Error Handling**: Test failure scenarios and recovery

Mock Repository Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

E2E tests use pre-built mock repositories:

.. code-block:: text

   tests/fixtures/mock_repos/
   ├── analog_library/
   │   ├── .git/                    # Git repository
   │   ├── lib/
   │   │   ├── amplifiers/
   │   │   │   ├── ota_5t/
   │   │   │   │   ├── ota_5t.sch
   │   │   │   │   ├── ota_5t.sym
   │   │   │   │   └── ota_5t.spice
   │   │   │   └── diffamp/
   │   │   └── filters/
   │   └── models/
   └── process_library/
       ├── .git/
       └── models/

Example E2E Test
~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_complete_install_workflow(tmp_path):
       """Test complete library installation workflow."""
       # Arrange
       project_dir = tmp_path / "test_project"
       project_dir.mkdir()
       
       config_file = project_dir / "analog-hub.yaml"
       config_content = """
       libraries:
         - name: "analog_lib"
           url: "tests/fixtures/mock_repos/analog_library"
           ref: "main"
           paths:
             - "lib/amplifiers"
       """
       config_file.write_text(config_content)
       
       # Act
       result = runner.invoke(cli, ['install'], cwd=project_dir)
       
       # Assert
       assert result.exit_code == 0
       assert (project_dir / "designs" / "libs" / "analog_lib").exists()
       assert (project_dir / "designs" / "libs" / "analog_lib" / "amplifiers").exists()
       assert (project_dir / ".analog-hub.lock").exists()

Branch Update Testing
~~~~~~~~~~~~~~~~~~~~~

Test branch update detection and handling:

.. code-block:: python

   def test_branch_update_detection(tmp_path):
       """Test detection of branch updates."""
       # Initial install
       install_library("v1.0.0")
       
       # Simulate remote branch update
       update_mock_repository("v1.1.0")
       
       # Test update detection
       result = runner.invoke(cli, ['update'])
       
       assert "analog_lib updated" in result.output
       assert get_installed_version("analog_lib") == "v1.1.0"

Local Modification Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~

Test handling of local modifications:

.. code-block:: python

   def test_local_modification_detection(tmp_path):
       """Test detection of locally modified library files."""
       # Install library
       install_library()
       
       # Modify local file
       lib_file = project_dir / "designs" / "libs" / "analog_lib" / "amplifiers" / "ota.sch"
       lib_file.write_text("modified content")
       
       # Test validation
       result = runner.invoke(cli, ['validate'])
       
       assert result.exit_code != 0
       assert "checksum mismatch" in result.output.lower()

Test Data Management
--------------------

Mock Repository Creation
~~~~~~~~~~~~~~~~~~~~~~~~

Script to create realistic mock repositories:

.. code-block:: python

   def create_mock_analog_repo(repo_path: Path):
       """Create a mock analog design repository."""
       # Initialize Git repository
       repo = git.Repo.init(repo_path)
       
       # Create analog design files
       create_schematic_file(repo_path / "lib" / "amplifiers" / "ota.sch")
       create_symbol_file(repo_path / "lib" / "amplifiers" / "ota.sym")
       create_spice_file(repo_path / "lib" / "amplifiers" / "ota.spice")
       
       # Create commits
       repo.index.add(["."])
       repo.index.commit("Initial analog library")
       
       # Create tags
       repo.create_tag("v1.0.0")

Test Isolation
~~~~~~~~~~~~~~

Ensure tests don't interfere with each other:

.. code-block:: python

   @pytest.fixture(autouse=True)
   def isolated_test_environment(tmp_path, monkeypatch):
       """Isolate each test in its own directory."""
       monkeypatch.chdir(tmp_path)
       
       # Clean environment variables
       for var in ['ANALOG_HUB_CONFIG', 'GIT_CONFIG']:
           monkeypatch.delenv(var, raising=False)

Debugging Tests
---------------

Test Debugging Techniques
~~~~~~~~~~~~~~~~~~~~~~~~~

**Print Debugging**:

.. code-block:: python

   def test_complex_scenario(capfd):
       """Test with output capture for debugging."""
       result = complex_operation()
       
       # Capture and print output for debugging
       captured = capfd.readouterr()
       print(f"Debug output: {captured.out}")
       
       assert result.success

**Temporary Files**:

.. code-block:: python

   def test_with_debug_files(tmp_path):
       """Test that preserves files for debugging."""
       debug_dir = tmp_path / "debug"
       debug_dir.mkdir()
       
       # Your test logic here
       
       # Files remain in debug_dir for inspection
       if os.getenv('KEEP_DEBUG_FILES'):
           print(f"Debug files preserved in: {debug_dir}")

**Interactive Debugging**:

.. code-block:: python

   def test_interactive_debug():
       """Test with breakpoint for interactive debugging."""
       result = some_operation()
       
       # Set breakpoint for inspection
       import pdb; pdb.set_trace()
       
       assert result.expected_value

Common Testing Patterns
-----------------------

Configuration Testing
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.parametrize("config_data,expected_error", [
       ({"libraries": []}, "No libraries configured"),
       ({"libraries": [{"name": "test"}]}, "Missing required field: url"),
       ({"libraries": [{"url": "invalid"}]}, "Invalid URL format"),
   ])
   def test_config_validation(config_data, expected_error):
       """Test configuration validation with various invalid inputs."""
       with pytest.raises(ValidationError, match=expected_error):
           AnalogHubConfig(**config_data)

Error Handling Testing
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_git_error_handling(mock_git_error):
       """Test graceful handling of Git errors."""
       mock_git_error.side_effect = GitCommandError("clone failed")
       
       result = installer.install_library(library_config)
       
       assert not result.success
       assert "clone failed" in result.error_message

Performance Testing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_large_repository_performance():
       """Test performance with large repositories."""
       start_time = time.time()
       
       result = install_large_library()
       
       duration = time.time() - start_time
       assert duration < 30  # Should complete within 30 seconds
       assert result.success

Continuous Integration
----------------------

GitHub Actions Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # .github/workflows/test.yml
   name: Tests
   
   on: [push, pull_request]
   
   jobs:
     test:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python-version: [3.8, 3.9, '3.10', 3.11, 3.12]
       
       steps:
       - uses: actions/checkout@v4
       - name: Set up Python ${{ matrix.python-version }}
         uses: actions/setup-python@v4
         with:
           python-version: ${{ matrix.python-version }}
       
       - name: Install dependencies
         run: |
           pip install -e ".[dev]"
       
       - name: Run tests
         run: |
           pytest --cov=analog_hub --cov-report=xml
       
       - name: Upload coverage
         uses: codecov/codecov-action@v3

Test Coverage Reporting
~~~~~~~~~~~~~~~~~~~~~~~

Track coverage trends and ensure quality gates:

.. code-block:: bash

   # Generate coverage report
   pytest --cov=analog_hub --cov-report=html --cov-report=xml

   # Enforce coverage minimums
   pytest --cov=analog_hub --cov-fail-under=90

Best Practices
--------------

Test Organization
~~~~~~~~~~~~~~~~~

* **Descriptive Names**: Test names should describe the scenario
* **Single Responsibility**: Each test should verify one behavior
* **Arrange-Act-Assert**: Follow AAA pattern for clarity
* **Independent Tests**: Tests should not depend on each other

Test Maintenance
~~~~~~~~~~~~~~~~

* **Regular Updates**: Update tests when requirements change
* **Refactor Tests**: Keep test code clean and maintainable
* **Remove Obsolete**: Delete tests for removed functionality
* **Documentation**: Comment complex test scenarios

This comprehensive testing strategy ensures analog-hub remains reliable and maintainable as it evolves.