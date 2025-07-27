Contributing Guide
==================

We welcome contributions to analog-hub! This guide will help you get started.

Development Setup
-----------------

1. Fork and clone the repository:

.. code-block:: bash

   git clone https://github.com/YOUR_USERNAME/analog-hub.git
   cd analog-hub

2. Create a virtual environment:

.. code-block:: bash

   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate

3. Install in development mode:

.. code-block:: bash

   pip install -e ".[dev]"

4. Install documentation dependencies:

.. code-block:: bash

   pip install -e ".[docs]"

Code Quality
------------

We maintain high code quality standards:

Formatting
~~~~~~~~~~

Use Black for code formatting:

.. code-block:: bash

   black analog_hub/ tests/

Type Checking
~~~~~~~~~~~~~

Use mypy for type checking:

.. code-block:: bash

   mypy analog_hub/

Linting
~~~~~~~

Use flake8 for linting:

.. code-block:: bash

   flake8 analog_hub/ tests/

Import Sorting
~~~~~~~~~~~~~~

Use isort for import organization:

.. code-block:: bash

   isort analog_hub/ tests/

Testing
-------

We use pytest for testing with comprehensive coverage requirements.

Test Structure
~~~~~~~~~~~~~~

Tests are organized in two tiers:

* ``tests/unit/``: Fast unit tests with mocked dependencies
* ``tests/e2e/``: End-to-end tests with mock repositories

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=analog_hub --cov-report=term-missing

   # Run specific test modules
   pytest tests/unit/core/
   pytest tests/e2e/

   # Run specific test
   pytest tests/unit/core/test_extractor_validation.py::test_validate_library_success

Test Requirements
~~~~~~~~~~~~~~~~~

* All new code must have >= 90% test coverage
* Unit tests should use mocks for external dependencies
* E2E tests should use the provided mock repository fixtures
* Test names should be descriptive: ``test_install_extracts_correct_library_path``

Writing Tests
~~~~~~~~~~~~~

Unit Test Example:

.. code-block:: python

   def test_extract_library_creates_target_directory(mock_extractor):
       """Test that extract_library creates the target directory."""
       # Setup
       library_config = LibraryConfig(name="test", url="http://example.com", paths=["lib"])
       
       # Execute
       result = mock_extractor.extract_library(library_config, Path("target"))
       
       # Verify
       assert result.success
       assert Path("target").exists()

Documentation
-------------

We use Sphinx for documentation with the following standards:

Docstring Format
~~~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def extract_library(self, library: LibraryConfig, target_path: Path) -> ExtractionState:
       """Extract a library from a Git repository to the target path.
       
       Args:
           library: Configuration for the library to extract
           target_path: Local path where the library should be extracted
           
       Returns:
           ExtractionState with extraction results and metadata
           
       Raises:
           GitError: If Git operations fail
           FileSystemError: If file operations fail
       """

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs/
   make html
   # Open _build/html/index.html in browser

Contribution Workflow
---------------------

1. **Create an Issue**: Describe the bug, feature, or improvement
2. **Fork and Branch**: Create a feature branch from ``main``
3. **Implement**: Write code following our standards
4. **Test**: Ensure all tests pass and coverage is maintained
5. **Document**: Update documentation if needed
6. **Submit PR**: Create a pull request with clear description

Pull Request Guidelines
-----------------------

PR Requirements
~~~~~~~~~~~~~~~

* **Tests**: All new code must have tests
* **Coverage**: Maintain >= 90% test coverage
* **Type Hints**: All functions must have type annotations
* **Documentation**: Update docs for user-facing changes
* **Changelog**: Add entry to CHANGELOG.md for significant changes

PR Description Template
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   ## Summary
   Brief description of changes

   ## Changes
   - List of specific changes
   - Include any breaking changes

   ## Testing
   - How was this tested?
   - Any new test files or test cases?

   ## Documentation
   - Documentation updates included?
   - Any API changes documented?

Review Process
~~~~~~~~~~~~~~

1. Automated checks must pass (tests, linting, type checking)
2. Code review by maintainers
3. Documentation review if applicable
4. Final approval and merge

Development Guidelines
----------------------

Architecture Principles
~~~~~~~~~~~~~~~~~~~~~~~

* **Single Responsibility**: Each module has a clear, focused purpose
* **Dependency Injection**: Use dependency injection for testability
* **Error Handling**: Provide clear, actionable error messages
* **Performance**: Optimize for analog design workflows

Code Style
~~~~~~~~~~

* Follow PEP 8 with 88-character line limit
* Use descriptive variable names
* Prefer explicit over implicit
* Comment complex logic, not obvious code

Analog IC Focus
~~~~~~~~~~~~~~~

* Error messages should be helpful for analog designers
* File operations should preserve design file metadata
* Consider analog design workflows in feature design
* Test with realistic analog design repository structures

Release Process
---------------

Versions follow semantic versioning (MAJOR.MINOR.PATCH):

* **MAJOR**: Breaking changes
* **MINOR**: New features, backward compatible
* **PATCH**: Bug fixes, backward compatible

Release Steps:

1. Update version in ``pyproject.toml``
2. Update ``CHANGELOG.md``
3. Create release tag
4. Build and publish to PyPI
5. Update documentation

Getting Help
------------

* **Questions**: Open a GitHub Discussion
* **Bugs**: Create a GitHub Issue with reproduction steps
* **Features**: Open a GitHub Issue with use case description
* **Security**: Email security@analog-hub.dev (if applicable)

Thank you for contributing to analog-hub!